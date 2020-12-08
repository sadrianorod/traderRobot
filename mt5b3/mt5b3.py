# This file is part of the mt5b3 package
#  mt5b3 home: https://github.com/paulo-al-castro/mt5b3
# Author: Paulo Al Castro
# Date: 2020-11-17


# mt5b3 main module
import MetaTrader5 as mt5
import pandas as pd 
import numpy as np 

import random
from math import *
from datetime import datetime
from datetime import timedelta
# importamos o módulo pytz para trabalhar com o fuso horário
import pytz
from pytz import timezone



sptz=pytz.timezone('Brazil/East')
etctz=pytz.timezone('etc/utc') # os tempos sao armazenados na timezone ETC (Greenwich sem horario de verao)

path=None # Metatrader program file path
datapath=None # Metatrader path to data folder
commonDatapath=None # Metatrader common data path
company=None  #broker name
platform=None  # digital plataform (M)
connected=False

"""
   login,                    // número da conta  (TODO)
   password="PASSWORD",      // senha
   server="SERVER",          // nome do servidor como definido no terminal
   timeout=TIMEOUT           // tempo de espera esgotado
"""
def connect(account=None,passw=None):
	#if not b3.connect():
	#print(“Error on connection”, b3.last_error())
	#exit():
    if account==None and passw==None:
        res= mt5.initialize()
    else:
        res= mt5.initialize(login=account, password=passw)
    global ac,path,datapath,commonDatapath,company,platform,connected
    info=mt5.account_info()
    if info.margin_so_mode !=mt5.ACCOUNT_MARGIN_MODE_RETAIL_NETTING:
        print("It is NOT netting, but B3 should be netting trade mode!! Error!!")  # B3 is Netting!!
        return False
    #elif info.margin_so_mode ==mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING:
    #    print("It is hedding, not netting")
    #else:
    #    print("It is something elese!!")
    #if info.margin_so_mode ==mt5.ACCOUNT_MARGIN_MODE_RETAIL_NETTING:
    #    print("It is netting, not hedding")  # B3 is Netting!!
    #elif info.margin_so_mode ==mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING:
    #    print("It is hedding, not netting")
    #else:
    #    print("It is something elese!!")
    if res:
        ac=mt5.terminal_info()
        path=ac.path
        datapath=ac.data_path
        commonDatapath=ac.commondata_path
        company=ac.company
        platform=ac.name
        connected=True
    return res


def accountInfo():
#acc=b3.accountInfo()    # it returns a dictionary
#acc['login']   # Account id
#acc['balance'] # Account balance in the deposit currency
# acc['equity'] # Account equity in the deposit currency
#acc['margin']  #Account margin used in the deposit currency
#acc['margin_free'] # Free margin of an account in the deposit currency
#acc['assets'] # The current assets of an account
# acc['name'] #Client name
#  acc['server'] # Trade server name
#  acc['currency'] # Account currency, BRL for Brazilian Real 
    if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return
    account_info = mt5.account_info()
    #print("account info")
    return account_info
"""
    returns the current number of assets of the given symbol
"""
def getShares(symbolId):
   if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return
   pos= mt5.positions_get(symbol=symbolId)
   if pos!=None and pos!=():
      d=pos[0]._asdict() 
      return d['volume']
   else:
       return 0

   return pos['volume']


"""
  It returns if the market is open or not for new orders.
     Note that markets can close in different times for different assets, therefore
     you need to inform the target asset. The default target assets is B3 stock.
     It there is no tick for 60 seconds, the market is considered closed!
"""
def isMarketOpen(asset='VALE3'):
  if not connected:
    print("In order to use this function, you must be connected to B3. Use function connect()")
    return
   # si=mt5.symbol_info(asset)
   # if si!=None:
  #      if si.trade_mode==mt5.SYMBOL_TRADE_MODE_FULL: # it does not work in XP/B3 (always True)
  #          return True
  #      else:
  #          return False
  #  return False

  t_secs=mt5.symbol_info_tick(asset).time # time in seconds
  now_dt=datetime.now(etctz)+timedelta(hours=-3)
  last_tick_dt=datetime.fromtimestamp(t_secs,etctz)
  #print(last_tick_dt)
  #print(now_dt)
  if now_dt>last_tick_dt+timedelta(seconds=60):
      return False
  else: 
      return True

