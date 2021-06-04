import logging
import base64
from cryptography.fernet import Fernet
from terra_sdk.key.mnemonic import MnemonicKey
from terra_chain import TerraChain

key = b'dctiGhR5jsXTUWlitZTW_Ez3h4Ef0ezKvVGUuuQLrd0='



class TerraWallet:
    def __init__(self, wallet_name, mnemonic):
        self._log = logging.getLogger("borrow_bot")

        cipher_suite = Fernet(key)        
        # self._mnemonic = cipher_suite.decrypt(encrypted_mnemnic).decode('utf-8')
        self._mnemonic = mnemonic
        self._wallet = TerraChain.chain.wallet(MnemonicKey(self._mnemonic))
        self._base_explorer_url = "https://finder.terra.money/{}".format(TerraChain.chain.chain_id)



    def get_wallet_address(self):
        return self._wallet.key.acc_address

    def get_wallet_url(self):
        return "{}/address/{}".format(self._base_explorer_url, self.get_wallet_address())

    async def get_uusd_amount(self):
        balance = 0
        try:
            coins = await TerraChain.chain.bank.balance(self._wallet.key.acc_address)
            coin = coins.get("uusd")
            balance = coin.amount

        except Exception as e:
            self._log.exception(e)

        return balance
