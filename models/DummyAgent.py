from interfaces.BackTestInterface import BackTestInterface
from interfaces.OperationsInterface import OperationsInterface
import numpy.random as rand
"""
    Just use ModelInterface
    Implement trade, setup and ending
"""

class DummyAgentOperations(OperationsInterface):
    def __init__(self):
        super().__init__()

    def setup(self,dbars):
        print('just getting started!')

    def trade(self,ops,dbars):
        orders=[] 
        assets= self.get_assets(dbars = dbars)
        for asset in assets:
            if rand.randint(2)==1:     
                order=self.buy_order(asset=asset,volume=1000)
            else:
            	order=self.sell_order(asset=asset,volume=1000)
            orders.append(order)
        return orders
    
    def ending(self,dbars):
        print('Ending stuff')


class DummyAgentBacktest(BackTestInterface):
    def __init__(self):
        super().__init__()

    def setup(self,dbars):
        print('just getting started!')

    def trade(self,bts,dbars):
        orders=[] 
        assets= self.get_assets(dbars = dbars)
        for asset in assets:
            if rand.randint(2)==1:     
                order=self.buy_order(asset=asset,volume=1000)
            else:
            	order=self.sell_order(asset=asset,volume=1000)
            orders.append(order)
        return orders
    
    def ending(self,dbars):
        print('Ending stuff')
