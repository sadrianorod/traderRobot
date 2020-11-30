import os
import pandas as pd
import numpy as np
from mt5b3 import pd
from setup import USEFUL_COLUMNS_NAMES,LISTED_COMPANIES_NAMES,PRICE_COLUMN_NAME,DATE_COLUMN_NAME,TIME_COLUMN_NAME
from functools import reduce
from sklearn.preprocessing import StandardScaler

def generate_listed_companies_dataframe(path_to_datasets_folder : str):
    listed_companies_dict = generate_listed_companies_dict(path_to_datasets_folder)
    return reduce(lambda *args: args[0].merge(args[1], on = [DATE_COLUMN_NAME,TIME_COLUMN_NAME]), listed_companies_dict.values())
    
def generate_listed_companies_dict(path_to_datasets_folder : str):
    df = dict()
    for company in LISTED_COMPANIES_NAMES:
        df[company] = pd.read_csv(path_to_datasets_folder  + company + '.csv',sep='\t')
        filter_useful_dataframe_columns(dataframe = df[company], useful_columns = USEFUL_COLUMNS_NAMES, inplace = True)
        df[company].rename(columns = { PRICE_COLUMN_NAME : company}, inplace = True)
    return df

def filter_useful_dataframe_columns(dataframe : pd.DataFrame, useful_columns: list, inplace=False): 
    columns_to_drop = [attribute for attribute in dataframe.columns if attribute not in useful_columns]
    return dataframe.drop(columns_to_drop,axis=1,inplace=inplace)

def calcReturns(serie):
    x=[]
    for i in range(len(serie)-1): # calculates the serie of returns
        x.append(serie[i+1]/serie[i]-1)
    return x

def make_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_data(col='close'):
    """ Only for the close col """
    bbas3 = pd.read_csv('dataset/BBAS3.csv', usecols=[col])
    bbdc4 = pd.read_csv('dataset/BBDC4.csv', usecols=[col])
    itub4 = pd.read_csv('dataset/ITUB4.csv', usecols=[col])
    petr4 = pd.read_csv('dataset/PETR4.csv', usecols=[col])
    vale3 = pd.read_csv('dataset/VALE3.csv', usecols=[col])
    
    return np.array([bbas3[col], bbdc4[col], itub4[col], petr4[col], vale3[col]])

def get_scaler(stock_price_history, init_invest):
    """ Takes a env and returns a scaler for its observation space """
    low = [0] * (env.n_stock * 2 + 1)

    high = []
    max_price = stock_price_history.max(axis=1)
    min_price = stock_price_history.min(axis=1)
    max_cash = init_invest * 3 # 3 is a magic number...
    max_stock_owned = max_cash // min_price
    for i in max_stock_owned:
        high.append(i)
    for i in max_price:
        high.append(i)
    high.append(max_cash)

    scaler = StandardScaler()
    scaler.fit([low, high])

    return scaler