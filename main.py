from models.DecisionTreeAgent import DecisionTreeAgent
from models.DummyAgent import DummyAgent

#print(generate_listed_companies_dataframe(path_to_datasets_folder = './datasets/'))

#Backtest
# trader = DecisionTreeAgent()
# print(trader.get_dict_of_metrics())

#Operations
trader = DummyAgent()
trader._run_operations()


