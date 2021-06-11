from Observable import Observable
from config import Config
import asyncio
import sys
import contextlib


class Looper(Observable):
    def __init__(self, do_job_method, wait_delay_s):
        Observable.__init__(self)

        self._do_job_method = do_job_method
        self._wait_delay_s = wait_delay_s

        self._do_stop_evt = asyncio.Event()
        self._stopped_evt = asyncio.Event()
        self._is_running = False

    async def start(self):
        try:
            self._do_stop_evt.clear()
            self._stopped_evt.clear()
            self._is_running = False

            await asyncio.gather(self.loop())

        except Exception as e:
            Config._log.exception(e)

    async def stop(self):
        try:
            if self._is_running == True:
                self._do_stop_evt.set()
                await self._stopped_evt.wait()
                self._is_running = False

        except Exception as e:
            Config._log.exception(e)

    async def loop(self):
        try:
            while not self._do_stop_evt.is_set():
                self._is_running = True
                await self._do_job_method()
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(self._do_stop_evt.wait(), self._wait_delay_s)

        except Exception as e:
            Config._log.exception(e)
        finally:
            self._stopped_evt.set()
            self._is_running = False