"""
  It returns if the market is still open but just for closing orders.
     Note that markets can close in different times for different assets, therefore
     you need to inform the target asset. The default target assets is B3 stock
"""
#def isMarketClosing(asset='B3SA3'): # it does not work in XP/B3 (always false)
#    si=mt5.symbol_info(asset)
#    if si!=None:
 #       if si.trade_mode==mt5.SYMBOL_TRADE_MODE_CLOSEONLY:
  #          return True
  #      else:
  #          return False
  #  return False


def getFreeMargin():
    if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return
    return mt5.account_info().margin_free

    
"""
    returns the max volume of shares thay you can buy, with your balance
        it also observes the volume step (a.k.a minimum number of shares you can trade)
"""
def getAfforShares(assetId,money=None,price=None):
    if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return
    if money==None:
        money=mt5.account_info().balance
    if money <=0:
        return 0.0
        
    if price==None:
        close=mt5.symbol_info_tick(assetId).last
    else:
        close=price
    

    step=mt5.symbol_info(assetId).volume_step
    free=0
    while free*close<money:
        free=free+step
    return free-step

def getSharesStep(assetId,money=None):
    if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return
    return mt5.symbol_info(assetId).volume_step
 
# Saldo da conta em BRL
def getBalance():
    return mt5.account_info().balance

# Valor da posição total, saldo em reais mais valores correntes dos ativos (Balance+getPosition).
def getTotalPosition():
    return getPosition()+getBalance()

def getPosition(symbolId=None):  # return the current value of assets (it does not include balance or margin)
#b3.getPosition( symbol_id) # return the current position in a given asset (symbol_id)
#Examples:
#b3.getPosition('PETR4')
#pos=b3.getPosition('ITUB3')
#pos['volume'] # position volume
#pos['open'] # position open price
#pos['time'] #position open time
#pos['symbol'] # position symbol id
#pos['price']  #current price of the asset
# b3.getPosition(group='PETR*') # returns a list of positions that are part of the group
  #print("get position")
  if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return

  if symbolId==None:
      return mt5.positions_total()
  else:
      return mt5.positions_get(symbol=symbolId)



def buyOrder(symbolId,volume,price=None,sl=None,tp=None): # Buying !!
#b=b3.buy(symbol_id,volume, price, sl, tp ))
#if b3.checkorder(b):
#    if b3.send(b): #buying
#	print('order sent to B3')
#    else:
#	print('Error : ',b3.getLastError())
#else:
#    print('Error : ',b3.getLastError())
   if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return
   symbol_info = mt5.symbol_info(symbolId)
   #print("symbol=",symbolId," info=",symbol_info)
   if symbol_info is None:
        setLastError(symbolId + " not found, can not create buy order")
        return None
 
# se o símbolo não estiver disponível no MarketWatch, adicionamo-lo
   if not symbol_info.visible:
        #print(symbolId, "is not visible, trying to switch on")
        if not mt5.symbol_select(symbolId,True):
            setLastError("symbol_select({}}) failed! symbol=" +symbolId)
            return None   
   point = mt5.symbol_info(symbolId).point
   deviation = 20
   
   request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": symbolId,
    "volume": float(volume),
    "type": mt5.ORDER_TYPE_BUY,

    "deviation": deviation,
    "magic": random.randrange(100,100000),
    "comment": "order by mt5b3",
    "type_time": mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_RETURN,
    }
   if price==None:  # order a mercado
       request['action']=mt5.TRADE_ACTION_DEAL
       request['type']=mt5.ORDER_TYPE_BUY
       request['price']=mt5.symbol_info_tick(symbolId).ask
   else:  # order limitada
       request['action']=mt5.TRADE_ACTION_PENDING
       request['type']=mt5.ORDER_TYPE_BUY_LIMIT
       request['price']=float(price)
   if sl!=None:
       request["sl"]=sl
   if tp!=None:
        request["tp"]= tp
  

   return request

