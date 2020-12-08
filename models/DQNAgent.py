from sklearn import tree
from sklearn.preprocessing import KBinsDiscretizer
from interfaces.BackTestInterface import BackTestInterface
from interfaces.OperationsInterface import OperationsInterface

import gym
import numpy as np
import itertools
import pickle
from gym import spaces
from gym.utils import seeding
from models.DQN.agent import QAgent
from utils import get_scaler, get_data

from setup import START_MONEY, LISTED_COMPANIES_NAMES
import time

class DQNAgentOperations(OperationsInterface):
    def __init__(self):
        super().__init__()
        #self.clf = None
        

    def setup(self, dbars):
        print("Setup")
        # data
        #train_data = np.around(get_data(dbars))
        train_data = get_data(dbars)
        print(train_data)
        self.stock_price_history = train_data # round up to integer to reduce state space
        self.n_stock, self.n_step = self.stock_price_history.shape
        print(self.n_stock,self.n_step)

        # instance attributes
        self.init_invest = self.b3.getBalance()
        self.cur_step = None
        self.stock_owned = None
        self.stock_price = None
        self.cash_in_hand = None

        # action space
        self.action_space = spaces.Discrete(3**self.n_stock)
        self.action_combo = [*map(list, itertools.product([0, 1, 2], repeat=self.n_stock))]

        # observation space: give estimates in order to sample and build scaler
        stock_max_price = [100 for i in range(self.n_stock)]
        #stock_range = [[0, self.init_invest * 2 // mx] for mx in stock_max_price]
        stock_range = [[0,1000],[0,1000],[0,1000],[0,1000],[0,1000]] 
        price_range = [[0, mx*100] for mx in stock_max_price]
        cash_in_hand_range = [[0, self.init_invest * 200]]
        print(stock_range + price_range + cash_in_hand_range)

        self.observation_space = spaces.MultiDiscrete(stock_range + price_range + cash_in_hand_range)

        # seed and start
        self.seed()
        self.reset()

        state_size = self.observation_space.shape
        action_size = self.action_space.n
        self.agent = QAgent(state_size, action_size)
        self.agent.load('./weights/dqn')
        self.scaler = get_scaler(self.stock_price_history, self.init_invest, self.n_stock)

        # parameters
        self.batch_size = 500

        # here we could have a variable called 'train'. If it is true we train, otherwise we load from weight file. 
        
        # here we train =]
        # state = self.reset()
        # state = self.scaler.transform([state])
        # for time in range(self.n_step):
        #     print("time:", time, "/", self.n_step)
        #     action = self.agent.act(state)
        #     next_state, reward, done = self.train_step(action)
        #     next_state = self.scaler.transform([next_state])
        #     self.agent.remember(state, action, reward, next_state, done)
        #     state = next_state
        #     if done:
        #         break
        #     if len(self.agent.memory) > self.batch_size: # train faster with this 
        #         self.agent.replay(self.batch_size)
            
        self.last_state = self.reset()
        self.last_state = self.scaler.transform([self.last_state])

    def ending(self, dbars):
        pass

    def trade(self, bts, dbars):
        print("Tradando for real")
        self.state = self.update_state(bts, dbars)
        print("Estado atual:", self.state)
        self.state = self.scaler.transform([self.state])
        action = self.agent.act(self.state)
        action_vec = self.action_combo[action]
        print("Acao a ser tomada:", action_vec)

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
        
        if len(buy_assets) != 0:
            money=self.b3.getBalance()/len(buy_assets)
            for asset in buy_assets:
                afford_shares = self.b3.getAfforShares(assetId=asset, money=money)
                if afford_shares > 0:
                    order=self.buy_order(asset,afford_shares)
                    orders.append(order)

        reward = self.get_reward(action_vec)
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
        for arr in self.stock_price:
            obs.append(int(np.average(arr))*100)
        obs.append(self.cash_in_hand)
        return obs


    def get_val(self):
        
        self.stock_price = np.array([round(np.average(arr),2) for arr in self.stock_price])
        return np.sum(self.stock_owned * self.stock_price) + self.cash_in_hand 
    

    def train_get_reward(self, action):
        action_vec = self.action_combo[action]
        #print("action: ", action_vec)
        prev_val = self.get_val()
        self.stock_price = self.stock_price_history[:, self.cur_step] # update price
        self.train_trade(action)
        cur_val = self.get_val()
        for a in action_vec:
            if a==1:
                cur_val -= 2000
        reward = cur_val - prev_val

        return reward
    
    
    def get_reward(self, action_vec):
        ##        np.sum(self.stock_owned * self.stock_price) + self.cash_in_hand 
        prev_val = np.sum(self.last_state[:5] * self.last_state[5:10]) + self.cash_in_hand 

        cur_val = self.get_val()
        for a in action_vec:
            if a==1:
                cur_val -= 2000
        print("TOTAL:", cur_val)
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
        
        if len(buy_assets):
            money=self.cash_in_hand/len(buy_assets)
            for asset in buy_assets:
                ## TODO: tem que conferir como que o get_affor_shares funciona
                if self.stock_price[asset] < money:
                    # afford_shares = self.get_affordable_shares(assets[asset], money)
                    n_shares = int ( money/self.stock_price[asset] )
                    # print("shares:", n_shares, ", afford:", afford_shares)
                    self.stock_owned[asset] += n_shares
                    self.cash_in_hand -= self.stock_price[asset] * n_shares
        
        for asset in sell_assets:
            # sell it all
            self.cash_in_hand += self.stock_price[asset] * self.stock_owned[asset]
            self.stock_owned[asset] = 0


    def update_state(self, bts, dbars):
        # update self.stock_owned = [asset1, asset2, ..., asset5]
        current_shares = list()
        for asset in LISTED_COMPANIES_NAMES:
            current_shares.append(self.get_current_shares(asset))
        self.stock_owned = current_shares

        # update self.stock_price = [price1, ..., price5]
        self.stock_price = get_data(dbars)
        self.cash_in_hand = self.get_current_money()

        return self.get_obs()

    
    def get_current_stock_prices(self, dbars, time):
        # stock_prices = np.around(get_data(dbars))
        stock_prices = get_data(dbars)
        
        return stock_prices[:, time]



