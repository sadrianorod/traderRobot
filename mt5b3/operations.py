# This file is part of the mt5b3 package
#  mt5b3 home: https://github.com/paulo-al-castro/mt5b3
# Author: Paulo Al Castro
# Date: 2020-11-17

"""
Operations Module - Disponibiliza funções para facilitar a criação, execução e avaliação de backtests
"""

import mt5b3.mt5b3 as b3
from datetime import datetime
from datetime import timedelta
import pandas as pd 
import time

def sessionStart(startHour=10,min=0):
    starts= datetime.now()
    starts = starts.replace(hour=startHour, minute=min)
    return starts

def sessionEnd():
    endHour=18; min=0
    ends= datetime.now()
    ends = ends.replace(hour=endHour, minute=min)

    return ends
#Returns the time to the end of session in seconds (float)
def secondsToEndSession(ops,refTime=None):
    if ops==None or ops['endTime']==None:
        return 0
    if refTime==None:
        refTime=datetime.now()
    d=ops['endTime']-refTime
    return d.total_seconds()


def set(assets,capital,endTime,mem,timeframe=b3.DAILY,file='operation_file',verbose=False,delay=1,waitForOpen=False):
    ops=dict()  #backtest setup
    if type(waitForOpen)==bool:
        ops['waitForOpen']=waitForOpen
    else:
        print('waitForOpen should be bool')
    if type(verbose)==bool:
        ops['verbose']=verbose
    else:
        print('verbose should be bool')
        return None
    if type(delay)==float or type(delay)==int:
        ops['delay']=mem
    else:
        print('delay should be float')
        return None
    
    if type(mem)==int:
        ops['mem']=mem
    else:
        print('mem should be int')
        return None

    if type(endTime)==datetime:
        ops['end']=endTime
    else:
        print('endTime should be datetime')
        return None
    if timeframe==b3.DAILY or timeframe==b3.INTRADAY:
        ops['type']=timeframe
    else:
        print('type should be daily or intraday')
        return None
    if type(file)==str:
        ops['file']=file
    else:
        print('file should be str')
        return None
    if type(assets)==list:
        ops['assets']=assets
    else:
        print('assets should be list')
        return None
    if type(capital)==float or type(capital)==int:
        ops['capital']=float(capital)
    else:
        print('capital should be float')
        return None
    return ops


def checkOps(ops):
    try:
        if type(ops['waitForOpen'])!=bool:
            print('waitForOpen should be bool')
            return False
        if type(ops['verbose'])!=bool:
            print('verbose should be bool')
            return False
        if type( ops['mem'])!=int:
            print('mem should be int')
            return False
        if type( ops['delay'])!=int and type( ops['delay'])!=float:
            print('delay should be int or float. (seconds of delay, between to calls to trade)')
            return False
        if type(ops['start'] )!=datetime:
            print('start should be datetime')
            return False
        if type(ops['end'])!=datetime:
            print('end should be datetime')
            return False
        if ops['type']!=b3.DAILY and ops['type']!=b3.INTRADAY:
            print('type should be daily or intraday')
            return False
        if type(ops['file'])!=str:
            print('file should be str')
            return False
        if type(ops['assets'])!=list:
            print('assets should be list')
            return False
        if type(ops['capital'])!=float and type(ops['capital'])!=int:
            print('capital should be float')
            return False
        return True
    except:
        print("An exception occurred")
        return False



## assume-se que todos os ativos tem o mesmo numero de barras do ativo indice zero assets[0] no periodo de backtest
sim_dates=[]
balanceHist=[]
equityHist=[]
datesHist=[]
def getCurrTime(ops):
    assets=ops['assets']
    bars=b3.getBars(assets[0],1,b3.INTRADAY)
    return bars['time'][0]
    
def startOps(ops): 
    global sim_dates
    assets=ops['assets']
    dbars=dict()
    
    sim_dates.append(getCurrTime(ops))
    mem=ops['mem']
    for asset in assets:
        dbar=b3.getBars(asset,mem)
        if not dbar is None and not dbar.empty:
            dbars[asset]=dbar
        else:
            print("Error asset ",asset, " without information!!!")
    balanceHist.append(ops['capital'])
    equityHist.append(ops['capital'])
    datesHist.append(sim_dates[0])
    return dbars



