"""
Minimal Twitch Chat Bot using AutoBot
- Stores latest P1: and P2: messages per user (max 200 chars)
- Posts to cloud function every 60 seconds
- Uses AutoBot for automatic OAuth handling
"""
import asyncio
import logging
import aiohttp
from typing import Dict, TYPE_CHECKING
from datetime import datetime
import asqlite
import twitchio
from twitchio import eventsub
from twitchio.ext import commands
from config import (
    CLIENT_ID, CLIENT_SECRET, BOT_ID, OWNER_ID, JUDGE_CLOUD_FUNCTION_URL, 
    MESSAGE_MAX_LENGTH, POST_INTERVAL_SECONDS, JUDGE_CLOUD_FUNCTION_TOKEN
)
from game_state import game_state

if TYPE_CHECKING:
    import sqlite3

# Setup logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

class MinimalTwitchBot(commands.AutoBot):
    def __init__(self, *, token_database: asqlite.Pool, subs: list[eventsub.SubscriptionPayload]):
        game_state.p1.name = "Snizzle"
        game_state.p1.health = 1
        game_state.p2.name = "Calvin"
        game_state.p2.health = 2
        # Storage for P1 and P2 messages per user
        self.p1_messages: Dict[str, str] = {"globalworming": "counters everything, goes hard"}
        self.p2_messages: Dict[str, str] = {"globalworming": "best player ever, beatiful moves"}
        self.token_database = token_database
        
        super().__init__(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            bot_id=BOT_ID,
            owner_id=OWNER_ID,
            prefix="!",
            subscriptions=subs,
        )
        
        # Start the periodic tasks
        self.judge_task = None
        self.summary_task = None

    async def setup_hook(self) -> None:
        # Add our message handler component
        await self.add_component(MessageHandler(self))
        # Start periodic tasks
        self.judge_task = asyncio.create_task(self.periodic_jugdgement_post())
        self.summary_task = asyncio.create_task(self.periodic_summary_post())

    async def event_oauth_authorized(self, payload: twitchio.authentication.UserTokenPayload) -> None:
        await self.add_token(payload.access_token, payload.refresh_token)

        if not payload.user_id or payload.user_id == self.bot_id:
            return

        # Subscribe to chat messages for authorized channel
        subs = [eventsub.ChatMessageSubscription(broadcaster_user_id=payload.user_id, user_id=self.bot_id)]
        resp = await self.multi_subscribe(subs)
        
        if resp.errors:
            LOGGER.warning("Failed to subscribe to: %r, for user: %s", resp.errors, payload.user_id)

    async def add_token(self, token: str, refresh: str) -> twitchio.authentication.ValidateTokenPayload:
        resp = await super().add_token(token, refresh)
        
        # Store tokens in database
        query = """
        INSERT INTO tokens (user_id, token, refresh)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            token = excluded.token,
            refresh = excluded.refresh;
        """
        
        async with self.token_database.acquire() as connection:
            await connection.execute(query, (resp.user_id, token, refresh))
        
        LOGGER.debug("Added token to database for user: %s", resp.user_id)
        return resp

    async def event_ready(self) -> None:
        LOGGER.debug("Bot ready | Bot ID: %s", self.bot_id)



    async def periodic_jugdgement_post(self):
        """Post messages to cloud function every 60 seconds"""
        while True:
            for remaining in range(POST_INTERVAL_SECONDS, 0, -1):
                LOGGER.info(f"Next judge in {remaining}s...")
                await asyncio.sleep(1)
            
            if not self.p1_messages and not self.p2_messages:
                LOGGER.info("No messages to post")
                continue
                
            # Prepare payload
            payload = {
                #"timestamp": datetime.now().isoformat(),
       #         "p1_messages": list(self.p1_messages.values()),
        #        "p2_messages": list(self.p2_messages.values()),
                "p1_messages": list(self.p1_messages.values()),
                "p2_messages": list(self.p2_messages.values()),
            }
            
            LOGGER.info("payload: %r", payload)
            try:
                response_text = None
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        JUDGE_CLOUD_FUNCTION_URL,
                        json=payload,
                        headers={"Content-Type": "application/json", "Authorization": f"Bearer {JUDGE_CLOUD_FUNCTION_TOKEN}", "role": "judge"}
                    ) as response:
                        response_text = await response.text()
                        LOGGER.info(f"Cloud function response ({response.status}): {response_text}")
                        
                if response_text.lower().endswith("p1"):
                    game_state.p2.take_damage(1)
                elif response_text.lower().endswith("p2"):
                    game_state.p1.take_damage(1)
                elif response_text.lower().endswith("draw"):
                    game_state.p1.take_damage(1)
                    game_state.p2.take_damage(1)
                
                if game_state.check_game_over():                    
                    # reset state after game over
                    game_state.reset_game()
                    LOGGER.info("reset game_state")
                    self.p1_messages.clear()
                    self.p2_messages.clear()
                    LOGGER.info("Messages cleared")
                
            except Exception as e:
                LOGGER.error(f"Failed to post to cloud function: {e}")

    async def periodic_summary_post(self):
        """Post messages to cloud function every 5 seconds for summary"""
        while True:
            await asyncio.sleep(5)
            

            if not self.p1_messages and not self.p2_messages:
                continue

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        JUDGE_CLOUD_FUNCTION_URL,
                        json={"messages": list(self.p1_messages.values())},
                        headers={"Content-Type": "application/json", "Authorization": f"Bearer {JUDGE_CLOUD_FUNCTION_TOKEN}", "role": "summary"}
                    ) as response:
                        response_text = await response.text()
                        LOGGER.info(f"Summary response ({response.status}) P1: {response_text}")           
            except Exception as e:
                LOGGER.error(f"Failed to post summary to cloud function: {e}")

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        JUDGE_CLOUD_FUNCTION_URL,
                        json={"messages": list(self.p2_messages.values())},
                        headers={"Content-Type": "application/json", "Authorization": f"Bearer {JUDGE_CLOUD_FUNCTION_TOKEN}", "role": "summary"}
                    ) as response:
                        response_text = await response.text()
                        LOGGER.info(f"Summary response ({response.status}) P2: {response_text}")           
            except Exception as e:
                LOGGER.error(f"Failed to post summary to cloud function: {e}")


