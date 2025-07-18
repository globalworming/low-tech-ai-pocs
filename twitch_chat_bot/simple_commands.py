"""
Simple commands for the Twitch chat bot.
Provides basic commands like !p1, !p2, !help, !speak, etc.
"""
import logging
import aiohttp
from urllib.parse import quote
from elevenlabs import play
from twitchio.ext import commands
from config import MESSAGE_MAX_LENGTH

# Setup logging
LOGGER = logging.getLogger(__name__)

class SimpleCommands(commands.Component):

    def __init__(self, bot) -> None:
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
