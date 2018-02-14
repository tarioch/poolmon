from influxdb import InfluxDBClient
import requests
import yaml
import json
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from yiimp import Yiimp
from miningpoolhub import MiningPoolHub

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

def balance(pool, amount):
    return {
        'measurement': 'balance',
        'tags': {
            'pool': pool
        },
        'fields': {
            'value': amount
        }
    }

def active(pool, worker):
    return createActivity(
        'pool',
        pool,
        worker['name'],
        None,
        worker['algo'],
        worker['miner'],
        worker['rate']
    )

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

def createActivity(src, pool, worker, workertype=None, algo=None, miner=None, currentHashrate=None, estimatedHashrate=None, income=None):
    result = {}
    result['measurement'] = 'activity'

    tags = {}
    tags['pool'] = pool.lower()
    tags['worker'] = worker.lower()
    if workertype:
        tags['workertype'] = workertype.lower().strip()
    if algo:
        tags['algo'] = algo.lower().strip()
    if miner:
        tags['miner'] = miner.lower().strip()
    tags['src'] = src

    result['tags'] = tags

    fields = {}
    if currentHashrate:
        fields['currenthashrate'] = extractRate(currentHashrate)
    if estimatedHashrate:
        fields['estimatedhashrate'] = extractRate(estimatedHashrate)
    if income:
        if isinstance(income, float):
            fields['income'] = income
        else:
            fields['income'] = float(income.replace(',', '.'))
    result['fields'] = fields

    return result

def fetchApis():
    print('Fetching APIs')

    coins = coinInfo()

    client = InfluxDBClient(database='poolmon')
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
                data = []
                data.append(balance(name, amt))
                client.write_points(data)

            data = []
            workers = fetcher.workers(pool, coins)
            for worker in workers:
                data.append(active(name, worker))

            client.write_points(data)
        except ValueError as e:
            print(e)

app = Flask(__name__)

@app.route('/',methods=['POST'])
def handle():
    worker = request.form['workername']
    miners = json.loads(str(request.form['miners']))

    data = []
    for miner in miners:
        for i in range(0, len(miner['Algorithm'])):
            data.append(stats(worker, miner, i))

    client = InfluxDBClient(database='poolmon')
    client.write_points(data)
    print(data)

    return 'ok'

def stats(worker, miner, index):
    return createActivity(
        'mpm',
        miner['Pool'][index],
        worker,
        miner['Type'][index],
        miner['Algorithm'][index],
        miner['Name'],
        miner['CurrentSpeed'][index],
        miner['EstimatedSpeed'][index],
        miner['BTC/day'] if index == 0 else None
    )
    
if __name__ == '__main__':
    with open('config.yaml', 'r') as configFile:
        config = yaml.safe_load(configFile)

    fetchApis()
    pollInterval = config['poll_interval']
    if pollInterval > 0:
        scheduler = BackgroundScheduler()
        scheduler.add_job(fetchApis, 'interval', minutes=pollInterval)
        scheduler.start()

    app.run(host=config['host'], port=config['port'], threaded=True)
