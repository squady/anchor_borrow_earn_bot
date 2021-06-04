import os

from terra_sdk.client.lcd import AsyncLCDClient




class TerraChain:
    chain = AsyncLCDClient(chain_id=os.environ.get("CHAIN_ID", "tequila-0004"), 
                            url=os.environ.get("CHAIN_URL", "https://tequila-lcd.terra.dev"))

