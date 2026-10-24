import requests
from . import FeedSource, _request_headers


class OpenErApi(FeedSource):
    def _fetch(self):
        feed = {}
        url = "https://open.er-api.com/v6/latest/{base}"
        for base in self.bases:
            response = requests.get(
                url=url.format(base=base.upper()),
                headers=_request_headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()
            if result.get("result") != "success":
                raise Exception("OpenErApi result %s" % result.get("result"))
            rates = result.get("rates") or {}
            for quote in self.quotes:
                if quote == base:
                    continue
                price = float(rates[quote.upper()])
                if not price > 0:
                    raise Exception("OpenErApi bad price %s" % quote)
                self.add_rate(feed, quote, base, price, 1.0)
        if not feed:
            raise Exception("OpenErApi returned no rates")
        return feed
