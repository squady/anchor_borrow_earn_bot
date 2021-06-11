from config import Config
from terra_sdk.client.lcd import AsyncLCDClient


class TerraChain:
    chain = AsyncLCDClient(chain_id=Config._chain_id, url=Config._chain_url)

    @staticmethod
    async def estimate_fee(tx):
        fees = None
        try:

            fees = await TerraChain.chain.tx.estimate_fee(
                tx, gas_prices="2uusd", fee_denoms=["uusd"]
            )
            fees.gas = max(fees.gas, 1000000)

        except Exception as e:
            Config._log.exception(e)
            fees = None

        return fees