def sellOrder(symbolId,volume,price=None,sl=None,tp=None): # Selling !!
    symbol_info = mt5.symbol_info(symbolId)
    #print("symbol=",symbolId," info=",symbol_info)
    if symbol_info is None:
        setLastError(symbolId + " not found, can not create buy order")
        return None
# se o símbolo não estiver disponível no MarketWatch, adicionamo-lo
    if not symbol_info.visible:
        #print(symbolId, "is not visible, trying to switch on")
        if not mt5.symbol_select(symbolId,True):
            setLastError("symbol_select({}}) failed! symbol=" +symbolId)
            return None   
    point = mt5.symbol_info(symbolId).point
    deviation = 20
    request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": symbolId,
    "volume": float(volume),
    "type": mt5.ORDER_TYPE_SELL,
    
    "deviation": deviation,
    "magic": random.randrange(100,100000),
    "comment": "order by mt5b3",
    "type_time": mt5.ORDER_TIME_DAY,
    "type_filling": mt5.ORDER_FILLING_FOK,
    }

    if price==None:  # order a mercado
       request['action']=mt5.TRADE_ACTION_DEAL
       request['type']=mt5.ORDER_TYPE_SELL
       request['price']=mt5.symbol_info_tick(symbolId).ask
    else:  # order limitada
       request['action']=mt5.TRADE_ACTION_PENDING
       request['type']=mt5.ORDER_TYPE_SELL_LIMIT
       request['price']=float(price)

    if sl!=None:
       request["sl"]=sl
   
    if tp!=None:
        request["tp"]= tp
    
    return request


def isSellOrder(req):
    if req==None:
        print("Error! Order is None!!!!")
        return False
    if req['type']==mt5.ORDER_TYPE_SELL_LIMIT or req['type']==mt5.ORDER_TYPE_SELL:
        return True
    elif req['type']==mt5.ORDER_TYPE_BUY_LIMIT or req['type']==mt5.ORDER_TYPE_BUY:
        return False
    else:
        print("Error! Order is not buy our sell!!!!")
        return False
    

def checkOrder(req):
    if req==None:
        return False
    result = mt5.order_check(req)
    #print('result=',result, 'req=',req)
    if result==None: # error
        setLastError(mt5.last_error())
        return False
    d=result._asdict()
    #for k in d.keys():
    #    print('{} = {}',k,d[k])
    if d['margin_free']>=d['request'].volume*d['request'].price : # checa se não ficaria negativo com a execução
        return True
    else:
        setLastError('Trade would make the balance negative! Therefore, it does not check!')
        return False

lastErrorText=""
def getLastError():
    global lastErrorText
    if lastErrorText==None or lastErrorText=="":
        return mt5.last_error()
    else:
        aux=lastErrorText
        lastErrorText=None  
        return aux    
    
def setLastError(error):
    global lastErrorText
    lastErrorText=error


def sendOrder(order):
    if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return
    if order==None:
        return False
    # enviamos a solicitação de negociação
    result = mt5.order_send(order)
    if result.retcode != mt5.TRADE_RETCODE_DONE:  # if error
        print("Sent order failed < {} > retcode={}".format(result.comment,result.retcode))
        # solicitamos o resultado na forma de dicionário e exibimos elemento por elemento
        dic=result._asdict()
        setLastError(dic['comment'])
       # for field in dic.keys():
       #     print("   {}={}".format(field,dic[field]))
       #     #se esta for uma estrutura de uma solicitação de negociação, também a exibiremos elemento a elemento
       #     if field=="request":
       #         traderequest_dict=dic[field]._asdict()
       #         for tradereq_filed in traderequest_dict:
       #             print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
        return False
    else:
        return True

    
def cancelOrder(o):# TO DO
   # action= TRADE_ACTION_REMOVE
    print("To do....")

def numOrders(): #returns the number of active orders
    if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return
    result=mt5.orders_total()
    if result==None:
        setLastError("Error on getting orders total")
        return -1
    else:
        return result

