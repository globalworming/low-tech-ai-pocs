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
import random
from database import setup_database
from elevenlabs import play
from urllib.parse import quote
import asqlite
import twitchio
from twitchio import eventsub
from twitchio.ext import commands
from config import (
    CLIENT_ID, CLIENT_SECRET, BOT_ID, OWNER_ID, JUDGE_CLOUD_FUNCTION_URL, SPEECH_ENABLED,
    MESSAGE_MAX_LENGTH, POST_INTERVAL_SECONDS, JUDGE_CLOUD_FUNCTION_TOKEN, SERVER_URL
)
from game_state import game_state, Fighter

if TYPE_CHECKING:
    import sqlite3

# Setup logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

class MinimalTwitchBot(commands.AutoBot):
    def __init__(self, *, token_database: asqlite.Pool, subs: list[eventsub.SubscriptionPayload]):
        game_state.p1.name = "Olivia"
        game_state.p1.health = 1
        game_state.p2.name = "Athena"
        game_state.p2.health = 1
        # Storage for P1 and P2 messages per user
        self.p1_messages: Dict[str, str] = {"globalworming": "lightspeed jetpack, can cross the the event horizon twice"}
        self.p2_messages: Dict[str, str] = {"globalworming": "targeted rockets travelling through the ether"}
        self.token_database = token_database
        self.remaining = 0  # Countdown timer for next judgment
        
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

        await self.add_component(GameStateMessageHandler(self))
        await self.add_component(SimpleCommands(self))

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
        LOGGER.info(f"Registered commands: {list(self.commands.keys())}")
    
    async def periodic_jugdgement_post(self):
        """Post messages to cloud function"""
        while True:
            await self._update_server_state()
            await self._update_player_thinking(game_state.p1, "what next...")
            await self._update_player_thinking(game_state.p2, "what next...")
            await self._hide_summary()
            
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
                self.remaining = remaining
                #LOGGER.info(f"Next judge in {remaining}s...")
                await asyncio.sleep(1)
            self.remaining = 0
            
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
            }
            
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

                if (SPEECH_ENABLED):
                    try:    
                        await self._tts(summary_text)
                    except Exception as e:
                        await asyncio.sleep(min(60, len(summary_text) / 8))
                else:
                    await asyncio.sleep(min(60, len(summary_text) / 8))

                await asyncio.sleep(2)
                
                await self._hide_summary()
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
                    await self._update_player_thinking(game_state.p1, "what next...")
                    await self._update_player_thinking(game_state.p2, "what next...")
                    
                
            except Exception as e:
                LOGGER.error(f"Failed to post to cloud function: {e}")

    async def _process_player_summary(self, player: Fighter, messages: dict):
        #if self.remaining <= 10:
        #    return
        """Process summary for a single player"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    JUDGE_CLOUD_FUNCTION_URL,
                    json={"messages": list(messages.values())},
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {JUDGE_CLOUD_FUNCTION_TOKEN}", "x-role": "summary"}
                ) as response:
                    if response.status == 200:
                        #LOGGER.info(f"got {player} summary")
                        response_text = await response.text()
                        LOGGER.info(f"Summary response ({response.status}) {player}: {response_text}")             
                        await self._update_player_thinking(player, response_text)
                        if self.remaining > 10:
                            text = f"{player.name} considers: {response_text}"
                            try:
                                await self._tts(text)
                            except Exception as e:
                                LOGGER.warning(f"get {player} summary failed: {response.status}")
                    else:
                        LOGGER.warning(f"get {player} summary failed: {response.status}")
                
        except Exception as e:
            LOGGER.error(f"Failed to post summary to cloud function: {e}")

    async def _tts(self, text: str):
        if not SPEECH_ENABLED:
            return
        """Play text to speech"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://0.0.0.0:8001/tts?text={text}") as response:
                    if response.status == 200:
                        LOGGER.info("Successfully called TTS endpoint")
                    else:
                        raise Exception(f"Failed to call TTS endpoint: {response.status} - {await response.text()}")
        except Exception as e:
            raise e

    async def periodic_summary_post(self):
        while True:
            if not self.p1_messages and not self.p2_messages:
                await asyncio.sleep(1)
                continue
            p1_first = random.choice([True, False])
            if game_state.p1.health > game_state.p2.health:
                p1_first = False
            elif game_state.p2.health > game_state.p1.health:
                p1_first = True

            if p1_first:
                if self.p1_messages:
                    await self._process_player_summary(game_state.p1, self.p1_messages)
                    await asyncio.sleep(10)            
                if self.p2_messages:
                    await self._process_player_summary(game_state.p2, self.p2_messages)
            else:
                if self.p2_messages:
                    await self._process_player_summary(game_state.p2, self.p2_messages)
                    await asyncio.sleep(10)
                if self.p1_messages:
                    await self._process_player_summary(game_state.p1, self.p1_messages)
            await asyncio.sleep(10)
            
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

    async def _update_player_thinking(self, player: Fighter, thoughts: str):
        """Update player thinking via REST call"""
        try:
            think_url = f"{SERVER_URL}/think"
            think_params = {"player": "P1" if player == game_state.p1 else "P2", "thoughts": thoughts}
            async with aiohttp.ClientSession() as think_session:
                async with think_session.get(think_url, params=think_params) as think_response:
                    if think_response.status == 200:
                        LOGGER.info(f"Successfully updated {player.name} thinking")
                    else:
                        LOGGER.warning(f"{player.name} think update failed: {think_response.status}")
        except Exception as e:
            LOGGER.error(f"Failed to update {player.name} thinking: {e}")

    async def _hide_summary(self):
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

