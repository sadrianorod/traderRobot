from utils import generate_listed_companies_dataframe
from models.DecisionTreeAgent import DecisionTreeAgent

#print(generate_listed_companies_dataframe(path_to_datasets_folder = './datasets/'))

trader = DecisionTreeAgent()

print(trader.get_dict_of_metrics())