#order fields  description:
    #order_id | buy_sell | volume | price | sl | tp | 
    #ticket | time_setup  time_setup_msc  time_expiration  type  type_time  type_filling  state  magic  
    # volume_current  price_open   sl   tp  price_current  symbol comment external_id
    #   ulong                         magic;            // Expert Advisor -conselheiro- ID (número mágico)
   #  ulong                         order;            // Bilhetagem da ordem
   #string                        symbol;           // Símbolo de negociação
  # double                        volume;           // Volume solicitado para uma encomenda em lotes
  # double                        price;            // Preço
  # double                        stoplimit;        // Nível StopLimit da ordem
  # double                        sl;               // Nível Stop Loss da ordem
  # double                        tp;               // Nível Take Profit da ordem
  # ulong                         deviation;        // Máximo desvio possível a partir do preço requisitado
 #  ENUM_ORDER_TYPE               type;             // Tipo de ordem
    #  ORDER_TYPE_BUY  Ordem de Comprar a Mercado
    #  ORDER_TYPE_SELL Ordem de Vender a Mercado
    #  ORDER_TYPE_BUY_LIMIT Ordem pendente Buy Limit
    #  ORDER_TYPE_SELL_LIMIT Ordem pendente Sell Limit
    #  ORDER_TYPE_BUY_STOP Ordem pendente Buy Stop
    #  ORDER_TYPE_SELL_STOP Ordem pendente Sell Stop
    #  ORDER_TYPE_BUY_STOP_LIMIT Ao alcançar o preço da ordem, uma ordem pendente Buy Limit é colocada no preço StopLimit
    #  ORDER_TYPE_SELL_STOP_LIMIT Ao alcançar o preço da ordem, uma ordem pendente Sell Limit é colocada no preço StopLimit
    #  ORDER_TYPE_CLOSE_BY  Ordem de fechamento da posição oposta
  # ENUM_ORDER_TYPE_FILLING       type_filling;     // Tipo de execução da ordem
    #ORDER_FILLING_FOK  Esta política de preenchimento significa que uma ordem pode ser preenchida somente na quantidade especificada. Se a quantidade desejada do ativo não está disponível no mercado, a ordem não será executada. 
  #  ENUM_ORDER_TYPE_TIME          type_time;        // Tipo de expiração da ordem
    # ORDER_TIME_DAY     Ordem válida até o final do dia corrente de negociação
  # datetime                      expiration;       // Hora de expiração da ordem (para ordens do tipo ORDER_TIME_SPECIFIED))
  # string                        comment;          // Comentário sobre a ordem
  # ulong                         position;         // Bilhete da posição
  # ulong                         position_by;      // Bilhete para uma posição oposta

def getOrders():  # returns a dataframe with all active orders
    if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return
    orders=mt5.orders_get()
    if orders == None or len(orders)==0:
        print("No orders, error code={}".format(mt5.last_error()))
        return None
    else:
        print("Total orders:",len(orders))
        df=pd.DataFrame(list(orders),columns=orders[0]._asdict().keys())
        return df
      


def getDailYBars(symbol, start,end=None): # sao inclusas barras com  tempo de abertura <= end.
    # definimos o fuso horário como UTC
    #timezone = pytz.timezone("Etc/UTC")
    if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return
    if end==None:
        end=datetime.now()
    if type(start).__name__!='datetime':
        if type(start).__name__!='int':
            print('Error, start should be a datetime from package datetime or int')
        else:
            start_day=datetime.now() #- timedelta(days=start)
            rates=mt5.copy_rates_from(symbol,mt5.TIMEFRAME_D1,start_day,start)
             # criamos a partir dos dados obtidos DataFrame
            rates_frame=pd.DataFrame(rates)
            rates_frame['time']=pd.to_datetime(rates_frame['time'], unit='s')
            return rates_frame
    else:
       rates=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_D1,start,end)
       # criamos a partir dos dados obtidos DataFrame
       rates_frame=pd.DataFrame(rates)
       rates_frame['time']=pd.to_datetime(rates_frame['time'], unit='s')
       return rates_frame
DAILY=1 # 
INTRADAY=2 #minutes


