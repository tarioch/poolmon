from influxdb import InfluxDBClient
import requests
import yaml
from lxml import html

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
                            'name': name,
                            'algo': algo, 
                            'rate': 0
                        }
                    workers[key]['rate'] += hashrate
    return workers

def active(pool, worker):
    return {
        'measurement': 'hashrate',
        'tags': {
            'pool': pool,
            'worker': worker['name'],
            'algo': worker['algo']
        },
        'fields': {
            'value': worker['rate']
        }
    }

def yiimpRate(rateStr):
    units = {
            'H/s': 1,
            'kH/s': 1000,
            'kS/s': 1000,
            'MH/s': 1000000,
            'GH/s': 1000000000
    }
    parts = rateStr.split()
    rate = 0
    if len(parts) == 2:
        rate = float(parts[0])
        unit = parts[1]
        rate = rate * units[unit]

    return rate

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
        rate = yiimpRate(data[4])
        if rate > 0:
            workers.append({
                'name': name,
                'algo': algo,
                'rate': rate
            })

    return workers

if __name__ == '__main__':
    with open('config.yaml', 'r') as configFile:
        config = yaml.safe_load(configFile)

    defAddress = config['default']['address']
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

    mphActive = mphActive(mphApiKey, coins)
    for key, worker in mphActive.items():
        data.append(active('miningpoolhub', worker))

    client = InfluxDBClient(database='poolmon')
    client.write_points(data)
