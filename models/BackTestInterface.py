from models.ModelInterface import ModelInterface
from setup import PRE_START_DATE,START_DATE,END_DATE,START_MONEY,LISTED_COMPANIES_NAMES,RESULTS_FILE
from utils import calcReturns

class BackTestInterface(ModelInterface):

    def __init__(self,*args,**kargs):
        super().__init__(args,kargs)
        self.bts = self._get_backtest_set()
    
    def setup(self,dbars): raise NotImplementedError("Not Implemented Error: setup was not implemented.")

    def trade(self,dbars): raise NotImplementedError("Not Implemented Error: trade was not implemented.")

    def ending(self,dbars): raise NotImplementedError("Not Implemented Error: ending was not implemented.")

    def get_current_shares(self,asset): return self.b3.backtest.getShares(bts = self.bts, asset = asset)

    def get_current_money(self): return self.b3.backtest.getBalance(self.bts)

    def get_affordable_shares(self,dbars,asset,money = None): return self.b3.backtest.getAfforShares(self.bts,dbars,assetId=asset,money=money)

    def get_dict_of_metrics(self):
        dataframe = self._run_backtest()
        serie = dataframe['equity']
        serie= calcReturns(serie)

        return {
            'Total Return'            : self.b3.backtest.calcTotalReturn(serie)*100,
            'Standard Deviation'      : self.b3.backtest.calcStdDev(serie)*100,
            'Average Return'          : self.b3.backtest.calcAvgReturn(serie)*100,
            'Geometric Average Return': self.b3.backtest.calcGeoAvgReturn(serie)*100
        }


    def _run_backtest(self, print_evaluation = False):
        dataframe = self.b3.backtest.run(self,self.bts)
        if print_evaluation: self.b3.backtest.evaluate(dataframe)
        return dataframe
    

    def _get_backtest_set(self):
        # sets Backtest options 
        prestart    =   self.b3.date(*PRE_START_DATE)
        start       =   self.b3.date(*START_DATE)
        end         =   self.b3.date(*END_DATE)
        capital     =   START_MONEY
        results_file=   RESULTS_FILE
        verbose     =   False 
        assets      =   LISTED_COMPANIES_NAMES
        period      =   self.b3.INTRADAY 

        bts         =   self.b3.backtest.set(assets,prestart,start,end,period,capital,results_file,verbose)
        
        if not self.b3.backtest.checkBTS(bts): raise Exception("Error: get_backtest_set was not ok !")
        
        return bts
    