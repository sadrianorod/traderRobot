from interfaces.BackTestInterface import BackTestInterface
from interfaces.OperationsInterface import OperationsInterface
import mt5b3.mt5b3 as b3
import numpy as np
from tensorforce import Agent, Environment, PPOAgent, Runner
from typing import Any

from setup import START_MONEY, LISTED_COMPANIES_NAMES
from utils import get_data

class PPOWolfOfWallstreet(OperationsInterface):
    """
        MONEY, MONEY, MONEY!
    """
    def __init__(self) -> None:
        super().__init__()
        self.trader = PPOTrader(self.b3, mode='operation')

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
        self.trader = PPOTrader(self.b3, mode='train')

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
    def __init__(self, b3Interface: b3, mode: str) -> None:
        self.mode = mode                   # Operation mode. No real use by now.
        self.b3Interface = b3Interface      # Actual trading API. A wrapper over MetaTrader library.
    
    def setup(self, dbars: Any) -> Any:
        trainingEnvironment = Environment.create(
            environment=TradingEnvironment(dbars),
        )
        self.agent = Agent.create(
            agent=PPOAgent,
            environment=trainingEnvironment,  # alternatively: states, actions, (max_episode_timesteps)
            update=dict(
                unit='timesteps', 
                batch_size=64
            ),
            network="auto",
            ## exploration=?,
            reward_estimation=dict(
                horizon=20
                # discount=?,
            ),
            learning_rate=3e-4,
            # likelihood_ratio_clipping=?,
            # subsampling_fraction=?,
            # multi_step=?
            summarizer=dict(
                directory='./tensorboard/'
            )
        )
        self.agent.save(directory='model-numpy', format='checkpoint', append='episodes')
        ## Train!
        runner = Runner(self.agent, environment=trainingEnvironment)
        runner.run(
            num_episodes=10000,
            save_best_agent='./best-agent/'
        )
        trainingEnvironment.close()
        ## Prepare agent for trading
        self.internal_state = self.agent.initial_internals()

    def trade(self, conf: Any, dbars: Any) -> Any: 
        state = ... # TODO: Convert dbars into state dict
        ## Decide action!
        actions, self.internal_state = self.agent.act(
            state, 
            internals=self.internal_state,
            independent=True,   # No reward or anything, just tell me what to do
            deterministic=True  # Don't explore, just exploit
        )
        orders = []
        ## TODO: Translate actions into orders
        return orders

    def ending(self, dbars: Any) -> Any:
        self.agent.save(directory='training', format='numpy', append='episodes')
        self.agent.close()

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
        # self._assetCodes = { LISTED_COMPANIES_NAMES[i]: i for i in range(self._nassets) }
        ## Minimum & Maximum stock prices: Useful for determining the state space range
        self._minStockPrice = self._data.min(axis=1)
        self._maxStockPrice = self._data.max(axis=1)
        ## Reset state
        self.reset()

    # TODO: Static utility to create a state representation

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
                asset,
                dict(
                    type=int,
                    num_actions=3
                )
            ) for asset in range(self._nassets)
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
            ((
                'stocks_'+LISTED_COMPANIES_NAMES[asset],
                dict(
                    type=float,
                    min_value=0,
                    max_value=2*START_MONEY // self._minStockPrice[asset]
                )
            ) for asset in range(self._nassets)),                            # 2.
            ((
                'price_'+LISTED_COMPANIES_NAMES[asset],
                dict(
                    type=float,
                    min_value=0,
                    max_value=self._maxStockPrice[asset]
                )
            ) for asset in range(self._nassets)),                            # 3.
            cash=dict(type=float, min_value=0, max_value=2*START_MONEY)      # 1.
        )
    
    def reset(self):
        """
            Resets all variables to start a new episode.
            return new initial state.
        """
        self._agentCash = START_MONEY ## TODO: Should this really be the same at the start of every day?
        self._agentStocks = np.zeros((self._nassets,1))
        self._timestep = 0
        self._currentPrices = self._data[:,self._timestep]
        return dict(
                ((
                    'stocks_'+LISTED_COMPANIES_NAMES[asset],
                    self._agentStocks[asset]
                ) for asset in range(self._nassets)),
                ((
                    'price_'+LISTED_COMPANIES_NAMES[asset],
                    self._currentPrices[asset]
                ) for asset in range(self._nassets)),
                cash=self._agentCash
            )

    
    def execute(self, actions):
        """
            :actions: dict[int] -> {0,1,2}.
        """
        ## Buying/Selling
        buying, _ = zip(*list(filter(lambda _, value: value == TradingEnvironment.BUY_ACTION, actions.items())))
        selling, _ = zip(*list(filter(lambda _, value: value == TradingEnvironment.SELL_ACTION, actions.items())))
        ##
        ## -> Distribute resources between assets being bought
        ## 
        capitalPerAsset = self._agentCash / self._nassets
        buyingReward = 0.0
        if np.fabs(capitalPerAsset) >= 1.0: ## Threshold for enabling buying
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
            self._agentCash += moneyReceived
            sellingReward += moneyReceived
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
            dict(
                ((
                    'stocks_'+LISTED_COMPANIES_NAMES[asset],
                    self._agentStocks[asset]
                ) for asset in range(self._nassets)),
                ((
                    'price_'+LISTED_COMPANIES_NAMES[asset],
                    self._currentPrices[asset]
                ) for asset in range(self._nassets)),
                cash=self._agentCash
            ), 
            terminal,
            reward
        )
