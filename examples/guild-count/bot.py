import asyncio

# The library imports
import dashcord

import discord
from discord.ext import commands

# Import the routing file
import routes

bot = commands.Bot(command_prefix="!", case_insensitive=True)

@bot.event
async def on_ready():
    print("Bot ready")
    # We start the dashboard in the on_ready event, to ensure everything works
    await bot.dashboard.start("localhost", 5000)
    # dashcord.App.start() takes the host and port for your server. To run it on your IP set the host to "0.0.0.0"
    
# The dashcord.App class takes your bot object, the path to your template folder,
# the path to your static folder, and the routing file.
app = dashcord.App(bot, template_path="templates", static_path="static", routing_file=routes)

if __name__ == "__main__":
    bot.run("TOKEN")