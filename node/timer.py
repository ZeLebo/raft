import asyncio


class Timer:
    def __init__(self, interval, callback):
        self.interval = interval
        self.callback = callback
        self.task = asyncio.create_task(self.run())

    async def run(self):
        await asyncio.sleep(self.interval)
        await self.callback()

    async def stop(self):
        self.task.cancel()

    async def reset(self, interval=None):
        if interval is not None:
            self.interval = interval
        await self.stop()
        self.task = asyncio.create_task(self.run())
