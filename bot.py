import discord
from discord.ext import commands
from mcrcon import MCRcon
import os # Used for securely loading credentials

# --- Configuration ---
# It's best practice to load these from environment variables or a config file
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
RCON_HOST = os.getenv("RCON_IP")  # Your VPS IP address
RCON_PORT = 25576           # Your RCON port from server.properties
RCON_PASS = os.getenv("RCON_PASSWORD")

# A list of allowed commands to prevent abuse
ALLOWED_COMMANDS = ["whitelist"]

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def server(ctx, *, command: str):
    """Sends a command to the Minecraft server."""
    
    command_parts = command.split()
    if not command_parts or command_parts[0].lower() not in ALLOWED_COMMANDS:
        await ctx.send("❌ **Error:** That command is not allowed.")
        return

    try:
        with MCRcon(RCON_HOST, RCON_PASS, port=RCON_PORT) as mcr:
            response = mcr.command(command)
            if response:
                await ctx.send(f"✅ **Server Response:**\n```\n{response}\n```")
            else:
                await ctx.send("✅ **Command sent successfully** (no response from server).")
    except Exception as e:
        await ctx.send(f"❌ **Error:** Could not connect to the server or send command. Details: {e}")

# --- Run the Bot ---
bot.run(DISCORD_TOKEN)