"""
  returns open-close serie of returns from bars
   the same order from bars (older-[0] to newer-[len-1])
"""
def getReturns(bars,offset=1):
    if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return
    x=[]
    offset=abs(offset)
    if offset==1:
        for i in range(len(bars)):
            x.append(bars['close'][i]/bars['open'][i]-1)
    else:
        for i in range(len(bars)-offset):
            x.append(bars['close'][i+offset]/bars['open'][i]-1)

    return x

def getLastPrice(bars): # argumento deve ser bars nao vazia, retorna erro se estiver vazia
    if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return
    return bars['close'].iloc[-1]

def getFirstPrice(bars):# argumento deve ser bars nao vazia, retorna erro se estiver vazia
    if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return
    return bars['open'][0]
   
def getLastTime(bars): # argumento deve ser bars nao vazia, retorna erro se estiver vazia
    return bars['time'].iloc[-1]

def getFirstTime(bars):# argumento deve ser bars nao vazia, retorna erro se estiver vazia
    if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return
    return bars['time'][0]

def readBarsFile(fileName):
    df=pd.read_csv(fileName,delimiter='\t',names=['date','time','open','high','low','close','vol', 'tickvol','spread'],header=0) 
    if df==None or len(df.columns)!=9:
        print("The bars file should be a csv file with nine columns: date,time,open,high,low,close,vol, tickvol,spread")
        return None
    else:
        return df

def getBars(symbol, start,end=None,timeFrame=INTRADAY):
 # definimos o fuso horário como UTC
    #timezone = pytz.timezone("Etc/UTC")
    #print("timeFrame: ",timeFrame)
    #print("symbol: ",symbol)
    #print("start: ",start)
    #print("end: ",end)
    if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return
    if symbol==None or type(symbol)!=str:
        return None
    else:
        symbol=symbol.upper()
    if timeFrame==DAILY:
        timeFrame=mt5.TIMEFRAME_D1
    elif timeFrame==INTRADAY:
        timeFrame=mt5.TIMEFRAME_M1
    else:
        timeFrame=mt5.TIMEFRAME_D1
    if end==None:
        end=datetime.now()
    if type(start).__name__!='datetime' and type(start).__name__!='Timestamp':
        if type(start).__name__!='int':
            print('Error, start should be a datetime or int, but it is ',type(start).__name__)
            return None
        else:
            start_day=datetime.now() #- timedelta(days=start)
            rates=mt5.copy_rates_from(symbol,timeFrame,start_day,start)
             # criamos a partir dos dados obtidos DataFrame
            rates_frame=pd.DataFrame(rates)
            if len(rates_frame)>0:
                rates_frame['time']=pd.to_datetime(rates_frame['time'], unit='s')
            #print("rates", rates_frame)
            return rates_frame
    else:
        if type(end).__name__=='int':
            rates=mt5.copy_rates_from(symbol,timeFrame,start,end)
        else:
            rates=mt5.copy_rates_range(symbol,timeFrame,start,end)
       # criamos a partir dos dados obtidos DataFrame
        rates_frame=pd.DataFrame(rates)
        if len(rates_frame)>0:
            rates_frame['time']=pd.to_datetime(rates_frame['time'], unit='s')
        #print("rates", rates_frame)
        return rates_frame


def getIntradayBars(symbol, day):
    # definimos o fuso horário como UTC
    #timezone = pytz.timezone("Etc/UTC")
    if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return
    if type(day).__name__!='datetime':
        print('Error, start should be a datetime from package datetime')
    else:
       rates=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M1,\
       day,datetime(day.year,day.month,day.day,23,59))
       rates_frame=pd.DataFrame(rates)
       rates_frame['time']=pd.to_datetime(rates_frame['time'], unit='s')
       # criamos a partir dos dados obtidos DataFrame
       return rates_frame
##############
# datetime auxiliary functions

def date(year,month,day,hour=0,min=0,sec=0):
    if not connected:
        print("In order to use this function, you must be connected to B3. Use function connect()")
        return
    return datetime(year,month,day,hour,min,sec)
###############################


# used in inverse control trader and backtest!!
class Trader:
    def __init__(self):
        pass

    def setup(self,dbars):
        pass

    def trade(self,dbars):
        pass
    def ending(self,dbars):
        pass
 

