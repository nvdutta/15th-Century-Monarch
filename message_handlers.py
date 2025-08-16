import discord
import random
from chat_engine import generate_response
from server_manager import (
    get_server_state, 
    can_respond, 
    increment_responses, 
    is_qotd_answered_today,
    reset_daily_chat
)

async def handle_message(message, client, config, facts_collection, logger):
    """Main message handler for Discord events."""
    
    # Do not respond to messages from the bot itself
    if message.author == client.user:
        return

    # Check if channel matches configured channel name
    if message.channel.name != config['bot']['channel_name']:
        return
    
    server_id = message.guild.id
    server_state = get_server_state(server_id, message.guild.name)
    
    # Check if bot can respond (daily limits, peasant unrest)
    if not can_respond(server_id, config['bot']['max_responses_per_day']):
        if server_state['peasant_unrest_percentage'] >= 101:
            logger.info(f"Peasant unrest percentage is above 100% for server {server_id}. The king is dead.")
        return
    
    trimmed_message = message.content.lower().replace("*","")

    # Handle Question of the Day
    if await handle_qotd(message, trimmed_message, server_id, server_state, config, facts_collection, logger):
        return

    # If QOTD hasn't been answered today, don't respond to other messages
    if not is_qotd_answered_today(server_id):
        return

    # Handle direct mentions
    if await handle_mention(message, client, trimmed_message, server_id, server_state, config, facts_collection, logger):
        return

    # Handle trigger words (if enabled)
    if config['bot']['random_responses']:
        await handle_trigger_words(message, trimmed_message, server_id, server_state, config, facts_collection, logger)

async def handle_qotd(message, trimmed_message, server_id, server_state, config, facts_collection, logger):
    """Handle Question of the Day messages."""
    if ("qotd:" in trimmed_message or "question of the day:" in trimmed_message) and not is_qotd_answered_today(server_id):
        logger.info(f"Received QOTD message: {trimmed_message}")
        
        # Reset daily state
        reset_daily_chat(server_id)
        logger.info(f"Peasant Unrest Percentage: {server_state['peasant_unrest_percentage']}")

        async with message.channel.typing():
            answer = generate_response(
                trimmed_message, 
                config,
                facts_collection,
                server_id,
                "ALL QUESTIONS SHOULD BE ANSWERED WITH A SPECIFIC ANSWER. Do not repeat your response. Answer in 50 words or fewer.", 
                message.author.display_name,
                server_state,
                logger
            )
            await message.reply(answer)
        
        logger.info(f"Sent QOTD response: {answer}")
        logger.info(f"Initialized new chat history for server {server_id} ({message.guild.name})")
        logger.info(f"Responses remaining: {config['bot']['max_responses_per_day'] - server_state['responses_sent']} / {config['bot']['max_responses_per_day']}.") 
        return True
    
    return False

async def handle_mention(message, client, trimmed_message, server_id, server_state, config, facts_collection, logger):
    """Handle direct mentions of the bot."""
    if message.mentions and client.user in message.mentions and not message.mention_everyone:
        logger.info(f"Received mention: {message.content}")
        
        # Check if this is the last response of the day
        if server_state["responses_sent"] == config['bot']['max_responses_per_day']:
            async with message.channel.typing():
                answer = generate_response(
                    "", 
                    config,
                    facts_collection,
                    server_id,
                    "Offer a short, vague excuse for why you must leave for the rest of the day, and give a goodbye.",
                    "",
                    server_state,
                    logger
                )
                await message.channel.send(answer)
            
            logger.info(f"Sent farewell response: {answer}")
            logger.info(f"Responses remaining: {config['bot']['max_responses_per_day'] - server_state['responses_sent']} / {config['bot']['max_responses_per_day']}. Day complete.")
            increment_responses(server_id)
            return True

        async with message.channel.typing():
            answer = generate_response(
                trimmed_message, 
                config,
                facts_collection,
                server_id,
                "The user is talking to you directly.", 
                message.author.display_name,
                server_state,
                logger
            )
            await message.reply(answer)
        
        logger.info(f"Sent mention response: {answer}")
        increment_responses(server_id)
        logger.info(f"Responses remaining: {config['bot']['max_responses_per_day'] - server_state['responses_sent']} / {config['bot']['max_responses_per_day']}.")
        return True
    
    return False

async def handle_trigger_words(message, trimmed_message, server_id, server_state, config, facts_collection, logger):
    """Handle trigger word responses (when random_responses is enabled)."""
    trigger_words = config['triggers']['words']
    max_responses = config['bot']['max_responses_per_day']
    
    # Check if message contains trigger words or long messages can randomly trigger
    should_respond = (
        any(word in message.content.lower() for word in trigger_words) or 
        (len(message.content) > 80 and random.randint(1, 100) <= 2 * (max_responses - server_state["responses_sent"]))
    )
    
    if should_respond:
        async with message.channel.typing():
            answer = generate_response(
                trimmed_message, 
                config,
                facts_collection,
                server_id,
                "The user's message is not addressed to you, but assert your opinion on what the user said.", 
                message.author.display_name,
                server_state,
                logger
            )
            await message.reply(answer) 
        
        logger.info(f"Sent trigger response: {answer}")
        increment_responses(server_id)
        logger.info(f"Responses remaining: {max_responses - server_state['responses_sent']} / {max_responses}.")

async def on_ready_handler(client, logger):
    """Handle bot ready event."""
    logger.info(f"Logged in as {client.user} (ID: {client.user.id})")