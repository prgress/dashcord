import asyncio

# The library imports
import dashcord

import discord
from discord.ext import commands

# Import the routing file
import routes

bot = commands.Bot(command_prefix="!", case_insensitive=True)

# The dashcord.App class takes your bot object, the path to your template folder,
# the path to your static folder, and the routing file.
app = dashcord.App(bot, template_path="templates", static_path="static", routing_file=routes)

if __name__ == "__main__":
    # In order to run both the bot and the web-server within the same asyncio loop,
    # the bot start is a bit different.
    
    loop = asyncio.get_event_loop()
    
    loop.create_task(bot.run("TOKEN"))
    loop.create_task(app.start("localhost", 5000))
    
    loop.run_forever()
    
    # dashcord.App.start() will create a variable in your bot called `dashboard`.
    # It can be accessed using bot.dashboard