import requests
from lxml import html

class Yiimp:
    def balance(self, config, coins):
        url = config['url']
        amt = 0
        for address in config['addresses']:
            response = requests.get(url + '/api/wallet?address=' + address)
            if response.status_code == 200 and response.text.strip():
                try:
                    data = response.json()
                except:
                    print(response.text)
                    raise

                unpaid = data['unpaid']
                cur = data['currency']
                if cur == 'BTC':
                    cur = 'bitcoin'
                elif cur == 'LTC':
                    cur = 'litecoin'
                rate = coins[cur]['price']
                amt += unpaid * rate 

        return amt

    def workers(self, config, coins):
        url = config['url']
        workers = []
        for address in config['addresses']:
            response = requests.get(url + '/site/wallet_miners_results?address=' + address)
            root = html.fromstring(response.content)
            rows = root.xpath('//table[last()]/tr')
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

