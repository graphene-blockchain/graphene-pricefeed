"""Build a feed price the chain can store.

The stock Price() helper keeps only fractions whose denominator is at most
10**asset_precision. GOLD and SILVER per 1 GPH are smaller than that tick,
so the fraction becomes 0. One base unit over an integer number of quote
units still fits in the chain integers, and Price.json() keeps it.
"""

from fractions import Fraction


def naive_fraction(value, base_precision):
    return Fraction(float(value)).limit_denominator(10 ** int(base_precision))


def satoshi_quote(value, base_precision, quote_precision):
    """Quote units for a price made of exactly 1 base unit."""
    scaled = float(value) * (10 ** int(base_precision)) / (10 ** int(quote_precision))
    if not scaled > 0:
        raise ValueError("non-positive feed price")
    quote_sat = int(round(1.0 / scaled))
    if quote_sat < 1 or quote_sat > 2 ** 62:
        raise ValueError("feed price does not fit in chain integers")
    return quote_sat


def feed_price(value, base_symbol, quote_symbol):
    from bitshares.amount import Amount
    from bitshares.asset import Asset
    from bitshares.price import Price

    value = float(value)
    if not value > 0:
        raise ValueError("non-positive feed price for %s" % base_symbol)
    base = Asset(base_symbol)
    quote = Asset(quote_symbol)
    if naive_fraction(value, base["precision"]).numerator > 0:
        return Price(value, base=base_symbol, quote=quote_symbol)
    base_prec = int(base["precision"])
    quote_prec = int(quote["precision"])
    quote_sat = satoshi_quote(value, base_prec, quote_prec)
    base_amount = Amount(amount=1 / (10 ** base_prec), asset=base)
    quote_amount = Amount(amount=quote_sat / (10 ** quote_prec), asset=quote)
    return Price(base=base_amount, quote=quote_amount)
