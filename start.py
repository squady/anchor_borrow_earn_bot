from terra_chain import TerraChain
from helper import Helper
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

import sys
import asyncio
import inspect
from looper import Looper
from anchor import Anchor, AnchorException
from terra_wallet import TerraWallet
from action import Action, LTV_TYPE
import bot_telegram
from config import Config


class Main:
    def __init__(self):

        self._wallet = TerraWallet(Config._wallet_name, Config._mnemonic)
        self._loop_check_borrow = Looper(self.do_check_borrow, 20)

        bot_telegram.events.addObserver(
            self,
            Action.GET_ANCHOR_INFOS,
            self.get_anchor_infos,
        )
        bot_telegram.events.addObserver(
            self,
            Action.GET_WALLET_INFOS,
            self.get_wallet_infos,
        )
        bot_telegram.events.addObserver(
            self,
            Action.FETCH_LTV,
            self.do_reach_target_ltv,
        )
        bot_telegram.events.addObserver(
            self,
            Action.CHANGE_LTV,
            self.change_ltv,
        )
        bot_telegram.events.addObserver(
            self,
            Action.DEPOSIT_AMOUNT,
            self.set_deposit_amount,
        )
        bot_telegram.events.addObserver(
            self,
            Action.WITHDRAW_AMOUNT,
            self.set_withdraw_amount,
        )
        bot_telegram.events.addObserver(
            self,
            Action.CLAIM_REWARDS,
            self.claim_rewards,
        )

    async def start(self):
        try:
            await Anchor.get_config(Config._address["mmCustody"])
            await Anchor.get_config(Config._address["market_contract"])
            await Anchor.get_config(Config._address["overseer_contract"])
            await self.check_if_enough_ust_for_fees()
            await asyncio.gather(
                bot_telegram.start(),
                self._loop_check_borrow.start(),
            )

        except Exception as e:
            Config._log.exception(e)

    async def stop(self):
        try:
            asyncio.gather(
                bot_telegram.stop(),
                self._loop_check_borrow.stop(),
            )

        except Exception as e:
            Config._log.exception(e)


    async def get_anchor_infos(self):
        try:
            await asyncio.gather(
                self.get_borrow_infos(),
                self.get_earn_infos(),
            )

        except AnchorException as e:
            Config._log.exception(e)
            await bot_telegram.send_message(e.to_telegram_str())

        except Exception as e:
            Config._log.exception(e)


    async def get_borrow_infos(self):
        try:
            await bot_telegram.send_message(
                "Please wait while the bot is computing ...",
                show_keyboard=False,
                show_typing=True,
            )

            wallet_address = self._wallet.get_wallet_address()


            results = await asyncio.gather(
                bot_telegram.show_is_typing(),
                Anchor.get_borrow_apy(),
                Anchor.get_borrow_value(wallet_address),
                Anchor.get_borrow_limit(wallet_address),
                Anchor.get_bluna_amount(wallet_address),
                Anchor.get_bluna_price()
            )

            borrow_apy = results[1]
            borrow_value = results[2]
            borrow_limit = results[3]
            bluna_amount = results[4]
            bluna_price = round(results[5], 2)

            liquidation_price = round(
                (borrow_value * Config._maximum_ltv_allowed) / bluna_amount,
                2,
            )
            if borrow_value != 0 and borrow_limit != 0:
                current_ltv = await Anchor.get_current_ltv(
                    wallet_address, borrow_value, borrow_limit
                )
                pending_rewards = await Anchor.get_pending_rewards(wallet_address)

                current_ltv_state = "🟢"
                if current_ltv < Config._min_ltv:
                    current_ltv_state = "🟠"
                elif current_ltv > Config._max_ltv:
                    current_ltv_state = "🔴"

                message = "<u><b>💱 Borrow infos :</b></u>\n\n"
                message += "{} Current LTV: <code>{}%</code>\n".format(
                    current_ltv_state, current_ltv
                )
                message += "🟢 Target LTV: <code>{}%</code>\n".format(Config._target_ltv)
                message += "🔴 Max LTV: <code>{}%</code>\n".format(Config._max_ltv)
                message += "🟠 Min LTV: <code>{}%</code>\n".format(Config._min_ltv)
                message += "🌖 bLuna price: <code>{}$</code>\n".format(bluna_price)
                message += "☠️ Liquidation price: <code>{}$</code>\n".format(
                    liquidation_price
                )
                message += "💴 Borrowed: <code>{}$</code>\n".format(
                    Helper.to_human_value(borrow_value)
                )
                message += "💴 Limit: <code>{}$</code>\n".format(
                    Helper.to_human_value(borrow_limit)
                )
                message += "🎁 Pending Rewards: <code>{}$ANC</code>\n".format(
                    Helper.to_human_value(pending_rewards)
                )
                message += "⚙️ APY: <code>{}%</code>\n".format(borrow_apy)

                await bot_telegram.send_message(message)

            else:
                raise AnchorException(
                    inspect.currentframe().f_code.co_name,
                    -1,
                    "You must provide a collateral on Anchor to use this bot",
                )

        except AnchorException as e:
            Config._log.exception(e)
            await bot_telegram.send_message(e.to_telegram_str())

        except Exception as e:
            Config._log.exception(e)

    async def get_earn_infos(self):
        try:
            wallet_address = self._wallet.get_wallet_address()

            results = await asyncio.gather(
                bot_telegram.show_is_typing(),
                Anchor.get_total_deposit_amount(wallet_address),
                Anchor.get_earn_apy()
            )

            total_deposit = results[1]
            earn_apy = results[2]

            message = "<u><b>💰 Earn infos :</b></u>\n\n"
            message += "💴 Total Deposit: <code>{}$</code>\n".format(
                Helper.to_human_value(total_deposit)
            )
            message += "⚙️ APY: <code>{}%</code>\n".format(earn_apy)

            await bot_telegram.send_message(message)
        except AnchorException as e:
            Config._log.exception(e)
            await bot_telegram.send_message(e.to_telegram_str())

        except Exception as e:
            Config._log.exception(e)

    async def get_wallet_infos(self):
        try:
            wallet_address = self._wallet.get_wallet_address()
            

            results = await asyncio.gather(
                bot_telegram.show_is_typing(),
                self.check_if_enough_ust_for_fees(),
                self._wallet.get_uusd_amount()
            )

            uusd_amount = results[2]

            message = "<u><b>👛 <a href='{}'>{}</a></b></u>".format(
                self._wallet.get_wallet_url(), self._wallet.get_wallet_name()
            )
            message += " (<code>v{}</code>)\n\n".format(Config.VERSION)
            message += "🔗 Chain id: <code>{}</code>\n".format(Config._chain_id)
            message += "🌎 Chain url: <code>{}</code>\n".format(Config._chain_url)
            message += "💴 Address: <code>{}</code>\n".format(wallet_address)
            message += "💲 UST: <code>{}$</code>\n".format(
                Helper.to_human_value(uusd_amount)
            )
            await bot_telegram.send_message(message)

        except AnchorException as e:
            Config._log.exception(e)
            await bot_telegram.send_message(e.to_telegram_str())

        except Exception as e:
            Config._log.exception(e)

    async def do_reach_target_ltv(self):
        trxhash = None
        try:
            await self.check_if_enough_ust_for_fees()
            wallet_address = self._wallet.get_wallet_address()
            await bot_telegram.send_message(
                "Please wait while the bot changes LTV...",
                show_keyboard=False,
                show_typing=True,
            )
            current_ltv = await Anchor.get_current_ltv(wallet_address)
            await bot_telegram.send_message(
                "Change LTV from <code>{}%</code> to <code>{}%</code> ...".format(
                    current_ltv, Config._target_ltv
                ),
                show_keyboard=False,
                show_typing=True,
            )
            if current_ltv is not None:
                if current_ltv > Config._target_ltv:
                    # do withdraxw if need
                    # then do repay
                    amount_to_repay = await Anchor.get_amount_to_repay(
                        wallet_address, Config._target_ltv
                    )
                    trxhash = await self.do_withdraw_if_needed_and_repay(
                        self._wallet, int(amount_to_repay)
                    )

                elif current_ltv < Config._target_ltv:
                    # do borrow
                    amount_to_borrow = await Anchor.get_amount_to_borrow(
                        wallet_address, Config._target_ltv
                    )
                    trxhash = await self.do_borrow_and_deposit(
                        self._wallet, amount_to_borrow
                    )
            else:
                raise AnchorException(
                    inspect.currentframe().f_code.co_name,
                    -1,
                    "You must provide a collateral on Anchor to use this bot",
                )

        except AnchorException as e:
            Config._log.exception(e)
            await bot_telegram.send_message(
                e.to_telegram_str(), show_keyboard=False, show_typing=True
            )

        except Exception as e:
            Config._log.exception(e)

        finally:
            await self.handle_result(trxhash)

    async def do_check_borrow(self):
        try:
            Config._log.info("Hello, job is starting...")

            wallet_address = self._wallet.get_wallet_address()

            current_ltv = await Anchor.get_current_ltv(wallet_address)
            if current_ltv is not None:
                if current_ltv < Config._min_ltv:
                    message = "❗️ LTV too low ❗️\n"
                    message += "Min is : <code>{}%</code> Current is : <code>{}%</code>".format(
                        Config._min_ltv,
                        current_ltv,
                    )
                    await bot_telegram.send_message(
                        message,
                        show_keyboard=False,
                        show_typing=True,
                    )
                    await self.do_reach_target_ltv()

                elif current_ltv > Config._max_ltv:
                    message = "❗️ LTV too high ❗️\n"
                    message += "Max is : <code>{}%</code> Current is : <code>{}%</code>".format(
                        Config._max_ltv,
                        current_ltv,
                    )
                    await bot_telegram.send_message(
                        message,
                        show_keyboard=False,
                        show_typing=True,
                    )
                    await self.do_reach_target_ltv()
                else:
                    Config._log.info("nothing to do")

        except AnchorException as e:
            await bot_telegram.send_message(e.to_telegram_str())

        except Exception as e:
            Config._log.exception(e)

    async def do_withdraw_if_needed_and_repay(self, wallet, amount_to_repay):
        wallet_address = wallet.get_wallet_address()
        uusd_amount_in_wallet = await wallet.get_uusd_amount()
        uusd_amount_in_wallet = max(
            uusd_amount_in_wallet - Helper.to_terra_value(20), 0
        )
        transactions = []
        if uusd_amount_in_wallet < amount_to_repay:
            earn_balance = await Anchor.get_balance_on_earn(wallet_address)
            if uusd_amount_in_wallet + earn_balance < amount_to_repay:
                if earn_balance > Helper.to_terra_value(10):
                    transactions.append(
                        await Anchor.get_withdraw_from_earn_msg(
                            wallet_address, int(earn_balance)
                        )
                    )
                    await bot_telegram.send_message(
                        "Not enough liquidity available on wallet + earn, nned to withdraw anyway <code>{}$</code> from earn to lower the ratio.".format(
                            Helper.to_human_value(earn_balance)
                        ),
                        show_keyboard=False,
                        show_typing=True,
                    )
                    amount_to_repay = uusd_amount_in_wallet + earn_balance
                    amount_to_repay = max(
                        amount_to_repay - Helper.to_terra_value(20),
                        0,
                    )
                elif uusd_amount_in_wallet > Helper.to_terra_value(10):
                    await bot_telegram.send_message(
                        "Less than <code>10$</code> on earn, it's not worth to withdraw",
                        show_keyboard=False,
                        show_typing=True,
                    )
                    amount_to_repay = uusd_amount_in_wallet
                else:
                    raise AnchorException(
                        inspect.currentframe().f_code.co_name,
                        -1,
                        "❗️ Not enough liquidity available, you must handle it by yourself ❗️",
                    )

            else:
                amount_to_withdraw = amount_to_repay - uusd_amount_in_wallet
                transactions.append(
                    await Anchor.get_withdraw_from_earn_msg(
                        wallet_address, int(amount_to_withdraw)
                    )
                )
                await bot_telegram.send_message(
                    "Need to withdraw <code>{}$</code> from earn.".format(
                        Helper.to_human_value(amount_to_withdraw)
                    ),
                    show_keyboard=False,
                    show_typing=True,
                )

        if amount_to_repay > 0:
            transactions.append(
                await Anchor.get_repay_amount_msg(wallet_address, int(amount_to_repay))
            )
            await bot_telegram.send_message(
                "Need to repay <code>{}$</code>.".format(
                    Helper.to_human_value(amount_to_repay)
                ),
                show_keyboard=False,
                show_typing=True,
            )

            await bot_telegram.send_message(
                "Sending transactions ...",
                show_keyboard=False,
                show_typing=True,
            )
            return await Anchor.do_trx(wallet, transactions)

        else:
            raise AnchorException(
                inspect.currentframe().f_code.co_name,
                -1,
                "❗️ Something went wrong, because amount to repay <= 0$ ❗️",
            )

    async def do_borrow_and_deposit(self, wallet, amount_to_borrow):

        transactions = []
        wallet_address = wallet.get_wallet_address()
        await bot_telegram.send_message(
            "Need to borrow <code>{}$</code>.".format(
                Helper.to_human_value(amount_to_borrow)
            ),
            show_keyboard=False,
            show_typing=True,
        )
        transactions.append(
            await Anchor.get_borrow_amount_msg(wallet_address, amount_to_borrow)
        )
        await bot_telegram.send_message(
            "Going to deposit <code>{}$</code> to earn.".format(
                Helper.to_human_value(amount_to_borrow)
            ),
            show_keyboard=False,
            show_typing=True,
        )
        transactions.append(
            await Anchor.get_deposit_to_earn_msg(wallet_address, amount_to_borrow)
        )

        await bot_telegram.send_message(
            "Sending transactions ...",
            show_keyboard=False,
            show_typing=True,
        )
        return await Anchor.do_trx(wallet, transactions)

    async def change_ltv(self, **kwargs):
        try:
            new_ltv = kwargs["new_ltv"]
            type_ltv = kwargs["type_ltv"]
            old_ltv = 0

            if type_ltv == LTV_TYPE.TARGET:
                if new_ltv > Config._min_ltv and new_ltv < Config._max_ltv:
                    old_ltv = Config._target_ltv
                    Config._target_ltv = new_ltv
                else:
                    raise AnchorException(
                        inspect.currentframe().f_code.co_name,
                        -1,
                        "Target({}%) LTV must be higher than MIN({}%) and lower than MAX({}%)".format(
                            new_ltv,
                            Config._min_ltv,
                            Config._max_ltv,
                        ),
                    )

            elif type_ltv == LTV_TYPE.MIN:
                if new_ltv < Config._target_ltv and new_ltv < Config._max_ltv:
                    old_ltv = Config._min_ltv
                    Config._min_ltv = new_ltv
                else:
                    raise AnchorException(
                        inspect.currentframe().f_code.co_name,
                        -1,
                        "Min({}%) LTV must be lower than Target({}%) and lower than MAX({}%)".format(
                            new_ltv,
                            Config._target_ltv,
                            Config._max_ltv,
                        ),
                    )

            elif type_ltv == LTV_TYPE.MAX:
                if new_ltv > Config._target_ltv and new_ltv > Config._min_ltv:
                    old_ltv = Config._max_ltv
                    Config._max_ltv = new_ltv
                else:
                    raise AnchorException(
                        inspect.currentframe().f_code.co_name,
                        -1,
                        "Max({}%) LTV must be higher than Min({}%) and higher than Target({}%)".format(
                            new_ltv,
                            Config._min_ltv,
                            Config._target_ltv,
                        ),
                    )
            else:
                raise AnchorException(
                    inspect.currentframe().f_code.co_name,
                    -1,
                    "unknow LTV type",
                )

            ltv = "Target"
            if type_ltv == LTV_TYPE.MIN:
                ltv = "Min"
            elif type_ltv == LTV_TYPE.MAX:
                ltv = "Max"

            await bot_telegram.send_message(
                "{} LTV changed from <code>{}%</code> to <code>{}%</code>".format(
                    ltv,
                    old_ltv,
                    new_ltv,
                )
            )

        except AnchorException as e:
            Config._log.exception(e)
            await bot_telegram.send_message(e.to_telegram_str())

        except Exception as e:
            Config._log.exception(e)

    async def set_deposit_amount(self, **kwargs):
        trxhash = None
        try:
            wallet_address = self._wallet.get_wallet_address()
            await self.check_if_enough_ust_for_fees()
            amount_to_deposit = kwargs["amount"]
            await bot_telegram.send_message(
                "Going to deposit <code>{}$</code> to earn.".format(amount_to_deposit),
                show_keyboard=False,
                show_typing=True,
            )
            amount_to_deposit = int(Helper.to_terra_value(float(amount_to_deposit)))
            uusd_amount = await self._wallet.get_uusd_amount()
            uusd_amount = uusd_amount - Helper.to_terra_value(20)
            if amount_to_deposit > uusd_amount:
                await bot_telegram.send_message(
                    "Unable to deposit, not enough liquidity"
                )
            else:
                await bot_telegram.send_message(
                    "Sending transaction ...",
                    show_keyboard=False,
                    show_typing=True,
                )
                trxhash = await Anchor.do_trx(
                    self._wallet,
                    [
                        await Anchor.get_deposit_to_earn_msg(
                            wallet_address,
                            amount_to_deposit,
                        )
                    ]
                )

        except AnchorException as e:
            Config._log.exception(e)
            await bot_telegram.send_message(
                e.to_telegram_str(),
                show_keyboard=False,
                show_typing=True,
            )

        except Exception as e:
            Config._log.exception(e)
        finally:
            await self.handle_result(trxhash)

    async def set_withdraw_amount(self, **kwargs):
        trxhash = None
        try:
            wallet_address = self._wallet.get_wallet_address()
            await self.check_if_enough_ust_for_fees()
            amount_to_withdraw = kwargs["amount"]
            await bot_telegram.send_message(
                "Going to withdraw <code>{}$</code> from earn.".format(
                    amount_to_withdraw
                ),
                show_keyboard=False,
                show_typing=True,
            )
            exchange_rate = await Anchor.get_exchange_rate()
            amount_to_withdraw = int(Helper.to_terra_value(float(amount_to_withdraw) / exchange_rate))
            amount_on_earn = await Anchor.get_balance_on_earn(wallet_address)
            if amount_to_withdraw > amount_on_earn:
                await bot_telegram.send_message("Not enough liquidity on earn")
            else:
                await bot_telegram.send_message(
                    "Sending transaction ...",
                    show_keyboard=False,
                    show_typing=True,
                )
                trxhash = await Anchor.do_trx(
                    self._wallet,
                    [
                        await Anchor.get_withdraw_from_earn_msg(
                            wallet_address,
                            amount_to_withdraw,
                        )
                    ]
                )

        except AnchorException as e:
            Config._log.exception(e)
            await bot_telegram.send_message(
                e.to_telegram_str(),
                show_keyboard=False,
                show_typing=True,
            )

        except Exception as e:
            Config._log.exception(e)
        finally:
            await self.handle_result(trxhash)

    async def claim_rewards(self, **kwargs):
        trxhash = None
        try:
            await self.check_if_enough_ust_for_fees()
            amount_rewards = await Anchor.get_pending_rewards(
                self._wallet.get_wallet_address()
            )
            if amount_rewards > 0:
                await bot_telegram.send_message(
                    "Going to claim <code>{} ANC</code> rewards.".format(
                        Helper.to_human_value(amount_rewards)
                    ),
                    show_keyboard=False,
                    show_typing=True,
                )
                await bot_telegram.send_message(
                    "Sending transaction ...",
                    show_keyboard=False,
                    show_typing=True,
                )
                trxhash = await Anchor.do_trx(
                    self._wallet,
                    [
                        await Anchor.get_claim_anc_rewards_msg(
                            self._wallet.get_wallet_address()
                        )
                    ],
                    Config.CLAIM_FEES,
                )
            else:
                await bot_telegram.send_message(
                    "No rewards to claim",
                    show_keyboard=False,
                    show_typing=True,
                )

        except AnchorException as e:
            Config._log.exception(e)
            await bot_telegram.send_message(
                e.to_telegram_str(),
                show_keyboard=False,
                show_typing=True,
            )

        except Exception as e:
            Config._log.exception(e)
        finally:
            await self.handle_result(trxhash)

    async def check_if_enough_ust_for_fees(self):
        try:
            uusd_amount = await self._wallet.get_uusd_amount()
            uusd_amount = Helper.to_human_value(uusd_amount)
            if uusd_amount < Config._minimum_ust_amount:
                await bot_telegram.send_message(
                    "❗️ Be careful you only have <code>{}$</code> left in your wallet to pay the fees, transactions may fail ❗️".format(
                        uusd_amount
                    )
                )

        except Exception as e:
            Config._log.exception(e)

    async def handle_result(self, trxhash):
        try:

            if trxhash == None:
                await bot_telegram.send_message("🔴 Ended with errors.")
            else:
                await bot_telegram.send_message(
                    "🟢 Done [<a href='{}'>link</a>].".format(
                        TerraChain.get_trx_url(trxhash)
                    )
                )

        except Exception as e:
            Config._log.exception(e)


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
