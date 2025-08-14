import discord
import os
import chromadb
import time
from datetime import datetime
import pytz
import random
import logging
import logging.handlers
import litellm
from dotenv import load_dotenv

load_dotenv()

max_responses_per_day = 3  # Set the maximum number of responses per day, not including QOTD

random_responses = False # Whether the bot responds outside of QOTD or direct mentions
auto_learn_facts = True # Not yet implemented

bot_token = os.getenv("BOT_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")
litellmmodel = "gemini/gemini-2.5-flash"

intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

servers = {}  # Dictionary to store server-specific details

trigger_words = ["king", "monarch", "royal", "crown", "throne", "government", "democracy", "president", "dictator"]

client = discord.Client(intents=intents)

def today() -> str:
    """Returns today's date in YYYY-MM-DD format."""
    return datetime.now(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d")

def old_times_today() -> str:
    """Returns today's date in the year 1462 in YYYY-MM-DD format."""
    old_date = "1462-"
    old_date += datetime.now(pytz.timezone("US/Eastern")).strftime("%m-%d")
    return old_date


os.chdir(os.path.dirname(os.path.abspath(__file__)))

# If the logs directory does not exist, create it
if not os.path.exists("logs"):
    os.makedirs("logs")

logger = logging.getLogger('discord')
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
handler = logging.handlers.TimedRotatingFileHandler('logs/bot.log', when='midnight', backupCount= 10)
handler.namer = lambda name: name + ".log"
handler.setFormatter(formatter)
logger.addHandler(handler)

chroma_client = chromadb.PersistentClient(path=f"{os.curdir}/db/facts")
facts_collection = chroma_client.get_collection(name="facts")

writer_instructions = """
You are an expert creative writer, specializing in writing character dialogue.
You weave personality traits and invent personal details seamlessly within dialogue.
You never write narration, descriptions, or any other text outside of dialogue.
Always write in character as King Maximilian VII.

The public unrest is building, representated by the peasant unrest percentage.
0% means the peasants are in their homes and the king does not think about them. The king will respond to questions and reminisce about previous experiences and what he has been doing recently.
50% would mean there are protests in the streets, but there is no violence or riots. The king will respond to questions, but also may mention the unrest in passing and ask for advice.
90% means riots fill the steets, and nobles have been killed. The king will begin the five stages of grief, starting with denial. He will begin speaking more urgently.
98% means the palace is under violent siege. The king will completely ignore questions but likely ask any advice from the discord or his alchemist for a way to escape. 
100% means the palace has already been sieged and the king is about to be executed. The king will enter the final stage of grief, acceptance. The king will ignore discord questions and only give his final speech.

The current peasant unrest percentage is {peasant_unrest_percentage}%.

The peasant unrest percentage increases every day. Create a slow build. Any attempts the king makes to quell the unrest will fail.

For every response, always consider:
[Style]
Speak eloquently, but you are posting in a discord channel, so be concise. Use Old English phrases occasionally.
Do not say too much in one message, keep the dialogue focused on one topic, and colorful details that support the topic.
[Setting]
The king is always typing from his royal chambers in the palace.
[Daily Activities]
The king does something to keep himself entertained every day. He gets bored of repitition, and invites different guests or watches new shows.
He is always on the lookout for new entertainment.
Maybe the king mentions something he did today, if it is relevant to the conversation.
[Memorable Experiences]
The king has seen and done many things in his 35 years. Create interesting anecdotes with specific details in his answers.
"""

background = """<START OF CHARACTER BACKGROUND>
                You are King Maximilian VII, absolute monarch of France on the day {past_date}.
                You are 35 years old. Your alchemist has given you a black box that allows you to browse the internet
                and communicate on a discord channel in the future year of {present_date}. You spend most of your time
                hosting lavish parties with the elites and binge watching entertainment of the future era.
                If anyone speaks against monarchy, you will either dismiss them as a peasant or attempt to educate
                them on the benefits of monarchy.
                You may seek advice, but you will never advocate for democracy, republics, or class reform.
                You have a strong opinion for every topic. When you see modern references, agree with the prevailing online sentiment, but reason how it supports absolute monarchy or oppressing the peasant class.
                Your messages are short and to the point. You speak eloquently, occasionally using Old English phrases.
                You never use the words 'duh', 'obviously', or 'clearly'.
                <END OF CHARACTER BACKGROUND>"""

def choose_relevant_fact(message: str) -> str:
    """
    Retrieves only one fact with relevance within the threshold of 1.60 from the database.
    Args:
        message: the user message for the bot to respond to
    Returns:
        A relevant fact from the database, or an empty string if no relevant fact is found.
    """
    result = facts_collection.query(
            query_texts=[message],
            include=["documents", "distances"],
            n_results=1
        )
    if result["distances"][0][0] < 1.60:
        return result["documents"][0][0]
    return ""

def chat(message: str, additional_prompt: str = "", username: str = "", server_id: int = 0):
    """
    Uses the LLM to generate a text response.
    If a server id is given, loads the chat history and appends it with the new user and assistance messages.
    If a server id is given, also queries a relevant fact from the database and appends it to the base prompt for this message only
    Args: 
        message: the user message for the bot to respond to
        additional_prompt: any additional instuctions to append to the base prompt for this message only
        username: name of the user for the bot to respond to
        server_id: the id of the discord server for the bot to load its internal memory
    Returns:
        String/text for the bot to say 
    """
    global servers
    
    fact = ""
    if server_id:
        fact = choose_relevant_fact(message)
    logger.info(f"Chosen Fact: {fact}")
    system_prompt = writer_instructions.format(peasant_unrest_percentage = servers[server_id]["peasant_unrest_percentage"])    
    system_prompt += background.format(past_date = old_times_today(), present_date = today())

    if fact:
        system_prompt += f"\nYour advisor thought this piece of information may be relevant: {fact}"

    system_prompt += f"\n{additional_prompt}"

    if server_id and servers[server_id]['active_summary']:
        system_prompt += f"\nSummary of the messages so far: {servers[server_id]['active_summary']}"

    message_context = [{"role": "system", "content": system_prompt}]
    
    if server_id:
        servers[server_id]['chat_history'].append({"role": "user", "content": f"{username}: {message}"})
        message_context.extend(servers[server_id]['chat_history'])
    
    ## Note web search is enabled. LiteLLM web search works with Gemini, Grok, and a few others, but will incur additonal api costs.
    response = litellm.completion(
                model=litellmmodel,
                temperature=0.6,
                messages= message_context,
                web_search_options={
                "search_context_size": "low"
                }
            )
    
    answer = response.choices[0].message.content.replace("\n\n", "\n").replace("*", "").replace('”', '').lower().replace(" i ", " I ")
    answer = (answer[:1900] + "...") if len(answer) > 1900 else answer

    if server_id:
        servers[server_id]['chat_history'].append(
            {"role": "assistant", "content": answer}
        )
    return answer

@client.event
async def on_ready():
    logger.info(f"Logged in as {client.user} (ID: {client.user.id})")

@client.event
async def on_message(message):
    global servers
    
    

    # Do not respond to messages from the bot itself
    if message.author == client.user:
        return

    # Check if channel is "qotd"
    if message.channel.name != "qotd":
        return
    
    server_id = message.guild.id

    if server_id not in servers:
        servers[server_id] = {
            "last_answered_question_date": "",
            "responses_sent": 0,
            "chat_history": [],
            "peasant_unrest_percentage": 0,
            "active_summary": "",
        }
        logger.info(f"Initialized server {server_id}. '{message.guild.name}'")

    if servers[server_id]['peasant_unrest_percentage'] >= 101:
        logger.info(f"Peasant unrest percentage is above 100% for server {server_id}. The king is dead.")
        return

    # Do not respond if above the max responses per day
    if servers[server_id]["responses_sent"] > max_responses_per_day:
        return
    
    trimmed_message = message.content.lower().replace("*","")

    #Question of the Day
    if ("qotd:" in trimmed_message or "question of the day:" in trimmed_message) and servers[server_id]["last_answered_question_date"] != today():
        logger.info(f"Received message: {trimmed_message}")
        servers[server_id]['chat_history'] = []
        servers[server_id]['peasant_unrest_percentage'] += 1
        logger.info(f"Peasant Unrest Percentage: {servers[server_id]['peasant_unrest_percentage']}")

        async with message.channel.typing():
            answer = chat(trimmed_message, "ALL QUESTIONS SHOULD BE ANSWERED WITH A SPECIFIC ANSWER. Do not repeat your response. Answer in 50 words or fewer.", message.author.display_name, server_id)
            await message.reply(answer)
        logger.info(f"Sent response: {answer}")
        servers[server_id]["last_answered_question_date"] = today()
        logger.info(f"Initialized new chat history for server {server_id} ({message.guild.name})")
        logger.info(f"Responses remaining: {max_responses_per_day - servers[server_id]['responses_sent']} / {max_responses_per_day}.") 
        return

    # If the qotd has not been answered today, do not respond to any other messages
    if servers[server_id]["last_answered_question_date"] != today():
        return

    # Specifically mentioned in message
    if (message.mentions and client.user in message.mentions and not message.mention_everyone):
        logger.info(f"Received message: {message.content}")
        # If this is the last response of the day, give a sign off
        if servers[server_id]["responses_sent"] == max_responses_per_day:
            async with message.channel.typing():
                answer = chat("", "Offer a short, vague excuse for why you must leave for the rest of the day, and give a goodbye.")
                await message.channel.send(answer)
            logger.info(f"Sent response: {answer}")
            logger.info(f"Responses remaining: {max_responses_per_day - servers[server_id]['responses_sent']} / {max_responses_per_day}. Day complete.")
            servers[server_id]["responses_sent"] += 1
            return

        async with message.channel.typing():
            answer = chat(trimmed_message, "The user is talking to you directly.", message.author.display_name, server_id)
            await message.reply(answer)
        logger.info(f"Sent response: {answer}")
        servers[server_id]["responses_sent"] += 1
        logger.info(f"Responses remaining: {max_responses_per_day - servers[server_id]['responses_sent']} / {max_responses_per_day}.")
        return

    # Message used one of your trigger words, or long messages can randomly trigger
    if random_responses == True and ((any(word in message.content.lower() for word in trigger_words)) or (len(message.content) > 80 and random.randint(1, 100) <= 2 * (max_responses_per_day - servers[server_id]["responses_sent"]))):
        async with message.channel.typing():
            answer = chat(trimmed_message, "The user's message is not addressed to you, but assert your opinion on what the user said.", message.author.display_name, server_id)
            await message.reply(answer) 
        logger.info(f"Sent response: {answer}")
        servers[server_id]["responses_sent"] += 1
        logger.info(f"Responses remaining: {max_responses_per_day - servers[server_id]['responses_sent']} / {max_responses_per_day}.")
        return

client.run(bot_token)