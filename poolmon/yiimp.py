import requests
from lxml import html

class Yiimp:
    def balance(self, config, coins):
        url = config['url']
        amt = 0
        for address in config['addresses']:
            amt += self.saveFetchBalance(url, address, coins)

        return amt

    def saveFetchBalance(self, url, address, coins):
        for i in range(0, 3):
            amt = self.fetchBalance(url, address, coins)
            if amt > 0:
                return amt

        raise ValueError('Not able to fetch an amount')

    def fetchBalance(self, url, address, coins):
        print(url + '/api/wallet?address=' + address)
        response = requests.get(url + '/api/wallet?address=' + address)
        print(response.text)
        if response.status_code == 200 and response.text.strip():
            try:
                data = response.json()
                unpaid = data['unpaid']
                cur = data['currency']
                if cur == 'BTC':
                    cur = 'bitcoin'
                elif cur == 'LTC':
                    cur = 'litecoin'
                print(unpaid)
                rate = coins[cur]['price']
                return unpaid * rate 
            except:
                print(response.text)
                raise
        else:
            print(response.text)
            return 0

    def workers(self, config, coins):
        url = config['url']
        workers = []
        for address in config['addresses']:
            try:
                print(url + '/site/wallet_miners_results?address=' + address)
                response = requests.get(url + '/site/wallet_miners_results?address=' + address)
                if response.content.strip():
                    root = html.fromstring(response.content)
                    rows = root.xpath('//table[last()]/tr')
                    for row in rows:
                        data = []
                        for cell in row.xpath('.//td/text()'):
                            data.append(cell)

                        if len(data) >= 5:
                            name = data[1].split(',')[0]
                            algo = data[2]
                            rate = data[4]
                            workers.append({
                                'miner': data[0],
                                'name': name,
                                'algo': algo,
                                'rate': rate
                            })
            except:
                print(response.content)
                raise

        return workers

