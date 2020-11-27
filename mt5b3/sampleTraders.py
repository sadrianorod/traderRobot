# This file is part of the mt5b3 package
#  mt5b3 home: https://github.com/paulo-al-castro/mt5b3
# Author: Paulo Al Castro
# Date: 2020-11-17

import numpy.random as rand
import mt5b3 as b3
import time
import pandas as pd
import numpy as np

class DummyTrader(b3.Trader):
    def __init__(self):
        pass

    def setup(self,dbars):
        print('just getting started!')

    def trade(self,ops,dbars):
        orders=[] 
        assets=ops['assets']
        for asset in assets:
            if rand.randint(2)==1:     
                order=b3.buyOrder(asset,100)
            else:
            	order=b3.sellOrder(asset,100)
            orders.append(order)
        return orders
    
    def ending(self,dbars):
        print('Ending stuff')

 

class MonoAssetTrader(b3.Trader):
    def trade(self,bts,dbars):
        assets=dbars.keys()
        asset=list(assets)[0]
        orders=[]
        bars=dbars[asset]
        curr_shares=b3.backtest.getShares(bts,asset)
        # number of shares that you can buy
        free_shares=b3.backtest.getAfforShares(bts,dbars,asset)
        rsi=b3.tech.rsi(bars)
        if rsi>=70:   
            order=b3.buyOrder(asset,free_shares)
        else:
            order=b3.sellOrder(asset,curr_shares)
        if rsi>=70 and free_shares>0: 
            order=b3.buyOrder(asset,free_shares)
        elif  rsi<70 and curr_shares>0:
            order=b3.sellOrder(asset,curr_shares)
        if order!=None:
                orders.append(order)
        return orders    



class MultiAssetTrader(b3.Trader):
    def trade(self,bts,dbars):
        assets=dbars.keys()
        orders=[]
        for asset in assets:
            bars=dbars[asset]
            curr_shares=b3.backtest.getShares(bts,asset)
            money=b3.backtest.getBalance(bts)/len(assets) # divide o saldo em dinheiro igualmente entre os ativos
            # number of shares that you can buy of asset 
            free_shares=b3.backtest.getAfforShares(bts,dbars,asset,money)
            rsi=b3.tech.rsi(bars)
            if rsi>=70 and free_shares>0: 
                order=b3.buyOrder(asset,free_shares)
            elif  rsi<70 and curr_shares>0:
                order=b3.sellOrder(asset,curr_shares)
            else:
                order=None
            if order!=None:
                orders.append(order)
        return orders    


from sklearn import tree
from sklearn.preprocessing import KBinsDiscretizer
 
class SimpleAITrader(b3.Trader):

    def setup(self,dbars):
        assets=list(dbars.keys())
        if len(assets)!=1:
            print('Error, this trader is supposed to deal with just one asset')
            return None
        bars=dbars[assets[0]]
        timeFrame=10 # it takes into account the last 10 bars
        horizon=1 # it project the closing price for next bar
        target='close' # name of the target column
        ds=b3.ai_utils.bars2Dataset(bars,target,timeFrame,horizon)

        X=b3.ai_utils.fromDs2NpArrayAllBut(ds,['target'])
        discretizer = KBinsDiscretizer(n_bins=3, encode='ordinal', strategy='uniform') 

        ds['target']=b3.ai_utils.discTarget(discretizer,ds['target'])
        Y=b3.ai_utils.fromDs2NpArray(ds,['target'])

        clf = tree.DecisionTreeClassifier()

        clf = clf.fit(X, Y)
        self.clf=clf

    def trade(self,bts,dbars):
            assets=dbars.keys()
            orders=[]
            timeFrame=10 # it takes into account the last 10 bars
            horizon=1 # it project the closing price for next bar
            target='close' # name of the target column
            for asset in assets:
                curr_shares=b3.backtest.getShares(asset)
                money=b3.backtest.getBalance()/len(assets) # divide o saldo em dinheiro igualmente entre os ativos
                free_shares=b3.backtest.getAfforShares(asset,money,dbars)
                # get new information (bars), transform it in X
                bars=dbars[asset]
                #remove irrelevant info
                del bars['time']
                # convert from bars to dataset
                ds=b3.ai_utils.bars2Dataset(bars,target,timeFrame,horizon)
                # Get X fields
                X=b3.ai_utils.fromDs2NpArrayAllBut(ds,['target'])

                # predict the result, using the latest info
                p=self.clf.predict([X[-1]])
                if p==2:
                    #buy it
                    order=b3.buyOrder(asset,free_shares)
                elif p==0:
                    #sell it
                    order=b3.sellOrder(asset,curr_shares)
                else:
                    order=None
                if order!=None:
                    orders.append(order)
            return orders    
