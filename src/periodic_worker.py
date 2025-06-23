import asyncio


async def periodic_worker():
    while True:
        print("Running periodic task...")

        await asyncio.sleep(60)
