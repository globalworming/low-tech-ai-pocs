"""
Minimal Twitch Chat Bot using AutoBot
- Stores latest P1: and P2: messages per user (max 200 chars)
- Posts to cloud function every 60 seconds
- Uses AutoBot for automatic OAuth handling
"""
import asyncio
import logging
import asqlite
import twitchio
from database import setup_database
from minimal_twitch_bot import MinimalTwitchBot

# Setup logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

def main() -> None:
    twitchio.utils.setup_logging(level=logging.INFO)
    
    async def runner() -> None:
        async with asqlite.create_pool("tokens.db") as tdb:
            tokens, subs = await setup_database(tdb)
            
            async with MinimalTwitchBot(token_database=tdb, subs=subs) as bot:
                for pair in tokens:
                    await bot.add_token(*pair)
                
                await bot.start(load_tokens=False)
    
    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        LOGGER.warning("Shutting down due to KeyboardInterrupt")

if __name__ == "__main__":
    main()
