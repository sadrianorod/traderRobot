from sklearn import tree
from sklearn.preprocessing import KBinsDiscretizer
from interfaces.BackTestInterface import BackTestInterface

import gym
import numpy as np
import itertools
import pickle
from gym import spaces
from gym.utils import seeding
from DQN.agent import QAgent
from utils import get_scaler, get_data

from setup import START_MONEY, LISTED_COMPANIES_NAMES
import time

class DQNAgent(BackTestInterface):
    def __init__(self):
        super().__init__()
        #self.clf = None
        

    def setup(self, dbars):
        # data
        train_data = np.around(get_data(dbars))
        self.stock_price_history = np.around(train_data) # round up to integer to reduce state space
        self.n_stock, self.n_step = self.stock_price_history.shape
        print(self.n_stock,self.n_step)

        # instance attributes
        self.init_invest = START_MONEY
        self.cur_step = None
        self.stock_owned = None
        self.stock_price = None
        self.cash_in_hand = None

        # action space
        self.action_space = spaces.Discrete(3**self.n_stock)
        self.action_combo = [*map(list, itertools.product([0, 1, 2], repeat=self.n_stock))]

        # observation space: give estimates in order to sample and build scaler
        stock_max_price = self.stock_price_history.max(axis=1)
        stock_range = [[0, self.init_invest * 2 // mx] for mx in stock_max_price]
        price_range = [[0, mx] for mx in stock_max_price]
        cash_in_hand_range = [[0, self.init_invest * 2]]
        self.observation_space = spaces.MultiDiscrete(stock_range + price_range + cash_in_hand_range)

        # seed and start
        self.seed()
        self.reset()

        state_size = self.observation_space.shape
        action_size = self.action_space.n
        self.agent = QAgent(state_size, action_size)
        self.scaler = get_scaler(self.stock_price_history, self.init_invest, self.n_stock)

        # parameters
        self.batch_size = 500

        # here we could have a variable called 'train'. If it is true we train, otherwise we load from weight file. 
        
        # here we train =]
        state = self.reset()
        state = self.scaler.transform([state])
        for time in range(self.n_step):
            action = self.agent.act(state)
            next_state, reward, done = self.train_step(action)
            next_state = self.scaler.transform([next_state])
            self.agent.remember(state, action, reward, next_state, done)
            state = next_state
            if done:
                break
            if len(self.agent.memory) > self.batch_size: # train faster with this 
                self.agent.replay(self.batch_size)
            
        
        self.last_state = self.reset()
        self.last_state = self.scaler.transform([self.last_state])

    def ending(self, dbars):
        pass

    def trade(self, bts, dbars):
        self.state = self.update_state(bts, dbars)
        self.state = self.scaler.transform([self.state])
        action = self.agent.act(self.state)
        action_vec = self.action_combo[action]


        sell_assets = []
        buy_assets = []
        assets = LISTED_COMPANIES_NAMES
        for i, a in enumerate(action_vec):
            if a == 0:
                sell_assets.append(assets[i])
            elif a == 2:
                buy_assets.append(assets[i])

        orders=[]
        for asset in sell_assets:
            curr_shares=self.get_current_shares(asset)
            order=self.sell_order(asset,curr_shares)
            orders.append(order)
        
        money=self.get_current_money()/len(buy_assets)
        for asset in buy_assets:
            order=self.buy_order(asset,money)
            orders.append(order)

        reward = self.get_reward()
        self.agent.remember(self.last_state, action, reward, self.state, False)
        self.last_state = self.state

        if len(self.agent.memory) > self.batch_size:
                self.agent.replay(self.batch_size)

        return orders   

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]


    def reset(self):
        self.cur_step = 0
        self.stock_owned = [0] * self.n_stock
        self.stock_price = self.stock_price_history[:, self.cur_step]
        self.cash_in_hand = self.init_invest
        return self.get_obs()


    def train_step(self, action):
        assert self.action_space.contains(action)
        self.cur_step += 1
        reward = self.train_get_reward(action)
        done = self.cur_step == self.n_step - 1
        return self.get_obs(), reward, done


    def get_obs(self):
        obs = []
        obs.extend(self.stock_owned)
        obs.extend(list(self.stock_price))
        obs.append(self.cash_in_hand)
        return obs


    def get_val(self):
        return np.sum(self.stock_owned * self.stock_price) + self.cash_in_hand 
    

    def train_get_reward(self, action):
        prev_val = self.get_val()
        self.stock_price = self.stock_price_history[:, self.cur_step] # update price
        self.train_trade(action)
        cur_val = self.get_val()
        reward = cur_val - prev_val

        return reward
    
    
    def get_reward(self):
        ##        np.sum(self.stock_owned * self.stock_price) + self.cash_in_hand 
        prev_val = np.sum(self.last_state[:5] * self.last_state[5:10]) + self.cash_in_hand 

        cur_val = self.get_val()
        reward = cur_val - prev_val

        return reward

    def train_trade(self, action):
        # just update update self.cash_in_hand and self.stock_owned
        action_vec = self.action_combo[action]
        sell_assets = []
        buy_assets = []
        for i, a in enumerate(action_vec):
            if a == 0:
                sell_assets.append(i)
            elif a == 2:
                buy_assets.append(i)
        
        money=self.cash_in_hand()/len(buy_assets)
        for asset in buy_assets:
            ## TODO: tem que conferir como que o get_affor_shares funciona
            if self.stock_price[asset] < money:
                n_shares = int ( money/self.stock_price[asset] )
                self.stock_owned[asset] += n_shares
                self.cash_in_hand -= self.stock_price[asset] * n_shares
        
        for asset in sell_assets:
            # sell it all
            self.cash_in_hand += self.stock_price[asset] * self.stock_owned[asset]
            self.stock_owned[asset] = 0


    def update_state(self, bts, dbars):
        ## Aqui tenho que atualizar baseado no bts e dbars o:
        # self.stock own, que eh o vetor de assets que eu tenho [asset1, asset2, ..., asset5]
        # self.stock_price, que eh o vetor do preço atual das assets agora [price1, ..., price5]
        self.cash_in_hand = self.get_current_money()

        return self.get_obs()