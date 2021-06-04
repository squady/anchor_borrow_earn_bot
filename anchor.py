import logging
import os
import asyncio
import inspect

from terra_sdk.client.lcd.api.tx import TxAPI
from terra_sdk.core.auth.data.tx import StdTx
from terra_wallet import TerraWallet
from terra_sdk.core.wasm.msgs import MsgExecuteContract
from terra_sdk.core.coins import Coins
from terra_sdk.core.auth import StdFee
from terra_sdk.core.wasm.msgs import dict_to_b64
from terra_sdk.exceptions import LCDResponseError
from aiogram.utils.markdown import quote_html

from helper import Helper
from terra_chain import TerraChain

BLOCKS_PER_YEAR = 4906443



class AnchorException(Exception):
    def __init__(self, action, code, log):
        self._code = code
        self._log = log
        self._action = action

        super().__init__(log)

    def __str__(self):
        return "❗️ Anchor error: {}\n{} : {}".format(self._action, self._code, self._log)
    
    def to_telegram_str(self):
        return "❗️ Anchor error: <code>{}</code>\n<pre>{} : {}</pre>".format(self._action, self._code, quote_html(self._log))



class Anchor():
    log = logging.getLogger("borrow_bot")

    # chain = chain
    mmMarket = os.environ.get("ANCHOR_mmMarket", "terra15dwd5mj8v59wpj0wvt233mf5efdff808c5tkal")
    mmOverseer = os.environ.get("ANCHOR_mmOverseer", "terra1qljxd0y3j3gk97025qvl3lgq8ygup4gsksvaxv")
    aTerra = os.environ.get("ANCHOR_aTerra", "terra1ajt556dpzvjwl0kl5tzku3fc3p3knkg9mkv8jl")

    async def get_block_height():
        block_info = await TerraChain.chain.tendermint.block_info()
        block_height = int(block_info["block"]["header"]["height"])

        return block_height

    async def get_borrow_value(wallet_address):
        borrow_value = 0
        try:
            query = {"borrower_info": {"borrower": wallet_address, "block_height": await Anchor.get_block_height()}}
            response = await TerraChain.chain.wasm.contract_query(Anchor.mmMarket, query)
            borrow_value = float(response["loan_amount"])


        except LCDResponseError as e:
            Anchor.log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)
            
        except Exception as e:
            raise AnchorException(inspect.currentframe().f_code.co_name, type(e).__name__, e.args[0] if e.args[0] else "")


        return borrow_value


    async def get_borrow_limit(wallet_address):
        borrow_limit = 0
        try:
            query = {"borrow_limit": {"borrower": wallet_address, "block_time": await Anchor.get_block_height()}}
            response = await TerraChain.chain.wasm.contract_query(Anchor.mmOverseer, query)
            borrow_limit = float(response["borrow_limit"])

        except LCDResponseError as e:
            Anchor.log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)
            
        except Exception as e:
            raise AnchorException(inspect.currentframe().f_code.co_name, type(e).__name__, e.args[0] if e.args[0] else "")


        return borrow_limit


    async def get_pending_rewards(wallet_address):
        pending_rewards = 0
        try:
            query = {"borrower_info": {"borrower": wallet_address, "block_height": await Anchor.get_block_height()}}
            response = await TerraChain.chain.wasm.contract_query(Anchor.mmMarket, query)
            pending_rewards = float(response["pending_rewards"])

        except LCDResponseError as e:
            Anchor.log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)
            
        except Exception as e:
            raise AnchorException(inspect.currentframe().f_code.co_name, type(e).__name__, e.args[0] if e.args[0] else "")


        return pending_rewards
                


    async def get_current_tvl(wallet_address, borrow_value = None, borrow_limit = None):
        current_tvl = None
        try:
            if (borrow_value is None):
                borrow_value = await Anchor.get_borrow_value(wallet_address)
            if (borrow_limit is None):
                borrow_limit = await Anchor.get_borrow_limit(wallet_address)

            if (borrow_value != 0 and borrow_limit != 0):
                # (v1*100/v2)
                current_tvl = round((borrow_value * 100) / (borrow_limit * 2), 2)

        except AnchorException as e:
            raise e

        except Exception as e:
            raise AnchorException(inspect.currentframe().f_code.co_name, type(e).__name__, e.args[0] if e.args[0] else "")

        return current_tvl

    async def get_amount_to_repay(wallet_address, target_tvl, borrow_value = None, borrow_limit = None):
        amount_to_repay = None
        try:
            if (borrow_value is None):
                borrow_value = await Anchor.get_borrow_value(wallet_address)
            if (borrow_limit is None):
                borrow_limit = await Anchor.get_borrow_limit(wallet_address)

            amount_to_repay = int(borrow_value - ((target_tvl * (borrow_limit * 2)) / 100))

        except Exception as e:
            Anchor.log.exception(e)
            amount_to_repay = None

        return amount_to_repay

    async def get_amount_to_borrow(wallet_address, target_tvl, borrow_value = None, borrow_limit = None):
        amount_to_borrow = None
        try:
            if (borrow_value is None):
                borrow_value = await Anchor.get_borrow_value(wallet_address)
            if (borrow_limit is None):
                borrow_limit = await Anchor.get_borrow_limit(wallet_address)

            amount_to_borrow = int(((target_tvl * (borrow_limit * 2)) / 100) - borrow_value)

        except Exception as e:
            Anchor.log.exception(e)
            amount_to_borrow = None

        return amount_to_borrow


    async def do_repay_amount(wallet, amount_to_repay):

        query = {"repay_stable": {}}
        tx = await wallet.create_and_sign_tx(
                msgs=[MsgExecuteContract(wallet.key.acc_address,
                                            contract=Anchor.mmMarket,
                                            execute_msg=query,
                                            coins=Coins(uusd=amount_to_repay))],
                gas_prices="1uusd",
                gas_adjustment="1.2",
                fee_denoms=["uusd"])


        result = await TerraChain.chain.tx.broadcast(tx)
        if (result.is_tx_error()):
            raise AnchorException(inspect.currentframe().f_code.co_name, result.code, result.raw_log)

    async def do_borrow_amount(wallet, amount_to_borrow):
        query = {"borrow_stable": {"borrow_amount": str(amount_to_borrow), "to": wallet.key.acc_address}}
        tx = await wallet.create_and_sign_tx(
                msgs=[MsgExecuteContract(wallet.key.acc_address,
                                            contract=Anchor.mmMarket,
                                            execute_msg=query)],
                gas_prices="1uusd",
                gas_adjustment="1.2",
                fee_denoms=["uusd"])

        result = await TerraChain.chain.tx.broadcast(tx)
        if (result.is_tx_error()):
            raise AnchorException(inspect.currentframe().f_code.co_name, result.code, result.raw_log)

    async def do_withdraw_from_earn(wallet, amount_to_withdraw):
        b64 = dict_to_b64({"redeem_stable": {}})
        msg = {"send": {"contract": Anchor.mmMarket,"amount": str(amount_to_withdraw), "msg": b64}}
        tx = await wallet.create_and_sign_tx(
                msgs=[MsgExecuteContract(wallet.key.acc_address,
                                            contract=Anchor.aTerra,
                                            execute_msg=msg)],
                gas_prices="1uusd",
                gas_adjustment="1.2",
                fee_denoms=["uusd"])

        result = await TerraChain.chain.tx.broadcast(tx)
        if (result.is_tx_error()):
            raise AnchorException(inspect.currentframe().f_code.co_name,result.code, result.raw_log)

    async def do_deposit_to_earn(wallet, amount_to_deposit):
        query = {"deposit_stable": {}}
        tx = await wallet.create_and_sign_tx(
                msgs=[MsgExecuteContract(wallet.key.acc_address,
                                        contract=Anchor.mmMarket,
                                        execute_msg=query,
                                        coins=Coins(uusd=amount_to_deposit))],
                gas_prices="1uusd",
                gas_adjustment="1.2",
                fee_denoms=["uusd"])


        result = await TerraChain.chain.tx.broadcast(tx)
        if (result.is_tx_error()):
            raise AnchorException(inspect.currentframe().f_code.co_name,result.code, result.raw_log)

    async def do_claim_anc_rewards(wallet):

        query = {"claim_rewards": {"to": wallet.key.acc_address}}
        tx = await wallet.create_and_sign_tx(
                msgs=[MsgExecuteContract(wallet.key.acc_address,
                                            contract=Anchor.mmMarket,
                                            execute_msg=query)],
                gas_prices="1uusd",
                gas_adjustment="1.2",
                fee_denoms=["uusd"])

        result = await TerraChain.chain.tx.broadcast(tx)
        if (result.is_tx_error()):
            raise AnchorException(inspect.currentframe().f_code.co_name, result.code, result.raw_log)



    async def get_total_deposit_amount(wallet_address):
        total_deposit = 0
        try:
            query = {"epoch_state": {}}
            response = await TerraChain.chain.wasm.contract_query(Anchor.mmMarket, query)
            exchange_rate = float(response["exchange_rate"])

            query = {"balance": {"address": wallet_address}}
            response = await TerraChain.chain.wasm.contract_query(Anchor.aTerra, query)
            balance = float(response["balance"])

            total_deposit = exchange_rate * balance


        except LCDResponseError as e:
            Anchor.log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)
            
        except Exception as e:
            raise AnchorException(inspect.currentframe().f_code.co_name, type(e).__name__, e.args[0] if e.args[0] else "")


        return total_deposit



    async def get_earn_apy():
        earn_apy = None
        try:

            query = {"epoch_state": {}}
            response = await TerraChain.chain.wasm.contract_query(Anchor.mmOverseer, query)
            deposit_rate = float(response["deposit_rate"])

            earn_apy = round(deposit_rate * BLOCKS_PER_YEAR * 100,2)


        except Exception as e:
            Anchor.log.exception(e)
            earn_apy = None

        return earn_apy

