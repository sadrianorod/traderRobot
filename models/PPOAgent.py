from interfaces.BackTestInterface import BackTestInterface
from interfaces.OperationsInterface import OperationsInterface
import mt5b3.mt5b3 as b3
import numpy as np
from tensorforce import Agent, Environment, Runner
from tensorforce.agents import PPOAgent
from typing import Any

from setup import START_MONEY, LISTED_COMPANIES_NAMES
from utils import get_data

## Trust me, you'll need this
ASSET_INDEX = { company.lower(): i for i, company in enumerate(LISTED_COMPANIES_NAMES) }

class PPOWolfOfWallstreet(OperationsInterface):
    """
        MONEY, MONEY, MONEY!
    """
    def __init__(self) -> None:
        super().__init__()
        self.trader = PPOTrader(self, self.b3, mode='operation')

    def setup(self, dbars):
        self.trader.setup(dbars)

    def trade(self, conf, dbars):
        self.trader.trade(conf, dbars)
    
    def ending(self, dbars):
        self.trader.ending(dbars)

class PPOChicken(BackTestInterface):
    """
        co, co, co.
    """
    def __init__(self) -> None:
        super().__init__()
        self.trader = PPOTrader(self, self.b3, mode='train')

    def setup(self, dbars):
        self.trader.setup(dbars)

    def trade(self, conf, dbars):
        self.trader.trade(conf, dbars)
    
    def ending(self, dbars):
        self.trader.ending(dbars)

####################
#### PPO Trading Agent
####################

class PPOTrader:
    """
        Does the actual work.
    """
    def __init__(self, b3Agent, b3Interface: b3, mode: str) -> None:
        self.mode = mode                   # Operation mode. No real use by now.
        self.b3Interface = b3Interface      # Actual trading API. A wrapper over MetaTrader library.
        self.b3Agent = b3Agent              # The trading interface. This code is a fucking mess.
    
    def setup(self, dbars: Any) -> Any: # No idea what the types actually are
        trainingEnvironment = Environment.create(
            environment=TradingEnvironment(dbars),
        )
        self.agent = Agent.create(
            agent=PPOAgent,
            environment=trainingEnvironment,  # alternatively: states, actions, (max_episode_timesteps)
            batch_size=64,
            network="auto",
            ## Optimization
            learning_rate=3e-4,
            # subsampling_fraction=?,
            # multi_step=?
            ## Reward estimation
            # discount=?,
            # likelihood_ratio_clipping=?,
            ## Exploration
            # exploration=?,
            summarizer=dict(
                directory='./training/tensorboard/'
            )
        )
        self.agent.save(directory='model-numpy', format='checkpoint', append='episodes')
        ## Train!
        runner = Runner(self.agent, environment=trainingEnvironment)
        runner.run(
            num_episodes=10000,
            save_best_agent='./training/bestagent'
        )
        trainingEnvironment.close()
        ## Prepare agent for trading
        self.internal_state = self.agent.initial_internals()

    def trade(self, conf: Any, dbars: Any) -> Any: # No idea what the types actually are
        return [] ## TODO: WIP
        nassets = len(conf['assets'])
        currentMoney = self.b3Agent.get_current_money()
        currentShares = [ self.b3Agent.get_current_shares(asset) for asset in conf['assets'] ]
        currentPrices = get_data(dbars)
        state = TradingEnvironment.state(currentMoney, currentShares, currentPrices, nassets)
        ## Decide action!
        actions, self.internal_state = self.agent.act(
            state, 
            internals=self.internal_state,
            independent=True,   # No reward or anything, just tell me what to do
            deterministic=True  # Don't explore, just exploit
        )
        
        buying = [ ASSET_INDEX[assetStr] for assetStr, act in actions.items() if act == TradingEnvironment.BUY_ACTION ]
        selling = [ ASSET_INDEX[assetStr] for assetStr, act in actions.items() if act == TradingEnvironment.SELL_ACTION ]
        orders = []
        capitalPerAsset = currentMoney / nassets
        if np.fabs(capitalPerAsset) >= 1.0: ## Threshold to enable buying
            for asset in buying:
                buyingStocksQty = int(currentPrices[asset] / capitalPerAsset)
                if buyingStocksQty * currentPrices[asset] > capitalPerAsset: buyingStocksQty -= 1
                moneySpent = buyingStocksQty * currentPrices[asset]
                currentShares[asset] += buyingStocksQty
                currentMoney -= moneySpent
                if currentMoney < 1.0:
                    # Money all spent. Early break.
                    break
            ##
            ## -> Sell all stocks owned
            ## 
            for asset in selling:
                moneyReceived = currentShares[asset] * currentPrices[asset]
                # Clip this money if it makes me richer than the 2*START_MONEY limit.
                moneyReceived = min(moneyReceived, 2*START_MONEY-self._agentCash)
                agent += moneyReceived

        return orders

    def ending(self, dbars: Any) -> Any: # No idea what the types actually are
        self.agent.save(directory='training', format='numpy', append='episodes')
        self.agent.close()

####################
#### PPO Trading Environment
####################

