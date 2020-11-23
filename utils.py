import pandas as pd
from setup import USEFUL_COLUMNS_NAMES,LISTED_COMPANIES_NAMES,PRICE_COLUMN_NAME,DATE_COLUMN_NAME,TIME_COLUMN_NAME
from functools import reduce

def generate_listed_companies_dataframe(path_to_datasets_folder : str):
    listed_companies_dict = generate_listed_companies_dict(path_to_datasets_folder)
    return reduce(lambda *args: args[0].merge(args[1], on = [DATE_COLUMN_NAME,TIME_COLUMN_NAME]), listed_companies_dict.values())
    

def generate_listed_companies_dict(path_to_datasets_folder : str):
    df = dict()
    for company in LISTED_COMPANIES_NAMES:
        df[company] = pd.read_csv(path_to_datasets_folder  + company + '.csv',sep='\t')
        filter_useful_dataframe_columns(df[company],USEFUL_COLUMNS_NAMES,inplace=True)
        df[company].rename(columns = {PRICE_COLUMN_NAME: company}, inplace=True)
    return df


def filter_useful_dataframe_columns(dataframe : pd.DataFrame, useful_columns: list, inplace=False): 
    columns_to_drop = [attribute for attribute in dataframe.columns if attribute not in useful_columns]
    return dataframe.drop(columns_to_drop,axis=1,inplace=inplace)

        