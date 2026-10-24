#!/usr/bin/env python3

import sys
import click
import os
import logging
from pprint import pprint
from .feed_price import feed_price
from bitshares.account import Account
# from bitshares.asset import Asset
from .pricefeed import Feed
from uptick.decorators import (
    # verbose,
    chain,
    unlock,
)
from .ui import (
    configfile,
    print_log,
    print_prices,
    print_premium_details,
    confirmwarning,
    confirmalert,
    alert,
)
log = logging.getLogger(__name__)


@click.group()
@click.option(
    "--configfile",
    default="config.yml",
    # type=click.File('r'),
)
@click.option(
    "--node",
    metavar='<wss://host:port>',
    help="Node to connect to",
)
@click.pass_context
def main(ctx, **kwargs):
    ctx.obj = {}
    for k, v in kwargs.items():
        ctx.obj[k] = v


@main.command()
@click.pass_context
@chain
@click.argument(
    "key",
    nargs=-1
)
@unlock
def addkey(ctx, key):
    """ Add a private key to the wallet
    """
    if not key:
        while True:
            key = click.prompt(
                "Private Key (wif) [Enter to quit]",
                hide_input=True,
                show_default=False,
                default="exit"
            )
            if not key or key == "exit":
                break
            try:
                ctx.bitshares.wallet.addPrivateKey(key)
            except Exception as e:
                click.echo(str(e))
                continue
    else:
        for k in key:
            try:
                ctx.bitshares.wallet.addPrivateKey(k)
            except Exception as e:
                click.echo(str(e))

    installedKeys = ctx.bitshares.wallet.getPublicKeys()
    if len(installedKeys) == 1:
        name = ctx.bitshares.wallet.getAccountFromPublicKey(installedKeys[0])
        if name:  # only if a name to the key was found
            account = Account(name, bitshares_instance=ctx.bitshares)
            click.echo("=" * 30)
            click.echo("Setting new default user: %s" % account["name"])
            click.echo()
            click.echo("You can change these settings with:")
            click.echo("    uptick set default_account <account>")
            click.echo("=" * 30)
            ctx.bitshares.set_default_account(account["name"])


@main.command()
@click.argument(
    "example",
    default="default"
)
@click.pass_context
def create(ctx, example):
    """ Create config file
    """
    import shutil
    this_dir, _ = os.path.split(__file__)
    default_config_file = os.path.join(this_dir, "examples", example + ".yaml")
    config_file = ctx.obj["configfile"]
    shutil.copyfile(
        default_config_file,
        config_file
    )
    click.echo("Config file created: %s" % config_file)



def configure_dry_run(ctx, param, value):
    if value:
        ctx.obj['unsigned'] = True
    return value

def configure_active_key(ctx, param, value):
    if value:
        ctx.obj['keys'] = { 'active': value }
        ctx.obj['unsigned'] = True

@main.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Only compute prices and print result, no publication.",
    default=False,
    callback=configure_dry_run,
    is_eager=True
)
@click.option(
    "--active-key",
    metavar='WIF',
    help="Active key to be used to sign transactions.",
    callback=configure_active_key,
    expose_value=False, 
    is_eager=True
)
@click.option(
    "--confirm-warning/--no-confirm-warning",
    help="Need for manual confirmation of warnings",
    default=True,
)
@click.option(
    "--skip-critical/--no-skip-critical",
    help="Skip critical feeds",
    default=False,
)
@click.pass_context
@configfile
@chain
@unlock
@click.argument(
    "assets",
    nargs=-1,
    required=False,
)
def update(ctx, assets, dry_run, confirm_warning, skip_critical):
    """ Update price feed for assets
    """
    exitcode = 0

    # Do i have a producer?
    assert "producer" in ctx.config and ctx.config["producer"], \
        "Please provide a feed producer name in the configuration!"

    feed = Feed(config=ctx.config, dry_run=dry_run)
    feed.fetch()
    feed.derive(assets)
    prices = feed.get_prices()
    print_log(prices)
    print_prices(prices)
    print_premium_details(prices)

    if dry_run:
        return

    # Bundle all operation in one transaction.
    ctx.bitshares.bundle = True
    # Assert that we sign the transactions.
    ctx.bitshares.unsigned = False

    for symbol, price in prices.items():
        # Skip empy symbols
        if not price:
            continue

        flags = price["flags"]

        if "skip_inactive_witness" in flags:
            alert("Witness is inactive, skipping {}.".format(symbol))
            continue

        # Prices that don't move sufficiently, or are not too old, can
        # be skipped right away
        if "min_change" not in flags and "over_max_age" not in flags:
            print('Price of %s did not moved sufficiently (%.2f%%). Skipping!' % (symbol, price['priceChange']))
            continue

        if "min_change" not in flags and "over_max_age" in flags:
            print('Price of %s is tool old, forcing republication.' % (symbol, ))

        if (
            confirm_warning and
            "over_warn_change" in flags and
            "skip_change" not in flags
        ):
            if not confirmwarning(
                "Price change for %s (%f) has been above 'warn_change'.  Please confirm!" % (
                    symbol,
                    price["priceChange"]
                )
            ):
                continue

        if "skip_change" in flags:
            if skip_critical:
                alert(
                    "Price change for %s (%f) has been above 'skip_change'.  Skipping!" % (
                        symbol,
                        price["priceChange"],
                    )
                )
                exitcode = 1
                continue
            else:
                if not confirmalert(
                    "Price change for %s (%f) has been above 'skip_change'. Please confirm to still publish, else feed will be skipped!" % (
                        symbol,
                        price["priceChange"],
                    )
                ):
                    continue

        # Prices are denoted in `base`/`quote`. For a bitUSD feed, we
        # want something like    0.05 USD per BTS. This makes "USD" the
        # `base` and BTS the `quote`.
        settlement_price = feed_price(
            price["price"],
            symbol,
            price["short_backing_symbol"])
        cer = feed_price(
            price["cer"],
            symbol,
            price["short_backing_symbol"])
        ctx.bitshares.publish_price_feed(
            symbol,
            settlement_price=settlement_price,
            cer=cer,
            mssr=price["mssr"],
            mcr=price["mcr"],
            account=ctx.config["producer"]
        )

    ctx.bitshares.txbuffer.constructTx()
    pprint(ctx.bitshares.txbuffer.json())

    # Always ask for confirmation if this flag is set to true
    if "confirm" in ctx.config and ctx.config["confirm"]:
        if not confirmwarning(
            "Please confirm"
        ):
            return

    if ctx.bitshares.txbuffer.ops:
        ctx.bitshares.txbuffer.broadcast()

    sys.exit(exitcode)


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
