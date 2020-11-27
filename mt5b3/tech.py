# This file is part of the mt5b3 package
#  mt5b3 home: https://github.com/paulo-al-castro/mt5b3
# Author: Paulo Al Castro
# Date: 2020-11-17


import pandas as pd 
import numpy as np 
import mt5b3.mt5b3 as b3

def rsi(returns):
    if type(returns)==pd.core.frame.DataFrame:
        returns=b3.getReturns(returns)
    u=0.0
    uc=0
    d=0.0
    dc=0
    for r in returns:
        if r>=0:
            u=u+r
            uc=uc+1
        else:
            d=d+r
            dc=dc+1
    if uc>0:
        u=u/uc
    if dc>0:
        d=d/dc   
    if d==0:
        d=1.0
    ifr=100*( 1 - 1/(1+u/d))
    return ifr


