from influxdb import InfluxDBClient
import requests
import yaml
from lxml import html
import json
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler

def yiimpBalance(url, address):
    response = requests.get(url + '/api/wallet?address=' + address)
    if response.status_code == 200:
        data = response.json()
        return data['unpaid']
    else:
        return 0

def all(coin):
    total = 0
    total += coin['confirmed']
    total += coin['unconfirmed']
    total += coin['ae_confirmed']
    total += coin['ae_unconfirmed']
    total += coin['exchange']
    return total

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

def mphBalance(mphkey, coins):
    response = requests.get('https://miningpoolhub.com/index.php?page=api&action=getuserallbalances&api_key=' + mphkey)
    if response.status_code == 200:
        data = response.json()
        balances = data['getuserallbalances']['data']
        total = 0
        for balance in balances:
            cur = balance['coin']
            sum = all(balance)
            rate = coins[cur]['price']
            total += sum * rate
            return total

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

def mphActive(mphkey, coins):
    workers = {} 
    for coinName, coin in coins.items():
        response = requests.get('https://' + coin['name'] + '.miningpoolhub.com/index.php?page=api&action=getuserworkers&api_key=' + mphkey)
        if response.status_code == 200:
            data = response.json()
            for worker in data['getuserworkers']['data']:
                hashrate = worker['hashrate']
                if hashrate > 0:
                    name = worker['username'].split('.')[1]
                    algo = coin['algo']
                    key = name + '_' + algo 
                    if not key in workers:
                        workers[key] = {
                            'miner': None,
                            'name': name,
                            'algo': algo, 
                            'rate': 0
                        }
                    workers[key]['rate'] += hashrate
    return workers

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

def yiimpActive(url, address):
    response = requests.get(url + '/site/wallet_miners_results?address=' + address)
    root = html.fromstring(response.content)
    rows = root.xpath('//table[last()]/tr')
    workers = []
    for row in rows:
        data = []
        for cell in row.xpath('.//td/text()'):
            data.append(cell)

        name = data[1].split(',')[0]
        algo = data[2]
        rate = data[4]
        workers.append({
            'miner': data[0],
            'name': name,
            'algo': algo,
            'rate': rate
        })

    return workers

def fetchApis():
    print('Fetching APIs')

    defAddress = config['default_address']
    mphApiKey = config['miningpoolhub']['apikey']

    coins = coinInfo()

    data = []

    for pool in config['yiimppools']:
        name = pool['name']
        url = pool['url']
        workers = yiimpActive(url, defAddress)
        for worker in workers:
            data.append(active(name, worker))
        amt = yiimpBalance(url, defAddress)
        if amt > 0:
            data.append(balance(name, amt))

    mph = mphBalance(mphApiKey, coins)
    if mph > 0:
       data.append(balance('miningpoolhub', mph))

    workers = mphActive(mphApiKey, coins)
    for key, worker in workers.items():
        data.append(active('miningpoolhub', worker))

    client = InfluxDBClient(database='poolmon')
    print(data)
    client.write_points(data)

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
    
def createActivity(src, pool, worker, workertype=None, algo=None, miner=None, currentHashrate=None, estimatedHashrate=None, income=None):
    result = {}
    result['measurement'] = 'activity'

    tags = {}
    tags['pool'] = pool.lower()
    tags['worker'] = worker.lower()
    if workertype:
        tags['workertype'] = workertype.lower()
    if algo:
        tags['algo'] = algo.lower()
    if miner:
        tags['miner'] = miner.lower()
    tags['src'] = src

    result['tags'] = tags

    fields = {}
    if currentHashrate:
        fields['currenthashrate'] = extractRate(currentHashrate)
    if estimatedHashrate:
        fields['estimatedhashrate'] = extractRate(estimatedHashrate)
    if income:
        fields['income'] = float(income.replace(',', '.'))
    result['fields'] = fields

    return result

if __name__ == '__main__':
    with open('config.yaml', 'r') as configFile:
        config = yaml.safe_load(configFile)

    pollInterval = config['poll_interval']
    if pollInterval > 0:
        scheduler = BackgroundScheduler()
        scheduler.add_job(fetchApis, 'interval', minutes=pollInterval)
        scheduler.start()

    app.run(host=config['host'], port=config['port'], threaded=True)
