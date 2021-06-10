from config import Config
import os
from terra_sdk.client.lcd import AsyncLCDClient




class TerraChain:
    chain = AsyncLCDClient(chain_id=Config._chain_id, 
                            url=Config._chain_url)

