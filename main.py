import discord
from config import load_config, get_env_vars
from database import initialize_database
from utils import setup_logging
from message_handlers import handle_message, on_ready_handler

def main():
    """Main entry point for the Monarch Bot."""
    # Load configuration
    config = load_config()
    env_vars = get_env_vars()
    
    # Setup logging
    logger = setup_logging(config)
    
    # Initialize database
    facts_collection = initialize_database(config)
    
    # Setup Discord client
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        await on_ready_handler(client, logger)
    
    @client.event
    async def on_message(message):
        await handle_message(message, client, config, facts_collection, logger)
    
    # Run the bot
    client.run(env_vars['bot_token'])

if __name__ == "__main__":
    main()