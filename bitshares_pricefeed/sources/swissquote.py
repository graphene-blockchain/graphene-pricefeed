import requests
from . import FeedSource, _request_headers


class Swissquote(FeedSource):
    def _fetch(self):
        feed = {}
        url = "https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/{quote}/{base}"
        for base in self.bases:
            for quote in self.quotes:
                if quote == base:
                    continue
                response = requests.get(
                    url=url.format(quote=quote.upper(), base=base.upper()),
                    headers=_request_headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                rows = response.json()
                if not rows:
                    raise Exception("Swissquote empty %s/%s" % (quote, base))
                level = rows[0].get("spreadProfilePrices") or []
                if not level:
                    raise Exception("Swissquote no price %s/%s" % (quote, base))
                bid = float(level[0].get("bid") or 0)
                ask = float(level[0].get("ask") or 0)
                if bid > 0 and ask > 0:
                    price = (bid + ask) / 2.0
                else:
                    price = bid or ask
                if not price > 0:
                    raise Exception("Swissquote bad price %s/%s" % (quote, base))
                self.add_rate(feed, base, quote, price, 1.0)
        if not feed:
            raise Exception("Swissquote returned no rates")
        return feed