class MessageHandler(commands.Component):
    def __init__(self, bot: MinimalTwitchBot):
        self.bot = bot

    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        # Log all messages
        LOGGER.info(f"[{payload.broadcaster.name}] - {payload.chatter.name}: {payload.text}")
        
        content = payload.text.strip()
        username = payload.chatter.name
        
        # Store P1 messages
        if content.startswith('P1:'):
            p1_content = content[3:].strip()[:MESSAGE_MAX_LENGTH]
            self.bot.p1_messages[username] = p1_content
            LOGGER.info(f"Stored P1 from {username}: {p1_content}")
            
        # Store P2 messages  
        elif content.startswith('P2:'):
            p2_content = content[3:].strip()[:MESSAGE_MAX_LENGTH]
            self.bot.p2_messages[username] = p2_content
            LOGGER.info(f"Stored P2 from {username}: {p2_content}")

async def setup_database(db: asqlite.Pool) -> tuple[list[tuple[str, str]], list[eventsub.SubscriptionPayload]]:
    """Setup token database and return existing tokens/subscriptions"""
    query = """CREATE TABLE IF NOT EXISTS tokens(user_id TEXT PRIMARY KEY, token TEXT NOT NULL, refresh TEXT NOT NULL)"""
    
    async with db.acquire() as connection:
        await connection.execute(query)
        rows: list[sqlite3.Row] = await connection.fetchall("""SELECT * from tokens""")
        
        tokens = []
        subs = []
        
        for row in rows:
            tokens.append((row["token"], row["refresh"]))
            subs.extend([eventsub.ChatMessageSubscription(broadcaster_user_id=row["user_id"], user_id=BOT_ID)])
    
    return tokens, subs

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
