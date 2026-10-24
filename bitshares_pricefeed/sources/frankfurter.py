import requests
from . import FeedSource, _request_headers


class Frankfurter(FeedSource):
    def _fetch(self):
        feed = {}
        url = "https://api.frankfurter.app/latest?from={base}&to={quotes}"
        for base in self.bases:
            quotes = [quote for quote in self.quotes if quote != base]
            if not quotes:
                continue
            response = requests.get(
                url=url.format(base=base.upper(), quotes=",".join(quote.upper() for quote in quotes)),
                headers=_request_headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            rates = response.json().get("rates") or {}
            for quote in quotes:
                price = float(rates[quote.upper()])
                if not price > 0:
                    raise Exception("Frankfurter bad price %s" % quote)
                self.add_rate(feed, quote, base, price, 1.0)
        if not feed:
            raise Exception("Frankfurter returned no rates")
        return feed