class TradingEnvironment(Environment):
    """
        The trading environment uses a set trading days to train an agent.
        Each trading day consists of an episode.
        The episode comprehends minute-wise intraday trading from 10am to 5pm.
            It may terminate earlier if for any reason we don't have all the data (we started late or something
            prevented us from gathering data from the end of the day, usually)
    """

    SELL_ACTION = 0
    NOP_ACTION = 1
    BUY_ACTION = 2

    def __init__(self, dbars) -> None:
        super().__init__()
        self._dbars = dbars
        self._data = get_data(dbars)
        ## _data shape: (number of assets, number of days * number of steps per day = total steps in the episode)
        ## We're using only close prices
        self._nassets, self._totalAvailableSteps = self._data.shape
        ## Minimum & Maximum stock prices: Useful for determining the state space range
        self._minStockPrice = self._data.min(axis=1)
        self._maxStockPrice = self._data.max(axis=1)
        ## Reset state
        self.reset()

    @staticmethod
    def state(agentCash, agentStocks, stockPrices, nassets: int):
        """
            Build a dictionary of state from variables that make the state.
        """
        return dict(
                **{
                    'stocks_'+LISTED_COMPANIES_NAMES[asset].lower(): agentStocks[asset]
                    for asset in range(nassets)
                },
                **{
                    'price_'+LISTED_COMPANIES_NAMES[asset].lower(): stockPrices[asset]
                    for asset in range(nassets)
                },
                cash=agentCash
            )

    def max_episode_timesteps(self) -> int:
        """
            10am -> 5pm
            with 1 minute resolution
        """
        return (17-10)*60
    
    def actions(self):
        """
            Returns dictionary specifying the actions that can be taken.
            One nested dicionary for each asset BBAS3, BBDC4, ITUB4, PETR4, VALE3.
            Each nested dictionary with 3 options: buy, sell or nothing.
            Sell -> Sells all stocks at hand.
            Nothing -> Well, nothing.
            Buy -> Spends all the money equally between the assets being bought.
        """
        return dict(
            (
                assetStr.lower(),
                dict(
                    type='int',
                    shape=(),
                    num_values=3
                )
            ) for assetStr in LISTED_COMPANIES_NAMES
        )

    def states(self):
        """
            Three sub states:
            1- Cash in hand. We stablish that the agent cannot end the day with more than double
                his money. Therefore it's in the range [0, 2*START_MONEY]
            2- Number of stocks in possession. With the theoretical maximum cash stablished, the
                maximum stocks the agent can have is 2*START_MONEY/MIN_STOCK_PRICE
            3- Price of the assets.
        """
        return dict(
            **{
                ## TODO: This is wrong, it should be int
                'stocks_'+LISTED_COMPANIES_NAMES[asset].lower(): dict(type='float', shape=(), min_value=0, max_value=(2*START_MONEY // self._minStockPrice[asset]))
                for asset in range(self._nassets)
            },                            # 2.
            **{
                'price_'+LISTED_COMPANIES_NAMES[asset].lower(): dict(type='float', shape=(), min_value=0,max_value=self._maxStockPrice[asset])
                for asset in range(self._nassets)
            },                            # 3.
            cash=dict(type='float', shape=(), min_value=0, max_value=2*START_MONEY)      # 1.
        )
    
    def reset(self):
        """
            Resets all variables to start a new episode.
            return new initial state.
        """
        self._agentCash = START_MONEY ## TODO: Should this really be the same at the start of every day?
        self._agentStocks = np.zeros(self._nassets)
        self._timestep = 0
        self._currentPrices = self._data[:,self._timestep]
        return TradingEnvironment.state(self._agentCash, self._agentStocks, self._currentPrices, self._nassets)

    
    def execute(self, actions):
        """
            :actions: dict[int] -> {0,1,2}.
        """
        ## Buying/Selling
        buying = [ ASSET_INDEX[assetStr] for assetStr, act in actions.items() if act == TradingEnvironment.BUY_ACTION ]
        selling = [ ASSET_INDEX[assetStr] for assetStr, act in actions.items() if act == TradingEnvironment.SELL_ACTION ]
        ##
        ## -> Distribute resources between assets being bought
        ## 
        capitalPerAsset = self._agentCash / self._nassets
        buyingReward = 0.0
        if np.fabs(capitalPerAsset) >= 1.0: ## Threshold to enable buying
            for asset in buying:
                buyingStocksQty = int(self._currentPrices[asset] / capitalPerAsset)
                if buyingStocksQty * self._currentPrices[asset] > capitalPerAsset: buyingStocksQty -= 1
                moneySpent = buyingStocksQty * self._currentPrices[asset]
                self._agentStocks[asset] += buyingStocksQty
                self._agentCash -= moneySpent
                buyingReward -= moneySpent
                if self._agentCash < 1.0:
                    # Money all spent. Early break.
                    break
        ##
        ## -> Sell all stocks owned
        ## 
        sellingReward = 0.0
        for asset in selling:
            moneyReceived = self._agentStocks[asset] * self._currentPrices[asset]
            # Clip this money if it makes me richer than the 2*START_MONEY limit.
            moneyReceived = min(moneyReceived, 2*START_MONEY-self._agentCash)
            self._agentCash += moneyReceived
            sellingReward += moneyReceived
            self._agentStocks[asset] = 0
        ##
        ## -> Calculate reward
        ##
        reward = buyingReward + sellingReward
        ##
        ## -> Commit next state
        ##
        self._timestep += 1
        ## -> Check finished
        ##      * No need to check max_steps, tensorforce does it for us
        ##      * Check if there are steps left. If there aren't, terminate early.
        terminal = self._timestep >= self._totalAvailableSteps
        self._currentPrices = self._data[:,self._timestep] if not terminal else np.zeros((self._nassets,1))
        return (
            TradingEnvironment.state(self._agentCash, self._agentStocks, self._currentPrices, self._nassets), 
            terminal,
            reward
        )
