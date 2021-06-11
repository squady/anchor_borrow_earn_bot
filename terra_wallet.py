from terra_sdk.key.mnemonic import MnemonicKey
from terra_chain import TerraChain
from helper import Helper
from config import Config


class TerraWallet:
    def __init__(self, wallet_name, mnemonic):

        self._mnemonic = mnemonic
        self._wallet_name = wallet_name
        self._wallet = TerraChain.chain.wallet(MnemonicKey(self._mnemonic))
        self._base_explorer_url = "{}/{}".format(
            Config._finder_base_url,
            TerraChain.chain.chain_id,
        )

    def get_wallet_name(self):
        return self._wallet_name

    def get_wallet_address(self):
        return self._wallet.key.acc_address

    def get_wallet_url(self):
        return "{}/address/{}".format(
            self._base_explorer_url, self.get_wallet_address()
        )

    async def get_uusd_amount(self):
        balance = 0
        try:
            coins = await TerraChain.chain.bank.balance(self._wallet.key.acc_address)
            coin = coins.get("uusd")
            balance = coin.amount

        except Exception as e:
            Config._log.exception(e)
            balance = 0

        return balance
