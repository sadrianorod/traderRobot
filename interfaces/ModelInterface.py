import mt5b3 as b3
from setup import LOGIN,PASSWORD

class ModelInterface(b3.Trader):
    
    def __init__(self,*args,**kargs):

        if not b3.connect(account = LOGIN,passw = PASSWORD): raise ConnectionError("Connection Error: B3 was not connected")
        else: print("Connection with MetaTrader was stablished.")

        self.b3            = b3
        self.args          = args
        self.kargs         = kargs
        
    
    def get_assets(self,dbars): return dbars.keys()
    
    def get_current_money(self): return self.b3.getBalance()

    def get_current_shares(self,asset): return self.b3.getShares(asset)

    def get_affordable_shares(self, asset , money=None): return self.b3.getAfforShares(assetId=asset,money= money)
        
    def buy_order(self,asset,volume): return self.b3.buyOrder(symbolId=asset,volume=volume)
    
    def sell_order(self,asset,volume): return self.b3.sellOrder(symbolId=asset,volume=volume)    

    

    