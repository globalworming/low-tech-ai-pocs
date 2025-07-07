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
    CLIENT_ID, CLIENT_SECRET, BOT_ID, OWNER_ID, CLOUD_FUNCTION_URL, 
    MESSAGE_MAX_LENGTH, POST_INTERVAL_SECONDS
)

if TYPE_CHECKING:
    import sqlite3

# Setup logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

class MinimalTwitchBot(commands.AutoBot):
    def __init__(self, *, token_database: asqlite.Pool, subs: list[eventsub.SubscriptionPayload]):
        # Storage for P1 and P2 messages per user
        self.p1_messages: Dict[str, str] = {}
        self.p2_messages: Dict[str, str] = {}
        self.token_database = token_database
        
        super().__init__(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            bot_id=BOT_ID,
            owner_id=OWNER_ID,
            prefix="!",
            subscriptions=subs,
        )
        
        # Start the periodic task
        self.post_task = None

    async def setup_hook(self) -> None:
        # Add our message handler component
        await self.add_component(MessageHandler(self))
        # Start periodic posting
        self.post_task = asyncio.create_task(self.periodic_post())

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
        
        LOGGER.info("Added token to database for user: %s", resp.user_id)
        return resp

    async def event_ready(self) -> None:
        LOGGER.info("Bot ready | Bot ID: %s", self.bot_id)

    async def periodic_post(self):
        """Post messages to cloud function every 60 seconds"""
        while True:
            await asyncio.sleep(POST_INTERVAL_SECONDS)
            
            if not self.p1_messages and not self.p2_messages:
                LOGGER.info("No messages to post")
                continue
                
            # Prepare payload
            payload = {
                "timestamp": datetime.now().isoformat(),
                "p1_messages": dict(self.p1_messages),
                "p2_messages": dict(self.p2_messages)
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        CLOUD_FUNCTION_URL,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        response_text = await response.text()
                        LOGGER.info(f"Cloud function response ({response.status}): {response_text}")
                        
                # Clear messages after successful post
                self.p1_messages.clear()
                self.p2_messages.clear()
                LOGGER.info("Messages cleared")
                
            except Exception as e:
                LOGGER.error(f"Failed to post to cloud function: {e}")

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
