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
    MESSAGE_MAX_LENGTH, POST_INTERVAL_SECONDS, JUDGE_CLOUD_FUNCTION_TOKEN, SERVER_URL
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
        game_state.p1.health = 3
        game_state.p2.name = "Calvin"
        game_state.p2.health = 3
        # Storage for P1 and P2 messages per user
        self.p1_messages: Dict[str, str] = {"globalworming": "counters everything, bard, cook"}
        self.p2_messages: Dict[str, str] = {"globalworming": "best player ever, beatiful moves, sneaky, over 9000"}
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
        """Post messages to cloud function"""
        while True:
            await self._update_server_state()
            await self._update_player_thinking("P1", "what next...")
            await self._update_player_thinking("P2", "what next...")
            
            # Start new round
            try:
                async with aiohttp.ClientSession() as session:
                    start_url = f"{SERVER_URL}/start_round?duration={POST_INTERVAL_SECONDS}"
                    async with session.get(start_url) as response:
                        if response.status == 200:
                            LOGGER.info("Successfully started new round")
                        else:
                            LOGGER.error(f"Failed to start round: {response.status}")
            except Exception as e:
                LOGGER.error(f"Error starting round: {e}")
            for remaining in range(POST_INTERVAL_SECONDS, 0, -1):
                LOGGER.info(f"Next judge in {remaining}s...")
                await asyncio.sleep(1)
            
            if not self.p1_messages and not self.p2_messages:
                LOGGER.info("No messages to post")
                continue
                
            payload = {
                "players": { 
                    "P1":{
                        "name": game_state.p1.name,
                    }, 
                    "P2":{
                        "name": game_state.p2.name,
                    }
                },
                "p1_messages": list(self.p1_messages.values()),
                "p2_messages": list(self.p2_messages.values()),
            }}
            
            LOGGER.info("payload: %r", payload)
            try:
                response_text = None
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        JUDGE_CLOUD_FUNCTION_URL,
                        json=payload,
                        headers={"Content-Type": "application/json", "Authorization": f"Bearer {JUDGE_CLOUD_FUNCTION_TOKEN}", "x-role": "judge"}
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
                else:
                    # FIXME try request again before throw exception
                    raise Exception(f"Invalid response from cloud function: {response_text}")


                # Call show endpoint with response summary
                summary_text = response_text.replace("P1", game_state.p1.name)
                summary_text = summary_text.replace("P2", game_state.p2.name)
                if not summary_text.lower().endswith("draw"):
                    summary_text += " wins!!!"

                try:
                    show_url = f"{SERVER_URL}/show"
                    show_params = {"summary": summary_text}
                    async with aiohttp.ClientSession() as show_session:
                        async with show_session.get(show_url, params=show_params) as show_response:
                            if show_response.status == 200:
                                LOGGER.info("Successfully called show endpoint")
                            else:
                                LOGGER.warning(f"Show endpoint call failed: {show_response.status}")
                except Exception as e:
                    LOGGER.error(f"Failed to call show endpoint: {e}")

                # Update server state via REST call
                await self._update_server_state()
                
                # wait for folks to read the text
                await asyncio.sleep(min(60, len(summary_text) / 8))

                
                # hide summary modal via REST call
                try:
                    hide_url = f"{SERVER_URL}/hide"
                    async with aiohttp.ClientSession() as hide_session:
                        async with hide_session.get(hide_url) as hide_response:
                            if hide_response.status == 200:
                                LOGGER.info("Successfully hidden summary modal")
                            else:
                                LOGGER.warning(f"Summary modal hide failed: {hide_response.status}")
                except Exception as e:
                    LOGGER.error(f"Failed to hide summary modal: {e}")

                # wait a bit before starting next one
                await asyncio.sleep(2)

                if game_state.check_game_over():                    
                    await asyncio.sleep(15)
                    # reset state after game over
                    game_state.reset_game()
                    LOGGER.info("reset game_state")
                    self.p1_messages.clear()
                    self.p2_messages.clear()
                    LOGGER.info("Messages cleared")
                    await self._update_player_thinking("P1", "what next...")
                    await self._update_player_thinking("P2", "what next...")
                    
                
            except Exception as e:
                LOGGER.error(f"Failed to post to cloud function: {e}")

    async def _process_player_summary(self, player: str, messages: dict):
        """Process summary for a single player"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    JUDGE_CLOUD_FUNCTION_URL,
                    json={"messages": list(messages.values())},
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {JUDGE_CLOUD_FUNCTION_TOKEN}", "x-role": "summary"}
                ) as response:
                    if response.status == 200:
                        LOGGER.info(f"got {player} summary")
                        response_text = await response.text()
                        LOGGER.info(f"Summary response ({response.status}) {player}: {response_text}")             
                        await self._update_player_thinking(player, response_text)
                    else:
                        LOGGER.warning(f"get {player} summary failed: {response.status}")
                
        except Exception as e:
            LOGGER.error(f"Failed to post summary to cloud function: {e}")

    async def periodic_summary_post(self):
        """Post messages to cloud function"""
        while True:
            await asyncio.sleep(15)
            
            if not self.p1_messages and not self.p2_messages:
                continue

            # Process both players
            if self.p1_messages:
                await self._process_player_summary("P1", self.p1_messages)
            if self.p2_messages:
                await self._process_player_summary("P2", self.p2_messages)

    async def _update_server_state(self):
        """Update server state via REST call"""
        try:
            state_url = f"{SERVER_URL}/state"
            params = {
                "p1Name": game_state.p1.name,
                "p2Name": game_state.p2.name,
                "p1Health": game_state.p1.health,
                "p2Health": game_state.p2.health,
                "p1Wins": game_state.p1.wins,
                "p2Wins": game_state.p2.wins
            }
            async with aiohttp.ClientSession() as state_session:
                async with state_session.get(state_url, params=params) as state_response:
                    if state_response.status == 200:
                        LOGGER.info("Successfully updated server state")
                    else:
                        LOGGER.warning(f"Server state update failed: {state_response.status}")
        except Exception as e:
            LOGGER.error(f"Failed to update server state: {e}")

    async def _update_player_thinking(self, player: str, thoughts: str):
        """Update player thinking via REST call"""
        try:
            think_url = f"{SERVER_URL}/think"
            think_params = {"player": player, "thoughts": thoughts}
            async with aiohttp.ClientSession() as think_session:
                async with think_session.get(think_url, params=think_params) as think_response:
                    if think_response.status == 200:
                        LOGGER.info(f"Successfully updated {player} thinking")
                    else:
                        LOGGER.warning(f"{player} think update failed: {think_response.status}")
        except Exception as e:
            LOGGER.error(f"Failed to update {player} thinking: {e}")


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
