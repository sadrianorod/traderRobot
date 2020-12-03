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

from setup import START_MONEY
import time

class DQNAgent(BackTestInterface):
    def __init__(self):
        super().__init__()
        #self.clf = None
        

    def setup(self,dbars):
        """  assets=['VALE3']
        if len(assets)!=1:
            print('Error, this trader is supposed to deal with just one asset')
            return None
        bars=dbars[assets[0]]
        # remove irrelevant info
        if 'time' in bars:
            del bars['time']
        timeFrame=10 # it takes into account the last 10 bars
        horizon=1 # it project the closing price for next bar
        target='close' # name of the target column
        ds=self.b3.ai_utils.bars2Dataset(bars,target,timeFrame,horizon)

        X=self.b3.ai_utils.fromDs2NpArrayAllBut(ds,['target'])
        discretizer = KBinsDiscretizer(n_bins=3, encode='ordinal', strategy='uniform') 

        # creates the discrete target
        ds['target']=self.b3.ai_utils.discTarget(discretizer,ds['target'])

        
        Y=self.b3.ai_utils.fromDs2NpArray(ds,['target'])
        clf = tree.DecisionTreeClassifier()
        clf = clf.fit(X, Y)
        self.clf=clf """

        ## Entao, aqui eu preciso de uma função que popule a variavel train_data baseado em dbars
        ## tipo, agora eu fiz uma que pega as informações dos csv salvos, mas a gente vai querer
        ## uma que use aquela starDate e Predate EU ACHO.
        train_data = np.around(get_data(dbars))
        
        # data
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
        self.action_space = spaces.Discrete(5**self.n_stock)

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

        # training parameters
        self.episode = 2000
        self.batch_size = 32
        timestamp = time.strftime('%Y%m%d%H%M')

        # here we could have a variable called 'train'. If it is true we train, otherwise we load from weight file. 
        portfolio_value = []
        for e in range(self.episode): # change this number to size of train data
            state = self.reset()
            state = self.scaler.transform([state])
            for time in range(self.n_step):
                action = self.agent.act(state)
                next_state, reward, done, info = self.step(action)
                next_state = self.scaler.transform([next_state])
                self.agent.remember(state, action, reward, next_state, done)
                state = next_state
                if done:
                    print("episode: {}/{}, episode end value: {}".format(
                    e + 1, self.episode, info['cur_val']))
                    portfolio_value.append(info['cur_val']) # append episode end portfolio value
                    break
                if len(self.agent.memory) > self.batch_size:
                    self.agent.replay(self.batch_size)
            if (e + 1) % 10 == 0:  # checkpoint weights
                self.agent.save('weights/{}-dqn.h5'.format(timestamp))

        # save portfolio value history to disk
        with open('portfolio_val/{}-{}.p'.format(timestamp, "train"), 'wb') as fp:
            pickle.dump(portfolio_value, fp)

    def ending(self,dbars):
        pass

    def trade(self,bts,dbars):
            assets=['VALE3'] #só utiliza 1 ação nessa implementação
            orders=[]
            timeFrame=10 # it takes into account the last 10 bars
            horizon=1 # it project the closing price for next bar
            target='close' # name of the target column
            for asset in assets:
                curr_shares=self.get_current_shares(asset)
                money=self.get_current_money()/len(assets) # divide o saldo em dinheiro igualmente entre os ativos
                free_shares=self.get_affordable_shares(dbars,asset)
                # get new information (bars), transform it in X
                bars=dbars[asset]
                #remove irrelevant info
                if 'time' in bars:
                    del bars['time']
                # convert from bars to dataset
                ds=self.b3.ai_utils.bars2Dataset(bars,target,timeFrame,horizon)
                # Get X fields
                X=self.b3.ai_utils.fromDs2NpArrayAllBut(ds,['target'])

                # predict the result, using the latest info
                p=self.clf.predict([X[-1]])
                if p==2:
                    #buy it
                    order=self.buy_order(asset,free_shares)
                elif p==0:
                    #sell it
                    order=self.sell_order(asset,curr_shares)
                else:
                    order=None
                if order!=None:
                    orders.append(order)
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


    def step(self, action):
        assert self.action_space.contains(action)
        reward, cur_val = self.get_reward(action)
        done = self.cur_step == self.n_step - 1
        info = {'cur_val': cur_val}
        return self.get_obs(), reward, done, info


    def get_obs(self):
        obs = []
        obs.extend(self.stock_owned)
        obs.extend(list(self.stock_price))
        obs.append(self.cash_in_hand)
        return obs


    def get_val(self):
        return np.sum(self.stock_owned * self.stock_price) + self.cash_in_hand 
    
    def get_reward(self, action):
        prev_val = self.get_val()
        self.cur_step += 1
        self.stock_price = self.stock_price_history[:, self.cur_step] # update price
        self._trade(action)
        cur_val = self.get_val()
        reward = cur_val - prev_val

        return reward, cur_val
