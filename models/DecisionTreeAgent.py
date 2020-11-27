from sklearn import tree
from sklearn.preprocessing import KBinsDiscretizer
from interfaces.BackTestInterface import BackTestInterface

class DecisionTreeAgent(BackTestInterface):

    def __init__(self):
        super().__init__()
        self.clf = None
        

    def setup(self,dbars):
        assets=['VALE3']
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
        self.clf=clf

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