class DQNAgentBacktest(BackTestInterface):
    def __init__(self):
        super().__init__()
        #self.clf = None
        

    def setup(self, dbars):
        print("Setup")
        # data
        #train_data = np.around(get_data(dbars))
        train_data = get_data(dbars)
        self.stock_price_history = train_data # round up to integer to reduce state space
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
        #stock_range = [[0, self.init_invest * 2 // mx] for mx in stock_max_price]
        stock_range = [[0,1000],[0,1000],[0,1000],[0,1000],[0,1000]] 
        price_range = [[0, mx*100] for mx in stock_max_price]
        cash_in_hand_range = [[0, self.init_invest * 2]]
        print(stock_range + price_range + cash_in_hand_range)

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
            print("time:", time, "/", self.n_step)
            action = self.agent.act(state)
            next_state, reward, done = self.train_step(action)
            next_state = self.scaler.transform([next_state])
            self.agent.remember(state, action, reward, next_state, done)
            state = next_state
            if done:
                break
            if len(self.agent.memory) > self.batch_size: # train faster with this 
                self.agent.replay(self.batch_size)
            
        
        self.agent.save('./weights/dqn')

        self.last_state = self.reset()
        self.last_state = self.scaler.transform([self.last_state])

    def ending(self, dbars):
        pass

    def trade(self, bts, dbars):
        print("Tradando for real")
        self.state = self.update_state(bts, dbars)
        print("Estado atual:", self.state)
        self.state = self.scaler.transform([self.state])
        action = self.agent.act(self.state)
        action_vec = self.action_combo[action]
        print("Acao a ser tomada:", action_vec)

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
        
        if len(buy_assets) != 0:
            money=self.get_current_money()/len(buy_assets)
            for asset in buy_assets:
                afford_shares = self.get_affordable_shares(dbars, asset=asset, money=money)
                order=self.buy_order(asset,afford_shares)
                orders.append(order)

        reward = self.get_reward(action_vec)
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
        obs.extend(list(self.stock_price*100))
        obs.append(self.cash_in_hand)
        return obs


    def get_val(self):
        return np.sum(self.stock_owned * self.stock_price) + self.cash_in_hand 
    

    def train_get_reward(self, action):
        action_vec = self.action_combo[action]
        #print("action: ", action_vec)
        prev_val = self.get_val()
        self.stock_price = self.stock_price_history[:, self.cur_step] # update price
        self.train_trade(action)
        cur_val = self.get_val()
        for a in action_vec:
            if a==1:
                cur_val -= 2000
        reward = cur_val - prev_val

        return reward
    
    
    def get_reward(self, action_vec):
        ##        np.sum(self.stock_owned * self.stock_price) + self.cash_in_hand 
        prev_val = np.sum(self.last_state[:5] * self.last_state[5:10]) + self.cash_in_hand 

        cur_val = self.get_val()
        for a in action_vec:
            if a==1:
                cur_val -= 2000
        print("TOTAL:", cur_val)
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
        
        if len(buy_assets):
            money=self.cash_in_hand/len(buy_assets)
            for asset in buy_assets:
                ## TODO: tem que conferir como que o get_affor_shares funciona
                if self.stock_price[asset] < money:
                    # afford_shares = self.get_affordable_shares(assets[asset], money)
                    n_shares = int ( money/self.stock_price[asset] )
                    # print("shares:", n_shares, ", afford:", afford_shares)
                    self.stock_owned[asset] += n_shares
                    self.cash_in_hand -= self.stock_price[asset] * n_shares
        
        for asset in sell_assets:
            # sell it all
            self.cash_in_hand += self.stock_price[asset] * self.stock_owned[asset]
            self.stock_owned[asset] = 0


    def update_state(self, bts, dbars):
        # update self.stock_owned = [asset1, asset2, ..., asset5]
        current_shares = list()
        for asset in LISTED_COMPANIES_NAMES:
            current_shares.append(self.get_current_shares(asset))
        self.stock_owned = current_shares

        # update self.stock_price = [price1, ..., price5]
        self.stock_price = self.get_current_stock_prices(dbars, bts['curr'])
        self.cash_in_hand = self.get_current_money()

        return self.get_obs()

    
    def get_current_stock_prices(self, dbars, time):
        # stock_prices = np.around(get_data(dbars))
        stock_prices = get_data(dbars)
        
        return stock_prices[:, time]
