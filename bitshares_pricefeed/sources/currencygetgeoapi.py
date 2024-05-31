import requests
from . import FeedSource, _request_headers

# https://currency.getgeoapi.com/
# pylint: disable=no-member
# Free Plan: 100 daily requests for Rates !
class Currencygetgeoapi(FeedSource):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.feed = {}

        def _request(self, quote, base):
            url = "https://api.getgeoapi.com/v2/currency/convert?api_key=%s&from=%s&to=%s&amount=1&format=json" % (self.api_key, quote, base)
            response = requests.get(url=url, headers=_request_headers, timeout=self.timeout)
            return response

        def _checkAdd(self, quote, base, response, result):

            if (response.status_code != 200):
                raise Exception('Status code in Currencygetgeoapi not 200')

            if (response.status_code == 200) and (result['status'] == 'success'):
                if quote == base:
                    return
                curr = 1 / float(result['rates'][base]['rate'])
                self.add_rate(self.feed, quote, base, curr, 1.0)
            else:
                raise Exception('Unknown error in Currencygetgeoapi')

        def _fetch(self):
            for base in self.bases:
                for quote in self.quotes:
                    if quote == base:
                        continue

                    response = self._request(quote, base)
                    result = response.json()
                    self._checkAdd(quote, base, response, result)

            return self.feed