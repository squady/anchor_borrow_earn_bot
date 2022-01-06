from terra_sdk.core.auth.data.tx import StdFee
from config import Config
from terra_sdk.client.lcd import AsyncLCDClient
import requests


class TerraChain:
    chain = AsyncLCDClient(chain_id=Config._chain_id, url=Config._chain_url)

    @staticmethod
    async def estimate_fee(wallet_address, msgs, usd_gas_price = None):
        fees = None
        try:
            if usd_gas_price is None:
                usd_gas_price = TerraChain.get_gas_price()

                fees = await TerraChain.chain.tx.estimate_fee(
                    wallet_address,
                    msgs,
                    "",
                    None,
                    gas_prices={"uusd": usd_gas_price},
                    gas_adjustment=1.8,
                    fee_denoms=["uusd"],
                )
            else:
                fees = StdFee(
                    1000000,
                    {"uusd": int(usd_gas_price * 1000000)},
                )

        except Exception as e:
            Config._log.exception(e)
            fees = None

        return fees

    @staticmethod
    def get_trx_url(txhash):
        try:
            return "{}/{}/tx/{}".format(
                Config._finder_base_url,
                TerraChain.chain.chain_id,
                txhash,
            )

        except Exception as e:
            Config._log.exception(e)

    @staticmethod
    def get_gas_price():
        gas_price = 2
        try:
            url = "https://fcd.terra.dev/v1/txs/gas_prices"
            res = requests.get(url)
            gas_price = res.json()["uusd"]

        except Exception as e:
            Config._log.exception(e)
            gas_price = 2

        return gas_price
