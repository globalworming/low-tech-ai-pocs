"""
Game state message handler for the Twitch chat bot.
Handles messages related to game state changes.
"""
import logging
import asyncio
import re
from twitchio.ext import commands
import twitchio
from game_state import game_state
from config import MESSAGE_MAX_LENGTH

# Setup logging
LOGGER = logging.getLogger(__name__)

class GameStateMessageHandler(commands.Component):
    def __init__(self, bot):
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
                game_state.reset_game()
                LOGGER.info(f"Game state set: {p1} vs {p2}")
                self.bot.p1_messages.clear()
                self.bot.p2_messages.clear()
                LOGGER.info(f"Messages cleared")
                if hasattr(self.bot, "judge_task") and self.bot.judge_task:
                    self.bot.judge_task.cancel()
                self.bot.judge_task = asyncio.create_task(self.bot.periodic_jugdgement_post())
