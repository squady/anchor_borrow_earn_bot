import requests
import inspect
from terra_sdk.core.wasm.msgs import MsgExecuteContract
from terra_sdk.core.coins import Coins
from terra_sdk.core.strings import AccAddress
from terra_sdk.core.wasm.msgs import dict_to_b64
from terra_sdk.exceptions import LCDResponseError
from aiogram.utils.markdown import quote_html
from terra_chain import TerraChain
from config import Config





class AnchorException(Exception):
    def __init__(self, action, code, message):
        self._code = code
        self._message = message
        self._action = action

        super().__init__(message)

    def __str__(self):
        return "❗️ Anchor error: {}\n{} : {}".format(self._action, self._code, self._message)
    
    def to_telegram_str(self):
        return "❗️ Anchor error: <code>{}</code>\n<pre>{} : {}</pre>".format(self._action, self._code, quote_html(self._message))



class Anchor():

    async def get_config():
        try:

            query = {"config": {}}
            response = await TerraChain.chain.wasm.contract_query(Config._address["mmMarket"], query)
            for val in response:
                Config._address[val] = response[val]



        except LCDResponseError as e:
            Config._log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)
            



    async def get_block_height():

        block_info = await TerraChain.chain.tendermint.block_info()
        block_height = int(block_info["block"]["header"]["height"])

        return block_height

    async def get_borrow_value(wallet_address):
        borrow_value = 0
        try:
            query = {"borrower_info": {"borrower": wallet_address, "block_height": await Anchor.get_block_height()}}
            response = await TerraChain.chain.wasm.contract_query(Config._address["mmMarket"], query)
            borrow_value = float(response["loan_amount"])


        except LCDResponseError as e:
            Config._log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)
            


        return borrow_value


    async def get_borrow_limit(wallet_address):
        borrow_limit = 0
        try:
            query = {"borrow_limit": {"borrower": wallet_address, "block_time": await Anchor.get_block_height()}}
            response = await TerraChain.chain.wasm.contract_query(Config._address["overseer_contract"], query)
            borrow_limit = float(response["borrow_limit"])

        except LCDResponseError as e:
            Config._log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)
            


        return borrow_limit


    async def get_pending_rewards(wallet_address):
        pending_rewards = 0
        try:
            query = {"borrower_info": {"borrower": wallet_address, "block_height": await Anchor.get_block_height()}}
            response = await TerraChain.chain.wasm.contract_query(Config._address["mmMarket"], query)
            pending_rewards = float(response["pending_rewards"])

        except LCDResponseError as e:
            Config._log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)
            


        return pending_rewards
                


    async def get_current_tvl(wallet_address, borrow_value = None, borrow_limit = None):
        current_tvl = None

        if (borrow_value is None):
            borrow_value = await Anchor.get_borrow_value(wallet_address)
        if (borrow_limit is None):
            borrow_limit = await Anchor.get_borrow_limit(wallet_address)

        if (borrow_value != 0 and borrow_limit != 0):
            # (v1*100/v2)
            current_tvl = round((borrow_value * 100) / (borrow_limit * 2), 2)




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
            Config._log.exception(e)
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
            Config._log.exception(e)
            amount_to_borrow = None

        return amount_to_borrow

    async def do_trx(wallet, msgs):
        try:
            tx = await wallet.create_and_sign_tx(msgs=msgs)

            estimated_fees = await TerraChain.estimate_fee(tx)
            tx = await wallet.create_and_sign_tx(msgs=msgs, fee=estimated_fees)

            result = await TerraChain.chain.tx.broadcast(tx)
            if (result.is_tx_error()):
                raise AnchorException(inspect.currentframe().f_code.co_name, result.code, result.raw_log)

        except LCDResponseError as e:
            Config._log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)   
            
    async def get_repay_amount_msg(wallet_address, amount_to_repay):
        try:
            query = {"repay_stable": {}}
            return MsgExecuteContract(AccAddress(wallet_address),
                                                contract=Config._address["mmMarket"],
                                                execute_msg=query,
                                                coins=Coins(uusd=amount_to_repay))

        except LCDResponseError as e:
            Config._log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)            

    async def get_borrow_amount_msg(wallet_address, amount_to_borrow):
        try:

            query = {"borrow_stable": {"borrow_amount": str(amount_to_borrow), "to": wallet_address}}
            return MsgExecuteContract(AccAddress(wallet_address),
                                                contract=Config._address["mmMarket"],
                                                execute_msg=query)

        except LCDResponseError as e:
            Config._log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)

    async def get_withdraw_from_earn_msg(wallet_address, amount_to_withdraw):
        try:
            b64 = dict_to_b64({"redeem_stable": {}})
            msg = {"send": {"contract": str(Config._address["mmMarket"]),"amount": str(amount_to_withdraw), "msg": b64}}
            return MsgExecuteContract(AccAddress(wallet_address),
                                                contract=Config._address["aterra_contract"],
                                                execute_msg=msg)

        except LCDResponseError as e:
            Config._log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)
            

            


    async def get_deposit_to_earn_msg(wallet_address, amount_to_deposit):
        try:
            query = {"deposit_stable": {}}
            return MsgExecuteContract(AccAddress(wallet_address),
                                            contract=Config._address["mmMarket"],
                                            execute_msg=query,
                                            coins=Coins(uusd=amount_to_deposit))

        except LCDResponseError as e:
            Config._log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)

    async def get_claim_anc_rewards_msg(wallet_address):
        try:
            query = {"claim_rewards": {"to": wallet_address}}
            return MsgExecuteContract(AccAddress(wallet_address),
                                                contract=Config._address["mmMarket"],
                                                execute_msg=query)

        except LCDResponseError as e:
            Config._log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)


    async def get_total_deposit_amount(wallet_address):
        total_deposit = 0
        try:
            query = {"epoch_state": {}}
            response = await TerraChain.chain.wasm.contract_query(Config._address["mmMarket"], query)
            exchange_rate = float(response["exchange_rate"])

            balance = await Anchor.get_balance_on_earn(wallet_address)

            total_deposit = exchange_rate * balance


        except LCDResponseError as e:
            Config._log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)
            

        return total_deposit

    async def get_balance_on_earn(wallet_address):
        balance = 0
        try:
            query = {"balance": {"address": wallet_address}}
            response = await TerraChain.chain.wasm.contract_query(Config._address["aterra_contract"], query)
            balance = float(response["balance"])

        except LCDResponseError as e:
            Config._log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)
            

        return balance

    async def get_earn_apy():
        earn_apy = None
        try:

            query = {"epoch_state": {}}
            response = await TerraChain.chain.wasm.contract_query(Config._address["overseer_contract"], query)
            deposit_rate = float(response["deposit_rate"])

            earn_apy = round(deposit_rate * Config.BLOCKS_PER_YEAR * 100,2)


        except LCDResponseError as e:
            Config._log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)
            


        return earn_apy


    async def get_borrow_apy():
        borrow_apy = None
        try:

            query = {"query":"{{\n  marketBalances: BankBalancesAddress(Address: \"{}\") {{\n    Result {{\n      Denom\n      Amount\n    }}\n  }}\n}}\n".format(Config._address["mmMarket"])}
            response = requests.post(Config._address["mantle_endpoint"], query)
            market_balance = response.json()["data"]["marketBalances"]["Result"][0]["Amount"]



            query = {"query":"{ borrowerDistributionAPYs: AnchorBorrowerDistributionAPYs(Order: DESC Limit: 1) {Height Timestamp DistributionAPY}}"}
            response = requests.post(Config._address["mantle_endpoint"], query)
            distribution_apy = response.json()["data"]["borrowerDistributionAPYs"][0]["DistributionAPY"]

            query = {"state": {"block_height":await Anchor.get_block_height()}}
            response = await TerraChain.chain.wasm.contract_query(Config._address["mmMarket"], query)

            total_liabilities = response["total_liabilities"]
            total_reserves = response["total_reserves"]

            query = {"borrow_rate": {"market_balance":market_balance, "total_liabilities": total_liabilities, "total_reserves":total_reserves},}
            response = await TerraChain.chain.wasm.contract_query(Config._address["interest_model"], query)
            borrow_rate = Config.BLOCKS_PER_YEAR * float(response["rate"])
            

            query = {"state": {}}
            response = await TerraChain.chain.wasm.contract_query(Config._address["mmMarket"], query)

            borrow_apy = round((float(distribution_apy) - borrow_rate) * 100,2)



        except LCDResponseError as e:
            Config._log.exception(e)
            raise AnchorException(inspect.currentframe().f_code.co_name, e.errno if e.errno else -1, e.message)
            


        return borrow_apy



