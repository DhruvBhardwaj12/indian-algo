import asyncio
from indiaopt import NSEClient

async def main():
    async with NSEClient() as nse:
        result = await nse.fetch_option_chain("NIFTY")
        for row in result.atm_window(n=1):
            print(f"Strike: {row.strike}")
            print("Available attributes:")
            for attr in dir(row):
                if not attr.startswith("_"):
                    print(f"  - {attr}")
            break

if __name__ == "__main__":
    asyncio.run(main())
    