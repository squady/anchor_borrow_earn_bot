from bot_telegram import bot_telegram
from Observable import Observable
import logging
import asyncio
import sys
import contextlib
from terra_wallet import TerraWallet
from anchor import Anchor, AnchorException
from action import Action







class Looper(Observable):
    def __init__(self, wallet: TerraWallet, target_tvl, min_tvl, max_tvl):
        Observable.__init__(self)

        self._log = logging.getLogger("borrow_bot")

        self._do_stop_evt = asyncio.Event()
        self._stopped_evt = asyncio.Event()
        self._is_running = False

        self._wallet = wallet
        self._target_tvl = target_tvl
        self._min_tvl = min_tvl
        self._max_tvl = max_tvl

    def change_target_tvl(self, target_tvl):
        previous_tvl = self._target_tvl
        try:
            self._target_tvl = float(target_tvl)

        except Exception as e:
            self._log.exception(e)
            self._target_tvl = previous_tvl


    def change_min_tvl(self, min_tvl):

        previous_min_tvl = self._min_tvl
        try:
            self._min_tvl = float(min_tvl)

        except Exception as e:
            self._log.exception(e)
            self._min_tvl = previous_min_tvl

    def change_max_tvl(self, max_tvl):

        previous_max_tvl = self._max_tvl
        try:
            self._max_tvl = float(max_tvl)

        except Exception as e:
            self._log.exception(e)
            self._max_tvl = previous_max_tvl     


    async def start(self):
        try:
            self._do_stop_evt.clear()
            self._stopped_evt.clear()
            self._is_running = False

            await asyncio.gather(self.loop())

        except Exception as e:
            self._log.exception(e)

    async def stop(self):
        try:
            if (self._is_running == True):
                self._do_stop_evt.set()
                await self._stopped_evt.wait()
                self._is_running = False


        except Exception as e:
            self._log.exception(e)


    async def loop(self):
        try:
            while not self._do_stop_evt.is_set():
                self._is_running = True
                await self.do_job()
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(self._do_stop_evt.wait(), 20)

        except Exception as e:
            self._log.exception(e)
        finally:
            self._stopped_evt.set()
            self._is_running = False

    async def do_job(self):
        try:
            self._log.info("Hello, job is starting...")

            wallet_address = self._wallet.get_wallet_address()

            current_tvl = await Anchor.get_current_tvl(wallet_address)
            if (current_tvl is not None):
                if (current_tvl < self._min_tvl):
                    await self.async_set(Action.TVL_TOO_LOW, current_tvl=current_tvl)
                elif (current_tvl > self._max_tvl):
                    await self.async_set(Action.TVL_TOO_HIGH, current_tvl=current_tvl)
                else:
                    self._log.info("nothing to do")

        except AnchorException as e:
            await bot_telegram.send_message(e.to_telegram_str())

        except Exception as e:
            self._log.exception(e)
        
