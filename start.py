from helper import Helper
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

import sys
import asyncio
import inspect
from looper import Looper
from anchor import Anchor, AnchorException
from terra_wallet import TerraWallet
from action import Action, TVL_TYPE
import bot_telegram
from config import Config


class Main:
    def __init__(self):

        self._wallet = TerraWallet(Config._wallet_name, Config._mnemonic)
        self._loop_check_borrow = Looper(self.do_check_borrow, 20)

        bot_telegram.events.addObserver(
            self,
            Action.GET_BORROW_INFOS,
            self.get_borrow_infos,
        )
        bot_telegram.events.addObserver(
            self,
            Action.GET_EARN_INFOS,
            self.get_earn_infos,
        )
        bot_telegram.events.addObserver(
            self,
            Action.GET_WALLET_INFOS,
            self.get_wallet_infos,
        )
        bot_telegram.events.addObserver(
            self,
            Action.FETCH_TVL,
            self.do_reach_target_tvl,
        )
        bot_telegram.events.addObserver(
            self,
            Action.CHANGE_TVL,
            self.change_tvl,
        )
        bot_telegram.events.addObserver(
            self,
            Action.DEPOSIT_AMOUNT,
            self.set_deposit_amount,
        )
        bot_telegram.events.addObserver(
            self,
            Action.CLAIM_REWARDS,
            self.claim_rewards,
        )

    async def start(self):
        try:
            await Anchor.get_config()
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

    async def get_borrow_infos(self):
        try:
            await bot_telegram.send_message(
                "Please wait while the bot is computing ...",
                show_keyboard=False,
                show_typing=True,
            )

            await bot_telegram.show_is_typing()
            wallet_address = self._wallet.get_wallet_address()
            borrow_apy = await Anchor.get_borrow_apy()
            borrow_value = await Anchor.get_borrow_value(wallet_address)
            borrow_limit = await Anchor.get_borrow_limit(wallet_address)
            if borrow_value != 0 and borrow_limit != 0:
                current_tvl = await Anchor.get_current_tvl(
                    wallet_address, borrow_value, borrow_limit
                )
                pending_rewards = await Anchor.get_pending_rewards(wallet_address)

                current_tvl_state = "🟢"
                if current_tvl < Config._min_tvl:
                    current_tvl_state = "🟠"
                elif current_tvl > Config._max_tvl:
                    current_tvl_state = "🔴"

                message = "<u><b>💱 Borrow infos :</b></u>\n\n"
                message += "{} Current TVL: <code>{}%</code>\n".format(
                    current_tvl_state, current_tvl
                )
                message += "🟢 Target TVL: <code>{}%</code>\n".format(Config._target_tvl)
                message += "🔴 Max TVL: <code>{}%</code>\n".format(Config._max_tvl)
                message += "🟠 Min TVL: <code>{}%</code>\n".format(Config._min_tvl)
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
            await bot_telegram.show_is_typing()
            wallet_address = self._wallet.get_wallet_address()
            total_deposit = await Anchor.get_total_deposit_amount(wallet_address)
            earn_apy = await Anchor.get_earn_apy()

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
            await self.check_if_enough_ust_for_fees()
            await bot_telegram.show_is_typing()
            wallet_address = self._wallet.get_wallet_address()
            uusd_amount = await self._wallet.get_uusd_amount()

            message = "<u><b>👛 <a href='{}'>{}</a></b></u>".format(
                self._wallet.get_wallet_url(), self._wallet.get_wallet_name()
            )
            message += " (<code>v{}</code>)\n\n".format(Config.VERSION)
            message += "🔗 Chain id: <code>{}</code>\n".format(Config._chain_id)
            message += "🌎 Chain url: <code>{}</code>\n".format(Config._chain_url)
            message += "💴 Address: <code>{}</code>\n".format(wallet_address)
            message += "💴 UUSD: <code>{}$</code>\n".format(
                Helper.to_human_value(uusd_amount)
            )
            await bot_telegram.send_message(message)

        except AnchorException as e:
            Config._log.exception(e)
            await bot_telegram.send_message(e.to_telegram_str())

        except Exception as e:
            Config._log.exception(e)

    async def do_reach_target_tvl(self):
        error_occured = False
        try:
            await self.check_if_enough_ust_for_fees()
            wallet_address = self._wallet.get_wallet_address()
            await bot_telegram.send_message(
                "Please wait while the bot changes TVL...",
                show_keyboard=False,
                show_typing=True,
            )
            current_tvl = await Anchor.get_current_tvl(wallet_address)
            await bot_telegram.send_message(
                "Change TVL from <code>{}%</code> to <code>{}%</code> ...".format(
                    current_tvl, Config._target_tvl
                ),
                show_keyboard=False,
                show_typing=True,
            )
            if current_tvl is not None:
                if current_tvl > Config._target_tvl:
                    # do withdraxw if need
                    # then do repay
                    amount_to_repay = await Anchor.get_amount_to_repay(
                        wallet_address, Config._target_tvl
                    )
                    await self.do_withdraw_if_needed_and_repay(
                        self._wallet, int(amount_to_repay)
                    )

                elif current_tvl < Config._target_tvl:
                    # do borrow
                    amount_to_borrow = await Anchor.get_amount_to_borrow(
                        wallet_address, Config._target_tvl
                    )
                    await self.do_borrow_and_deposit(self._wallet, amount_to_borrow)
            else:
                raise AnchorException(
                    inspect.currentframe().f_code.co_name,
                    -1,
                    "You must provide a collateral on Anchor to use this bot",
                )

        except AnchorException as e:
            error_occured = True
            Config._log.exception(e)
            await bot_telegram.send_message(
                e.to_telegram_str(), show_keyboard=False, show_typing=True
            )

        except Exception as e:
            error_occured = True
            Config._log.exception(e)

        finally:
            if error_occured == True:
                await bot_telegram.send_message("🔴 Ended with errors.")
            else:
                await bot_telegram.send_message("🟢 Done.")

    async def do_check_borrow(self):
        try:
            Config._log.info("Hello, job is starting...")

            wallet_address = self._wallet.get_wallet_address()

            current_tvl = await Anchor.get_current_tvl(wallet_address)
            if current_tvl is not None:
                if current_tvl < Config._min_tvl:
                    message = "❗️ TVL too low ❗️\n"
                    message += "Min is : <code>{}%</code> Current is : <code>{}%</code>".format(
                        Config._min_tvl,
                        current_tvl,
                    )
                    await bot_telegram.send_message(
                        message,
                        show_keyboard=False,
                        show_typing=True,
                    )
                    await self.do_reach_target_tvl()

                elif current_tvl > Config._max_tvl:
                    message = "❗️ TVL too high ❗️\n"
                    message += "Max is : <code>{}%</code> Current is : <code>{}%</code>".format(
                        Config._max_tvl,
                        current_tvl,
                    )
                    await bot_telegram.send_message(
                        message,
                        show_keyboard=False,
                        show_typing=True,
                    )
                    await self.do_reach_target_tvl()
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
                amount_to_repay = uusd_amount_in_wallet + amount_to_withdraw
                amount_to_repay = max(amount_to_repay - Helper.to_terra_value(20), 0)

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
            await Anchor.do_trx(wallet._wallet, transactions)

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
        await Anchor.do_trx(wallet._wallet, transactions)

    async def change_tvl(self, **kwargs):
        try:
            new_tvl = kwargs["new_tvl"]
            type_tvl = kwargs["type_tvl"]
            old_tvl = 0

            if type_tvl == TVL_TYPE.TARGET:
                if new_tvl > Config._min_tvl and new_tvl < Config._max_tvl:
                    old_tvl = Config._target_tvl
                    Config._target_tvl = new_tvl
                else:
                    raise AnchorException(
                        inspect.currentframe().f_code.co_name,
                        -1,
                        "Target({}%) TVL must be higher than MIN({}%) and lower than MAX({}%)".format(
                            new_tvl,
                            Config._min_tvl,
                            Config._max_tvl,
                        ),
                    )

            elif type_tvl == TVL_TYPE.MIN:
                if new_tvl < Config._target_tvl and new_tvl < Config._max_tvl:
                    old_tvl = Config._min_tvl
                    Config._min_tvl = new_tvl
                else:
                    raise AnchorException(
                        inspect.currentframe().f_code.co_name,
                        -1,
                        "Min({}%) TVL must be lower than Target({}%) and lower than MAX({}%)".format(
                            new_tvl,
                            Config._target_tvl,
                            Config._max_tvl,
                        ),
                    )

            elif type_tvl == TVL_TYPE.MAX:
                if new_tvl > Config._target_tvl and new_tvl > Config._min_tvl:
                    old_tvl = Config._max_tvl
                    Config._max_tvl = new_tvl
                else:
                    raise AnchorException(
                        inspect.currentframe().f_code.co_name,
                        -1,
                        "Max({}%) TVL must be higher than Min({}%) and higher than Target({}%)".format(
                            new_tvl,
                            Config._min_tvl,
                            Config._target_tvl,
                        ),
                    )
            else:
                raise AnchorException(
                    inspect.currentframe().f_code.co_name,
                    -1,
                    "unknow TVL type",
                )

            tvl = "Target"
            if type_tvl == TVL_TYPE.MIN:
                tvl = "Min"
            elif type_tvl == TVL_TYPE.MAX:
                tvl = "Max"

            await bot_telegram.send_message(
                "{} TVL changed from <code>{}%</code> to <code>{}%</code>".format(
                    tvl,
                    old_tvl,
                    new_tvl,
                )
            )

        except AnchorException as e:
            Config._log.exception(e)
            await bot_telegram.send_message(e.to_telegram_str())

        except Exception as e:
            Config._log.exception(e)

    async def set_deposit_amount(self, **kwargs):
        error_occured = False
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
                error_occured = True
                await bot_telegram.send_message(
                    "Unable to deposit, not enough liquidity"
                )
            else:
                await bot_telegram.send_message(
                    "Sending transaction ...",
                    show_keyboard=False,
                    show_typing=True,
                )
                await Anchor.do_trx(
                    self._wallet._wallet,
                    [
                        await Anchor.get_deposit_to_earn_msg(
                            wallet_address,
                            amount_to_deposit,
                        )
                    ],
                )

        except AnchorException as e:
            error_occured = True
            Config._log.exception(e)
            await bot_telegram.send_message(
                e.to_telegram_str(),
                show_keyboard=False,
                show_typing=True,
            )

        except Exception as e:
            error_occured = True
            Config._log.exception(e)
        finally:
            if error_occured == True:
                await bot_telegram.send_message("🔴 Ended with errors.")
            else:
                await bot_telegram.send_message("🟢 Done.")

    async def claim_rewards(self, **kwargs):
        error_occured = False
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
                await Anchor.do_trx(
                    self._wallet._wallet,
                    [
                        await Anchor.get_claim_anc_rewards_msg(
                            self._wallet.get_wallet_address()
                        )
                    ],
                )
            else:
                await bot_telegram.send_message(
                    "No rewards to claim",
                    show_keyboard=False,
                    show_typing=True,
                )

        except AnchorException as e:
            error_occured = True
            Config._log.exception(e)
            await bot_telegram.send_message(
                e.to_telegram_str(),
                show_keyboard=False,
                show_typing=True,
            )

        except Exception as e:
            error_occured = True
            Config._log.exception(e)
        finally:
            if error_occured == True:
                await bot_telegram.send_message("🔴 Ended with errors.")
            else:
                await bot_telegram.send_message("🟢 Done.")

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
