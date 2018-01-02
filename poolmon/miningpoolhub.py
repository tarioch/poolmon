import requests

class MiningPoolHub:
    def balance(self, config, coins):
        response = requests.get('https://miningpoolhub.com/index.php?page=api&action=getuserallbalances&api_key=' + config['key'])
        if response.status_code == 200:
            data = response.json()
            balances = data['getuserallbalances']['data']
            total = 0
            for balance in balances:
                cur = balance['coin']
                sum = self.__all(balance)
                rate = coins[cur]['price']
                total += sum * rate

            return total

    def __all(self, coin):
        total = 0
        total += coin['confirmed']
        total += coin['unconfirmed']
        total += coin['ae_confirmed']
        total += coin['ae_unconfirmed']
        total += coin['exchange']
        return total

    def workers(self, config, coins):
        mphkey = config['key']
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
        return workers.values()

