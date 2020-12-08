from models.DecisionTreeAgent import DecisionTreeAgent
from models.DummyAgent import DummyAgentBacktest,DummyAgentOperations
from models.DQNAgent import DQNAgentBacktest,DQNAgentOperations
#from models.PPOAgent import PPOWolfOfWallstreet, PPOChicken
import argparse
from utils import make_dir
#print(generate_listed_companies_dataframe(path_to_datasets_folder = './datasets/'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--agent', type=str, choices=['decisionTree', 'dqn', 'dummy', 'ppo'], required=True, help='either an agent type: "dqn", "dummy" or "decisionTree')
    parser.add_argument('-m', '--mode', type=str, choices=['makeMeRich', 'train'], help='either "train" or "makeMeRich"')
    # parser.add_argument('-w', '--weights', type=str, help='a trained model weights')
    args = parser.parse_args()

    make_dir('weights')

    # build trader
    if args.agent == 'dummy':
        if args.mode == 'train':
            trader = DummyAgentBacktest()
        else:
            trader = DQNAgentOperations()
    elif args.agent == 'decisionTree':
        trader = DecisionTreeAgent()
    elif args.agent == 'dqn':
        if args.mode =='train':
            trader = DQNAgentBacktest()
        else:
            trader = DQNAgentOperations()

    # elif args.agent == 'ppo':
    #     trader = PPOWolfOfWallstreet() if args.mode == 'makeMeRich' else PPOChicken()

    print("Bora")
    trader._run_operations()
   

#trader = DQNAgent()
#trader._run_operations()


