import discord
from discord.ext import commands
import os # Used for securely loading credentials
from dotenv import load_dotenv
import json # Import the json library
from decimal import Decimal, InvalidOperation # For precise decimal validation

# --- Configuration ---
# It's best practice to load these from environment variables or a config file
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
BOUNTY_FILE = "bounties.json" # The file to store bounty data

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
# We still need a prefix, but since we handle commands manually, it won't be used.
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

# --- Validation Functions ---
def validate_difficulty(difficulty_str):
    """Validates and standardizes the difficulty input."""
    valid_difficulties = {
        "easy": "Easy",
        "basic": "Basic",
        "advanced": "Advanced",
        "expert": "Expert",
        "master": "Master"
    }
    lower_str = difficulty_str.lower()
    # Special check for Re:Master, must contain ':'
    if "re" in lower_str and "master" in lower_str and ":" in lower_str:
        return "Re:Master"
    
    return valid_difficulties.get(lower_str)

def validate_target(target_str):
    """Validates the target is a number between 0 and 101 with up to 4 decimal places."""
    try:
        target = Decimal(target_str)
        if not (Decimal('0') <= target <= Decimal('101')):
            return None, "Target must be between 0 and 101."
        # Check decimal places by looking at the string representation
        if '.' in target_str and len(target_str.split('.')[-1]) > 4:
            return None, "Target can have a maximum of 4 decimal places."
        return target, None
    except InvalidOperation:
        return None, "Target must be a valid number."

def validate_amount(amount_str):
    """Validates the amount is a number between 0 and 1,000,000 with up to 2 decimal places."""
    try:
        # Remove potential commas for user-friendliness
        amount_str_cleaned = amount_str.replace(',', '')
        amount = Decimal(amount_str_cleaned)
        if not (Decimal('0') <= amount <= Decimal('1000000')):
            return None, "Amount must be between 0 and 1,000,000."
        if '.' in amount_str_cleaned and len(amount_str_cleaned.split('.')[-1]) > 2:
             return None, "Amount can have a maximum of 2 decimal places."
        # Format to 2 decimal places for consistency
        return amount.quantize(Decimal('0.01')), None
    except InvalidOperation:
        return None, "Amount must be a valid number."

# --- Bounty Data Storage ---
# Load bounties from the file when the bot starts
bounties = load_bounties()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# --- Custom Command Handling via on_message ---
@bot.event
async def on_message(message):
    """
    Handles messages to check for custom commands that don't use the bot's prefix.
    """
    global bounties

    if message.author == bot.user:
        return

    content = message.content.strip()

    # --- List Bounties Command ---
    if content.lower() == "aqil>bounty":
        if not bounties:
            await message.channel.send("There are currently no active bounties.")
            return

        header = f"{'Song Name':<30} | {'Difficulty':<10} | {'Target':<8} | {'Amount (RM)':<12} | {'User':<20}\n"
        separator = f"{'-'*30}-+-{'-'*10}-+-{'-'*8}-+-{'-'*12}-+-{'-'*20}\n"
        table = header + separator

        for bounty in bounties:
            song_name = (bounty['song_name'][:27] + '...') if len(bounty['song_name']) > 30 else bounty['song_name']
            difficulty = bounty.get('difficulty', 'N/A')
            target = str(bounty['target'])
            amount = str(bounty['amount'])
            user = bounty['user']
            table += f"{song_name:<30} | {difficulty:<10} | {target:<8} | {amount:<12} | {user:<20}\n"

        await message.channel.send(f"**Current Bounties:**\n```\n{table}```")

    # --- Register Bounty Command ---
    elif content.lower().startswith("bounty>register "):
        try:
            params_str = content[len("bounty>register "):].strip()
            parts = params_str.rsplit(' ', 3)
            
            if len(parts) < 4:
                await message.channel.send("❌ **Invalid Format.** Use: `bounty>register [Song Name] [Difficulty] [Target] [Amount]`")
                return

            song_name, difficulty_str, target_str, amount_str = [p.strip() for p in parts]

            if not song_name:
                await message.channel.send("❌ **Error:** Song name cannot be empty.")
                return

            # --- Validation ---
            difficulty = validate_difficulty(difficulty_str)
            if not difficulty:
                await message.channel.send("❌ **Invalid Difficulty.** Valid values are: Easy, Basic, Advanced, Expert, Master, Re:Master.")
                return

            target, target_error = validate_target(target_str)
            if target_error:
                await message.channel.send(f"❌ **Invalid Target:** {target_error}")
                return

            amount, amount_error = validate_amount(amount_str)
            if amount_error:
                await message.channel.send(f"❌ **Invalid Amount:** {amount_error}")
                return

            bounties.append({
                "song_name": song_name,
                "difficulty": difficulty,
                "target": str(target),
                "amount": str(amount),
                "user": message.author.name
            })
            save_bounties(bounties)
            
            await message.channel.send(f"✅ **Bounty registered for '{song_name}'!**")

        except Exception as e:
            print(f"Error during bounty registration: {e}")
            await message.channel.send("❌ **Invalid Format.** Use: `bounty>register [Song Name] [Difficulty] [Target] [Amount]`")

    # --- Delete Bounty Command ---
    elif content.lower().startswith("bounty>delete "):
        song_query = content[len("bounty>delete "):].strip().lower()
        if not song_query:
            await message.channel.send("❌ **Invalid Format.** Please provide a song name to delete.")
            return

        user_matches = [
            b for b in bounties 
            if song_query in b['song_name'].lower() and b['user'] == message.author.name
        ]

        if not user_matches:
            await message.channel.send("❌ **Error:** No bounty found matching that name under your user.")
            return
        
        if len(user_matches) > 1:
            response = "Found multiple bounties matching your query. Please be more specific.\nHere are the matches:\n"
            for match in user_matches:
                response += f"- {match['song_name']}\n"
            await message.channel.send(response)
            return

        bounty_to_delete = user_matches[0]
        bounties.remove(bounty_to_delete)
        save_bounties(bounties)
        await message.channel.send(f"✅ **Successfully deleted bounty:** '{bounty_to_delete['song_name']}'")

    # --- Bounty Help Command ---
    elif content.lower() == "bounty>help":
        help_message = (
            "**Bounty Bot Commands:**\n"
            "```\n"
            "aqil>bounty\n"
            "   - Lists all active bounties.\n\n"
            "bounty>register [Song Name] [Difficulty] [Target] [Amount]\n"
            "   - Registers a new bounty.\n"
            "   - Example: bounty>register \"My Song\" Master 100.5 150.50\n\n"
            "bounty>delete [Song Name]\n"
            "   - Deletes a bounty you created. Partial names work.\n\n"
            "bounty>help\n"
            "   - Shows this help message.\n"
            "```"
        )
        await message.channel.send(help_message)


# --- Run the Bot ---
bot.run(DISCORD_TOKEN)

