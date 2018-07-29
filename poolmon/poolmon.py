from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, REGISTRY 
import requests
import yaml
import json
from yiimp import Yiimp
from miningpoolhub import MiningPoolHub
import time

def coinInfo():
    response = requests.get('https://miningpoolhub.com/index.php?page=api&action=getminingandprofitsstatistics')
    coins = {} 
    if response.status_code == 200:
        data = response.json()
        for coin in data['return']:
            name = coin['coin_name']
            coins[name] = {
                'name': name,
                'algo': coin['algo'].lower(),
                'price': coin['highest_buy_price']
            }

    return coins

def extractRate(rateStr):
    if isinstance(rateStr, float):
        return rateStr
    elif isinstance(rateStr, int):
        return float(rateStr)

    units = {
            'h/s': 1,
            'kh/s': 1000,
            'ks/s': 1000,
            'mh/s': 1000000,
            'gh/s': 1000000000,
            'th/s': 1000000000000,
            'ph/s': 1000000000000000,
    }

    rateStr = rateStr.replace(',', '.')
    parts = rateStr.split()
    rate = 0
    if len(parts) == 2:
        rate = float(parts[0])
        unit = parts[1].lower()
        rate = rate * units[unit]

    return float(rate)

class CustomCollector(object):
    def collect(self):
        print('Fetching APIs')

        coins = coinInfo()

        bal = GaugeMetricFamily('tarioch_poolmon_balance', 'Pool Balance', labels=['pool'])
        activity = GaugeMetricFamily('tarioch_poolmon_activity', 'Pool Activity', labels=['pool', 'worker', 'algo', 'miner'])

        for pool in config['pools']:
            name = pool['name']

            type = pool['type']
            if 'yiimp' == type:
                fetcher = Yiimp()
            elif 'miningpoolhub' == type:
                fetcher = MiningPoolHub()
            else:
                raise ValueError('Invalid type ' + type + ' for pool ' + name)

            try:
                amt = fetcher.balance(pool, coins)
                if amt > 0:
                    bal.add_metric([name], amt)

                workers = fetcher.workers(pool, coins)
                for worker in workers:
                    activity.add_metric([
                        name, 
                        worker['name'].lower().strip(), 
                        worker['algo'].lower().strip(), 
                        worker['miner'].lower().strip()], 
                        extractRate(worker['rate']))

            except ValueError as e:
                print(e)

        yield bal
        yield activity

if __name__ == '__main__':
    with open('config.yaml', 'r') as configFile:
        config = yaml.safe_load(configFile)

    REGISTRY.register(CustomCollector())

    start_http_server(8000)

    while True:
        time.sleep(10)

