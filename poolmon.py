from influxdb import InfluxDBClient
import requests
import yaml

def yiimp(url, address):
    response = requests.get(url + '/api/wallet?address=' + address)
    if response.status_code == 200:
        data = response.json()
        return data['unpaid']
    else:
        return 0

def ratelookup(currency):
    response = requests.get('https://api.coinmarketcap.com/v1/ticker/' + currency + '/')
    if response.status_code == 200:
        data = response.json()[0]
        return float(data['price_btc'])

    return 0

def all(coin):
    total = 0
    total += coin['confirmed']
    total += coin['unconfirmed']
    total += coin['ae_confirmed']
    total += coin['ae_unconfirmed']
    total += coin['exchange']
    return total

def mph(mphkey):
    response = requests.get('https://miningpoolhub.com/index.php?page=api&action=getuserallbalances&api_key=' + mphkey)
    if response.status_code == 200:
        data = response.json()
        coins = data['getuserallbalances']['data']
        total = 0
        for coin in coins:
            cur = coin['coin']
            sum = all(coin)
            rate = ratelookup(cur)
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


if __name__ == '__main__':
    with open('config.yaml', 'r') as configFile:
        config = yaml.safe_load(configFile)

    defAddress = config['default']['address']

    data = []

    for pool in config['yiimppools']:
        amt = yiimp(pool['url'], defAddress)
        if amt > 0:
            data.append(balance(pool['name'], amt))

    mph = mph(config['miningpoolhub']['apikey'])
    if mph > 0:
        data.append(balance('miningpoolhub', mph))

    client = InfluxDBClient(database='poolmon')
    client.write_points(data)
