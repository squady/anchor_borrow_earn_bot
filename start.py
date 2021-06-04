from helper import Helper
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")

import sys
import asyncio
import logging
import os
import base64
import inspect
from bot_telegram import bot_telegram
from looper import Looper
from anchor import Anchor, AnchorException
from terra_wallet import TerraWallet
from terra_sdk.client.lcd import AsyncLCDClient
from action import Action, TVL_TYPE

PAUSE_BETWEEN_TRX_S = 8



class Main():
    def __init__(self):
        logger = logging.getLogger("borrow_bot")
        formatter = logging.Formatter('%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                                      datefmt='%Y-%m-%d:%H:%M:%S')
        logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)



        
        self._log = logger

        self._wallet_name = os.environ.get("WALLET_NAME", "Wallet#1")
        self._mnemonic = base64.b64decode(os.environ.get("WALLET_MNEMONIC")).decode("utf-8")
        self._telegram_token = os.environ.get("TELEGRAM_TOKEN", None)
        self._telegram_chat_id = int(os.environ.get("TELEGRAM_CHAT_ID", 0))
        self._anchor_mmMarket = os.environ.get("ANCHOR_mmMarket", "terra15dwd5mj8v59wpj0wvt233mf5efdff808c5tkal")
        self._anchor_mmOverseer = os.environ.get("ANCHOR_mmOverseer", "terra1qljxd0y3j3gk97025qvl3lgq8ygup4gsksvaxv")
        self._anchor_aTerra = os.environ.get("ANCHOR_aTerra", "terra1ajt556dpzvjwl0kl5tzku3fc3p3knkg9mkv8jl")
        self._target_tvl = float(os.environ.get("TARGET_TVL", 35))
        self._min_tvl = float(os.environ.get("MIN_TVL", 30))
        self._max_tvl = float(os.environ.get("MAX_TVL", 40))
        self._chain_id = os.environ.get("CHAIN_ID", "tequila-0004")
        self._chain_url = os.environ.get("CHAIN_URL", "https://tequila-lcd.terra.dev")

        
        self._log.info("===========================================")
        self._log.info("wallet_name = {}".format(self._wallet_name))
        self._log.info("chain_id = {}".format(self._chain_id))
        self._log.info("chain_url = {}".format(self._chain_url))
        self._log.info("telegram token = {}".format(self._telegram_token))
        self._log.info("telegram chat_id = {}".format(self._telegram_chat_id))
        self._log.info("anchor mmMarket = {}".format(self._anchor_mmMarket))
        self._log.info("anchor mmOverseer = {}".format(self._anchor_mmOverseer))
        self._log.info("anchor aTerra = {}".format(self._anchor_aTerra))
        self._log.info("MIN TVL = {}".format(self._min_tvl))
        self._log.info("Target TVL = {}".format(self._target_tvl))
        self._log.info("MAX TVL = {}".format(self._max_tvl))
        self._log.info("===========================================")


        self._bot_telegram = bot_telegram(self._telegram_token,self._telegram_chat_id)
        self._wallet = TerraWallet(self._wallet_name, self._mnemonic)
        self._looper = Looper(self._wallet, self._target_tvl, self._min_tvl, self._max_tvl)


        self._bot_telegram.addObserver(self, Action.GET_BORROW_INFOS, self.get_borrow_infos)
        self._bot_telegram.addObserver(self, Action.GET_EARN_INFOS, self.get_earn_infos)
        self._bot_telegram.addObserver(self, Action.GET_WALLET_INFOS, self.get_wallet_infos)
        self._bot_telegram.addObserver(self, Action.FETCH_TVL, self.fetch_tvl)
        self._bot_telegram.addObserver(self, Action.CHANGE_TVL, self.change_tvl)
        self._bot_telegram.addObserver(self, Action.DEPOSIT_AMOUNT, self.set_deposit_amount)
        self._bot_telegram.addObserver(self, Action.CLAIM_REWARDS, self.claim_rewards)
        self._looper.addObserver(self, Action.TVL_TOO_LOW, self.tvl_too_low)
        self._looper.addObserver(self, Action.TVL_TOO_HIGH, self.tvl_too_high)





    async def start(self):
        try:
            await asyncio.gather(
                self._bot_telegram.start(), 
                self._looper.start())

        except Exception as e:
            self._log.exception(e)


    async def stop(self):
        try:
            await self._bot_telegram.stop()
            await self._looper.stop()

        except Exception as e:
            self._log.exception(e)


    async def get_borrow_infos(self):
        try:
            wallet_address = self._wallet.get_wallet_address()
            borrow_value = await Anchor.get_borrow_value(wallet_address)
            borrow_limit = await Anchor.get_borrow_limit(wallet_address)
            if (borrow_value != 0 and borrow_limit != 0):
                current_tvl = await Anchor.get_current_tvl(wallet_address, borrow_value, borrow_limit)
                pending_rewards = await Anchor.get_pending_rewards(wallet_address)


                current_tvl_state ="🟩"
                if (current_tvl < self._min_tvl):
                    current_tvl_state = "🟧"
                elif (current_tvl > self._max_tvl):
                    current_tvl_state = "🟥"

                message = "<b>Borrow datas</b>\n"
                message += "{} Current TVL: <code>{}%</code>\n".format(current_tvl_state, current_tvl)
                message += "🟩 Target TVL: <code>{}%</code>\n".format(self._target_tvl)
                message += "🟥 Max TVL: <code>{}%</code>\n".format(self._max_tvl)
                message += "🟧 Min TVL: <code>{}%</code>\n".format(self._min_tvl)
                message += "💴 Borrowed: <code>{}$</code>\n".format(Helper.to_human_value(borrow_value))
                message += "💴 Limit: <code>{}$</code>\n".format(Helper.to_human_value(borrow_limit))
                message += "💴 Pending Rewards: <code>{}$ANC</code>\n".format(Helper.to_human_value(pending_rewards))

                await bot_telegram.send_message(message)

            else:
                raise AnchorException(inspect.currentframe().f_code.co_name , -1, "You must provide a collateral on Anchor to use this bot")

            
        except AnchorException as e:
            self._log.exception(e)
            await bot_telegram.send_message(e.to_telegram_str())

        except Exception as e:
            self._log.exception(e)


    async def get_earn_infos(self):
        try:

            wallet_address = self._wallet.get_wallet_address()
            total_deposit = await Anchor.get_total_deposit_amount(wallet_address)
            earn_apy = await Anchor.get_earn_apy()

            message = "<b>Earn datas</b>\n"
            message += "💴 Total Deposit: <code>{}$</code>\n".format(Helper.to_human_value(total_deposit))
            message += "💴 APY: <code>{}%</code>\n".format(earn_apy)

            await bot_telegram.send_message(message)
        except AnchorException as e:
            self._log.exception(e)
            await bot_telegram.send_message(e.to_telegram_str())

        except Exception as e:
            self._log.exception(e)

    async def get_wallet_infos(self):
        try:
            wallet_address = self._wallet.get_wallet_address()
            uusd_amount = await self._wallet.get_uusd_amount()

            message = "<b>Wallet datas</b>\n"
            message += "💴 Address : <a href='{}'>{}</a>\n".format(self._wallet.get_wallet_url(), wallet_address)
            message += "💴 UUSD : <code>{}$</code>\n".format(Helper.to_human_value(uusd_amount))
            await bot_telegram.send_message(message)

        except AnchorException as e:
            self._log.exception(e)
            await bot_telegram.send_message(e.to_telegram_str())

        except Exception as e:
            self._log.exception(e)        


    async def fetch_tvl(self):
        error_occured = False
        try:
            await bot_telegram.send_message("Sets the TVL to the target value ...", False)
            wallet_address = self._wallet.get_wallet_address()
            current_tvl = await Anchor.get_current_tvl(wallet_address)
            if (current_tvl is not None):
                if (current_tvl > self._target_tvl):
                    # do withdraxw if need
                    # then do repay
                    amount_to_repay = await Anchor.get_amount_to_repay(wallet_address, self._target_tvl)
                    await bot_telegram.send_message("Needs to repay to reach TVL ...", False)
                    await self.do_withdraw_if_needed_and_repay(self._wallet, int(amount_to_repay))


                elif (current_tvl < self._target_tvl):
                    # do borrow
                    amount_to_borrow = await Anchor.get_amount_to_borrow(wallet_address, self._target_tvl)
                    # await bot_telegram.send_message("Borrowing <code>{}$</code> and deposit it on earn ...".format(Helper.to_human_value(amount_to_borrow)), False)
                    await bot_telegram.send_message("Needs to borrow to reach TVL ...", False)                
                    await self.do_borrow_and_deposit(self._wallet, amount_to_borrow)
            else:
                raise AnchorException(inspect.currentframe().f_code.co_name , -1, "You must provide a collateral on Anchor to use this bot")

        except AnchorException as e:
            error_occured = True
            self._log.exception(e)
            await bot_telegram.send_message(e.to_telegram_str(), False)
        
        except Exception as e:
            error_occured = True
            self._log.exception(e)

        finally:
            if (error_occured == True):
                await bot_telegram.send_message("🔴 Ended with errors.")
            else:
                await bot_telegram.send_message("🟢 Done.")


    async def do_withdraw_if_needed_and_repay(self, wallet, amount_to_repay):
        wallet_address = wallet.get_wallet_address()
        uusd_amount_in_wallet = await wallet.get_uusd_amount()
        uusd_amount_in_wallet = max(uusd_amount_in_wallet - Helper.to_terra_value(20), 0)
        
        if (uusd_amount_in_wallet < amount_to_repay):
            # need to withdraw
            total_deposit = await Anchor.get_total_deposit_amount(wallet_address) 
            amount_to_repay = amount_to_repay - uusd_amount_in_wallet
            await bot_telegram.send_message("Not enough liquidity, withdrawing from earn <code>{}$</code> ...".format(Helper.to_human_value(amount_to_repay)), False)
            if (total_deposit > amount_to_repay):
                await Anchor.do_withdraw_from_earn(wallet._wallet, int(amount_to_repay))
                await asyncio.sleep(PAUSE_BETWEEN_TRX_S)
                # await bot_telegram.send_message("done.", False)


        await bot_telegram.send_message("Repaying <code>{}$</code> ...".format(Helper.to_human_value(amount_to_repay)), False)
        await Anchor.do_repay_amount(wallet._wallet, int(amount_to_repay))

    async def do_borrow_and_deposit(self, wallet, amount_to_borrow):

        await bot_telegram.send_message("Borrowing <code>{}$</code> ...".format(Helper.to_human_value(amount_to_borrow)), False)
        await Anchor.do_borrow_amount(wallet._wallet, amount_to_borrow)
        await bot_telegram.send_message("Depositing <code>{}$</code> to earn...".format(Helper.to_human_value(amount_to_borrow)), False)
        await asyncio.sleep(PAUSE_BETWEEN_TRX_S)
        await Anchor.do_deposit_to_earn(wallet._wallet, amount_to_borrow)

    async def change_tvl(self, **kwargs):
        try:
            new_tvl = kwargs["new_tvl"]
            type_tvl = kwargs["type_tvl"]
            old_tvl = 0

            if (type_tvl == TVL_TYPE.TARGET):
                if (new_tvl > self._min_tvl and new_tvl < self._max_tvl):
                    old_tvl = self._target_tvl
                    self._target_tvl = new_tvl
                    self._looper.change_target_tvl(new_tvl)
                else:
                    raise AnchorException(inspect.currentframe().f_code.co_name,
                            -1,
                            "Target({}%) TVL must be higher than MIN({}%) and lower than MAX({}%)".format(new_tvl, self._min_tvl, self._max_tvl))
            
            elif (type_tvl == TVL_TYPE.MIN):
                if (new_tvl < self._target_tvl and new_tvl < self._max_tvl):
                    old_tvl = self._min_tvl
                    self._min_tvl = new_tvl
                    self._looper.change_min_tvl(new_tvl)
                else:
                    raise AnchorException(inspect.currentframe().f_code.co_name,
                            -1,
                            "Min({}%) TVL must be lower than Target({}%) and lower than MAX({}%)".format(new_tvl, self._target_tvl, self._max_tvl))

            elif (type_tvl == TVL_TYPE.MAX):
                if (new_tvl > self._target_tvl and new_tvl > self._min_tvl):
                    old_tvl = self._max_tvl                
                    self._max_tvl = new_tvl
                    self._looper.change_max_tvl(new_tvl)
                else:
                    raise AnchorException(inspect.currentframe().f_code.co_name,
                            -1,
                            "Max({}%) TVL must be higher than Min({}%) and higher than Target({}%)".format(new_tvl, self._min_tvl, self._target_tvl))                    
            else:
                raise AnchorException(inspect.currentframe().f_code.co_name, -1, "unknow TVL type")

            tvl = "Target"
            if (type_tvl == TVL_TYPE.MIN):
                tvl = "Min"
            elif (type_tvl == TVL_TYPE.MAX):
                tvl = "Max"

            await bot_telegram.send_message("{} TVL changed from <code>{}%</code> to <code>{}%</code>".format(tvl, old_tvl, new_tvl))

        except AnchorException as e:
            self._log.exception(e)
            await bot_telegram.send_message(e.to_telegram_str())

        except Exception as e:
            self._log.exception(e)   

    async def set_deposit_amount(self, **kwargs):
        error_occured = False
        try:
            amount_to_deposit = kwargs["amount"]         
            await bot_telegram.send_message("Trying to deposit <code>{}$</code> to earn ...".format(amount_to_deposit), False)
            amount_to_deposit = int(Helper.to_terra_value(float(amount_to_deposit)))
            uusd_amount = await self._wallet.get_uusd_amount()
            uusd_amount = uusd_amount - Helper.to_terra_value(20)
            if (amount_to_deposit > uusd_amount):
                error_occured = True
                await bot_telegram.send_message("Unable to deposit, not enough liquidity")
            else:
                await Anchor.do_deposit_to_earn(self._wallet._wallet, amount_to_deposit)

        except AnchorException as e:
            error_occured = True
            self._log.exception(e)
            await bot_telegram.send_message(e.to_telegram_str(), False)
        
        except Exception as e:
            error_occured = True
            self._log.exception(e)
        finally:
            if (error_occured == True):
                await bot_telegram.send_message("🔴 Ended with errors.")
            else:
                await bot_telegram.send_message("🟢 Done.")
            


    async def claim_rewards(self, **kwargs):
        error_occured = False
        try:
            amount_rewards = await Anchor.get_pending_rewards(self._wallet.get_wallet_address())
            if (amount_rewards > 0):
                await bot_telegram.send_message("Claiming <code>{} ANC</code> rewards ...".format(Helper.to_human_value(amount_rewards)), False)
                await Anchor.do_claim_anc_rewards(self._wallet._wallet)
            else:
                await bot_telegram.send_message("No rewards to claim", False)

        except AnchorException as e:
            error_occured = True
            self._log.exception(e)
            await bot_telegram.send_message(e.to_telegram_str(), False)
        
        except Exception as e:
            error_occured = True
            self._log.exception(e)
        finally:
            if (error_occured == True):
                await bot_telegram.send_message("🔴 Ended with errors.")
            else:
                await bot_telegram.send_message("🟢 Done.")
            
                  

    async def tvl_too_low(self, **kwargs):
        try:
            current_tvl = kwargs["current_tvl"]
            message = "❗️ TVL too low ❗️\n"
            message += "Min is : <code>{}%</code> Current is : <code>{}%</code>".format(self._min_tvl, current_tvl)
            await bot_telegram.send_message(message, False)
            await self.fetch_tvl()

        except Exception as e:
            self._log.exception(e)        

    async def tvl_too_high(self, **kwargs):
        try:
            current_tvl = kwargs["current_tvl"]
            message = "❗️ TVL too high ❗️\n"
            message += "Max is : <code>{}%</code> Current is : <code>{}%</code>".format(self._max_tvl, current_tvl)
            await bot_telegram.send_message(message, False)
            await self.fetch_tvl()

        except Exception as e:
            self._log.exception(e)        





if __name__ == "__main__":
    _main = Main()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(_main.start())
    except KeyboardInterrupt:
        loop.run_until_complete(_main.stop())
    finally:
        print("exit")
        sys.exit()