import re
from game_state import game_state

class SimpleCommands(commands.Component):

    def __init__(self, bot: MinimalTwitchBot) -> None:
        self.bot = bot
        self.speak_enabled = False
    
    @commands.command(name="")
    async def help(self, ctx: commands.Context):
        pass

    @commands.command(name="commands")
    async def help(self, ctx: commands.Context):
        commands_list = "commands: !p1, !p2, !commands"
        if self.speak_enabled:
            commands_list += ", !speak"
        await ctx.send(commands_list)        

    @commands.command()
    async def p1(self, ctx: commands.Context, *, content: str = ""):
        if content.strip() == "":
            await ctx.send("usage: !p1 <message> – like !p1 has ninja skills")
            return

        """Store P1 message for the user"""
        username = ctx.author.name
        p1_content = content.strip()[:MESSAGE_MAX_LENGTH]
        self.bot.p1_messages[username] = p1_content
        LOGGER.info(f"Stored P1 from {username}: {p1_content}")
    
    @commands.command()
    async def p2(self, ctx: commands.Context, *, content: str = ""):
        if content.strip() == "":
            await ctx.send("usage: !p2 <message> – like !p2 has ninja skills")
            return

        """Store P2 message for the user"""
        username = ctx.author.name
        p2_content = content.strip()[:MESSAGE_MAX_LENGTH]
        self.bot.p2_messages[username] = p2_content
        LOGGER.info(f"Stored P2 from {username}: {p2_content}")

    @commands.command()
    async def speak(self, ctx: commands.Context, *, content: str = "what do you want?"):
        if content.strip() == "what do you want?":
            await ctx.send("usage: !speak <message> –like !speak welcome to worms AI brawl")
            
        if not self.speak_enabled:
            if ctx.chatter.name != "globalworming":
                return
        self.speak_enabled = True
        """Play text to speech"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://t431s:8002/tts?text={quote(content)}&speakerJson=summary.json") as response:
                    if response.status == 200:
                        LOGGER.info("Successfully called TTS endpoint")
                        wav_bytes = await response.read()
                        play(wav_bytes)
                    else:
                        response_json = await response.json()
                        text = response_json.get("detail", "Error")
                        await ctx.send(f"TTS: {response.status} {text}")
                        raise Exception(f"Failed to call TTS endpoint: {response.status} - {text}")
        except Exception as e:
            raise e

    @commands.command("!speak")
    async def stop_speak(self, ctx: commands.Context):
        self.speak_enabled = False

class GameStateMessageHandler(commands.Component):
    def __init__(self, bot: MinimalTwitchBot):
        self.bot = bot

    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        # Log all messages
        #LOGGER.info(f"[{payload.broadcaster.name}] - {payload.chatter.name}: {payload.text}")
        
        content = payload.text.strip()
        content = content.strip()[:MESSAGE_MAX_LENGTH]
        username = payload.chatter.name
        if username == "globalworming":
            LOGGER.info(f"{username}: {content}")
            match = re.match(r"^game (.*) vs (.*)$", content, re.IGNORECASE)
            if match:
                p1, p2 = match.group(1).strip(), match.group(2).strip()
                game_state.set_players(p1, p2)
                LOGGER.info(f"Game state set: {p1} vs {p2}")
                self.bot.p1_messages.clear()
                self.bot.p2_messages.clear()
                LOGGER.info(f"Messages cleared")
                if hasattr(self.bot, "judge_task") and self.bot.judge_task:
                    self.bot.judge_task.cancel()
                self.bot.judge_task = asyncio.create_task(self.bot.periodic_jugdgement_post())


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
