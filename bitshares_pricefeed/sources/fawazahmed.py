import requests
from . import FeedSource, _request_headers


class Fawazahmed(FeedSource):
    def _fetch(self):
        feed = {}
        url = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{base}.min.json"
        for base in self.bases:
            response = requests.get(
                url=url.format(base=base.lower()),
                headers=_request_headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            rates = payload.get(base.lower()) or {}
            for quote in self.quotes:
                if quote == base:
                    continue
                price = float(rates[quote.lower()])
                if not price > 0:
                    raise Exception("Fawazahmed bad price %s" % quote)
                self.add_rate(feed, quote, base, price, 1.0)
        if not feed:
            raise Exception("Fawazahmed returned no rates")
        return feed
