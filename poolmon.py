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

def mph(mphkey, coins):
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


if __name__ == '__main__':
    with open('config.yaml', 'r') as configFile:
        config = yaml.safe_load(configFile)

    defAddress = config['default']['address']

    coins = coinInfo()

    data = []

    for pool in config['yiimppools']:
        amt = yiimp(pool['url'], defAddress)
        if amt > 0:
            data.append(balance(pool['name'], amt))

    mph = mph(config['miningpoolhub']['apikey'], coins)
    if mph > 0:
        data.append(balance('miningpoolhub', mph))

    client = InfluxDBClient(database='poolmon')
    client.write_points(data)