def executeOrders(orders,ops,dbars):
    assets=ops['assets']
    total_in_shares=0.0
    sim_dates.append(getCurrTime(ops))
    # No orders!
    if orders==None:
        equityHist.append(equityHist[-1])
        balanceHist.append(balanceHist[-1])
        datesHist.append(sim_dates[-1])
        balance=b3.getBalance() 
        total_in_shares=b3.getPosition()
        if ops['verbose']:
            print( 'No orders in time(',sim_dates[-1],') = ',sim_dates[-1],' balance=',balance, 'total in shares=',total_in_shares,' Positon=',(balance+total_in_shares))
        return True
    #Yes, some orders
    if ops['verbose']:
        print('List of ',len(orders),'orders in time(',sim_dates[-1],') :')
    for asset in assets:
        order=getOrder(orders,asset)
        # send order
        if order!=None:
            if b3.checkOrder(order) and b3.sendOrder(order): 
                    print('order sent to B3')
            else:
                    print('Error  : ',b3.getLastError())
        else:
            balance=b3.getBalance() 
            shares=b3.getShares(asset)
            print("No order at the moment for asset=",asset,' balance=',balance,' asset''s shares=',shares)
            continue
    balance=b3.getBalance() 
    total_in_shares=b3.getPosition()
    if ops['verbose']:
        print( len(orders),' order(s) in time(',sim_dates[-1],' capital=',balance, 'total in shares=',total_in_shares, 'equity=',balance+total_in_shares)
    equityHist.append(balance+total_in_shares)
    balanceHist.append(balance)
    datesHist.append(sim_dates[-1])
    #detalhamento das ordens
    
    

def getOrder(orders,asset):
    for order in orders:
        if order['symbol']==asset:
            return order
    return None


def getCurrBars(ops,dbars):
    assets=ops['assets']
    #dbars=dict()
    for asset in assets:
        dbar=dbars[asset]
        #pega nova barra    
        aux=b3.getBars(asset,1) # pega uma barra!
        if not aux is None and not aux.empty:
            dbar=dbar.iloc[1:,] #remove barra mais antiga
            #adiciona nova barra
            dbar=dbar.append(aux)
            dbar.index=range(len(dbar))# corrige indices
            dbars[asset]=dbar
       
    return dbars 

def getLastTime(ops):
    assets=ops['assets']
    bars=b3.getBars(assets[0],1,b3.INTRADAY)
    return bars['time'][0]
   

def endedOps(ops):
    if not b3.isMarketOpen():
        print('Market is NOT open at the moment!!')
        return True
    
    if ops['verbose']:
        print('Ended?? time =',getCurrTime(ops), ' of ',len(sim_dates))
    if ops['end']==None:
        return True
    elif ops['end']<getLastTime(ops):
        return 
    else:
        return False


def run(trader,ops):
    if trader==None: # or type(trader)!=b3.Trader:
        print("Error! Trader should be an object of class mt5b3.Trader or its subclass")
        return False
    dbars=startOps(ops)
    trader.setup(dbars)
    if 'delay' in ops.keys():
        delay=ops['delay']
    else:
        delay=0
    if ops['verbose']:
        print("Starting Operation at date/time=",sim_dates[0]," len=",len(sim_dates))
    if ops['waitForOpen']:
        while not b3.isMarketOpen():
            print('Market is NOT open! we will wait until it is open...')
            time.sleep(1)
    while not endedOps(ops):
        orders=trader.trade(ops,dbars)
        executeOrders(orders,ops,dbars)
        dbars=getCurrBars(ops,dbars)
        time.sleep(delay)
    print('End of operation saving equity file in ',ops['file'])
    trader.ending(dbars)
    df=saveEquityFile(ops)
    return df


def saveEquityFile(ops):
    """
    print('csv format, columns: <DATE>		<BALANCE>	<EQUITY>	<DEPOSIT LOAD>')
<DATE>	            <BALANCE>	<EQUITY>	<DEPOSIT LOAD>
2019.07.01 00:00	100000.00	100000.00	0.0000
2019.07.01 12:00	99980.00	99999.00	0.0000
2019.07.01 12:59	99980.00	100002.00	0.1847
2019.07.01 12:59	99980.00	99980.00	0.0000
2019.07.02 14:59	99960.00	99960.00	0.0000
2019.07.03 13:00	99940.00	99959.00	0.0000
2019.07.03 13:59	99940.00	99940.00	0.0000
2019.07.08 15:59	99920.00	99936.00	0.0000
2019.07.08 16:59	99920.00	99978.00	0.1965
2019.07.10 10:00	99920.00	99920.00	0.0000
2019.07.10 10:59	99900.00	99937.00	0.1988
Formato gerado pelo metatrader,
ao fazer backtest com o Strategy Tester, clicar na tab 'Graphs' e botao direto 'Export to CSV (text file)'
    """
    #print('write report....')
    if len(equityHist)!=len(balanceHist) or len(balanceHist)!=len(datesHist):
        print("Erro!! Diferentes tamanhos de historia, de equity, balance e dates")
        return False
    df=pd.DataFrame()
    df['date']=[]
    df['balance']=[]
    df['equity']=[]
    df['load']=[]

    for i in range(len(equityHist)):
        df.loc[i]=[datesHist[i],balanceHist[i],equityHist[i],0.0]

    df.to_csv(ops['file']+'.csv') 
    return df 


