import discord
from discord.ext import commands
from mcrcon import MCRcon
import os # Used for securely loading credentials
from dotenv import load_dotenv

# --- Configuration ---
# It's best practice to load these from environment variables or a config file
load_dotenv()
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

# --- Data Persistence Functions ---
def load_bounties():
    """Loads bounty data from the JSON file."""
    try:
        with open(BOUNTY_FILE, 'r') as f:
            # Check if file is empty to avoid errors
            content = f.read()
            if not content:
                return []
            return json.loads(content)
    except FileNotFoundError:
        # If the file doesn't exist, return an empty list
        return []
    except json.JSONDecodeError:
        # If the file is corrupted or not valid JSON, return empty
        print("Warning: Could not decode bounties.json. Starting with empty bounties.")
        return []

def save_bounties(data):
    """Saves the bounty data to the JSON file."""
    with open(BOUNTY_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- Bounty Data Storage ---
# Load bounties from the file when the bot starts
bounties = load_bounties()

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

# --- Custom Command Handling via on_message ---
@bot.event
async def on_message(message):
    """
    Handles messages to check for custom commands that don't use the bot's prefix.
    """
    # This is now a global variable, so we need to declare our intent to modify it
    global bounties

    # Ignore messages sent by the bot itself to prevent loops
    if message.author == bot.user:
        return

    # Allows the bot to still process commands with the "!" prefix (like !server)
    await bot.process_commands(message)

    # Standardize message content for easier checking
    content = message.content.strip()

    # --- List Bounties Command ---
    if content.lower() == "aqil>bounty":
        if not bounties:
            await message.channel.send("There are currently no active bounties.")
            return

        # Build the table string
        # We calculate padding to make it look neat
        header = f"{'Song Name':<30} | {'Target':<15} | {'Amount':<10} | {'User':<20}\n"
        separator = f"{'-'*30}-+-{'-'*15}-+-{'-'*10}-+-{'-'*20}\n"
        table = header + separator

        for bounty in bounties:
            # Truncate long song names to prevent breaking the format
            song_name = (bounty['song_name'][:27] + '...') if len(bounty['song_name']) > 30 else bounty['song_name']
            target = (bounty['target'][:12] + '...') if len(bounty['target']) > 15 else bounty['target']
            table += f"{song_name:<30} | {target:<15} | {bounty['amount']:<10} | {bounty['user']:<20}\n"

        await message.channel.send(f"**Current Bounties:**\n```\n{table}```")

    # --- Register Bounty Command ---
    elif content.lower().startswith("bounty>register "):
        try:
            # Extract parameters from the command string
            params_str = content[len("bounty>register "):].strip()
            
            # The last two words are amount and target, everything before is the song name
            parts = params_str.rsplit(' ', 2)
            
            if len(parts) < 3:
                await message.channel.send("❌ **Invalid Format.** Please include a song name, target, and amount.")
                return

            song_name = parts[0].strip()
            target = parts[1].strip()
            amount = parts[2].strip()

            if not song_name:
                await message.channel.send("❌ **Error:** Song name cannot be empty.")
                return
            if not target:
                await message.channel.send("❌ **Error:** Target cannot be empty.")
                return

            # Add the new bounty to our list
            bounties.append({
                "song_name": song_name,
                "target": target,
                "amount": amount,
                "user": message.author.name
            })
            # Save the updated list to the JSON file
            save_bounties(bounties)
            
            await message.channel.send(f"✅ **Bounty registered for '{song_name}'!**")

        except Exception as e:
            print(f"Error during bounty registration: {e}")
            await message.channel.send("❌ **Invalid Format.** Use: `bounty>register [Song Name] [Target] [Amount]`")

    # --- Bounty Help Command ---
    elif content.lower() == "bounty>help":
        help_message = (
            "**Bounty Bot Commands:**\n"
            "```\n"
            "aqil>bounty\n"
            "   - Lists all active bounties.\n\n"
            "bounty>register [Song Name] [Target] [Amount]\n"
            "   - Registers a new bounty.\n"
            "   - Example: bounty>register \"A Cruel Angel's Thesis\" FC 100k\n\n"
            "bounty>help\n"
            "   - Shows this help message.\n"
            "```"
        )
        await message.channel.send(help_message)


# --- Run the Bot ---
bot.run(DISCORD_TOKEN)

