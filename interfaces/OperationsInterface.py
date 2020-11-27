from interfaces.ModelInterface import ModelInterface
from setup import START_MONEY,LISTED_COMPANIES_NAMES,DELAY,MEMORY_BARS,WAIT_FOR_OPEN,RESULTS_FILE

class OperationsInterface(ModelInterface):

    def __init__(self,*args,**kargs):
        super().__init__(args,kargs)
        self.ops = self._get_operations_set()
    

    def setup(self,dbars): raise NotImplementedError("Not Implemented Error: setup was not implemented.")

    def trade(self,ops,dbars): raise NotImplementedError("Not Implemented Error: trade was not implemented.")

    def ending(self,dbars): raise NotImplementedError("Not Implemented Error: ending was not implemented.")

    def _run_operations(self):
        self.b3.operations.run(self,self.ops)
        
    def _get_operations_set(self):
        # sets Backtest options 
        
        capital     =   START_MONEY
        verbose     =   False 
        endTime     =   self.b3.operations.sessionEnd() 

        assets      =   LISTED_COMPANIES_NAMES
        timeframe   =   self.b3.INTRADAY
        delay       =   DELAY
        wait        =   WAIT_FOR_OPEN
        mem         =   MEMORY_BARS
        results_file=   RESULTS_FILE

        ops         =   self.b3.operations.set(assets,capital,endTime,mem,timeframe,results_file,verbose,delay,wait)
        
        return ops
    