import requests
from . import FeedSource, _request_headers


class GoldApiCom(FeedSource):
    def _fetch(self):
        feed = {}
        url = "https://api.gold-api.com/price/{quote}"
        for base in self.bases:
            if base.upper() != "USD":
                continue
            for quote in self.quotes:
                if quote == base:
                    continue
                response = requests.get(
                    url=url.format(quote=quote.upper()),
                    headers=_request_headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                result = response.json()
                price = float(result["price"])
                if not price > 0:
                    raise Exception("GoldApiCom bad price %s" % quote)
                self.add_rate(feed, base, quote, price, 1.0)
        if not feed:
            raise Exception("GoldApiCom returned no rates")
        return feed
