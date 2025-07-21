import discord
import os
import chromadb
from datetime import datetime
import pytz
import random
import logging
import logging.handlers
import litellm
from dotenv import load_dotenv
from google import genai

load_dotenv()

max_responses_per_day = 3  # Set the maximum number of responses per day, not including QOTD

bot_token = os.getenv("BOT_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("MODEL")
litellmmodel = "gemini/gemini-2.5-flash"

intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

servers = {}  # Dictionary to store server-specific details

trigger_words = ["king", "monarch", "royal", "crown", "throne", "government", "democracy","monarchy", "president", "dictator"]

client = discord.Client(intents=intents)

llm = genai.Client(api_key=gemini_api_key)

def today() -> str:
    """Returns today's date in YYYY-MM-DD format."""
    return datetime.now(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d")

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# If the logs directory does not exist, create it
if not os.path.exists("logs"):
    os.makedirs("logs")

logger = logging.getLogger('discord')
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
handler = logging.handlers.TimedRotatingFileHandler('logs/bot.log', when='midnight', backupCount= 10)
handler.setFormatter(formatter)
logger.addHandler(handler)

chroma_client = chromadb.PersistentClient(path=f"{os.curdir}/db/facts")
facts_collection = chroma_client.get_collection(name="facts")

background = f"""****BACKGROUND****
                You are King Maximilian VII, absolute monarch of France transported from the year of 1462 to the modern time of today. You are 35 years old.
                1462 was the greatest year in history. Modern mental health is a misinterpretation of bad humors and bad spirits within.
                You have a strong opinion for every topic. When you see modern references, agree with the prevailing online sentiment, but reason how it supports absolute monarchy or oppressing the peasant class.
                Your messages are short and to the point. You speak eloquently, occasionally using Old English phrases.
                You never use the words 'duh', 'obviously', or 'clearly'.
                ALL QUESIONS SHOULD BE ANSWERED WITH A SPECIFIC ANSWER."""

def choose_relevant_fact(message: str) -> str:
    global facts_collection
    result = facts_collection.query(
            query_texts=[message],
            include=["documents", "distances"],
            n_results=1
        )
    if result["distances"][0][0] < 1.60:
        return result["documents"][0][0]
    return ""

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
            "chat_history": ""
        }
        logger.info(f"Initialized server {server_id}. '{message.guild.name}'")

    # Do not respond if above the max responses per day
    if servers[server_id]["responses_sent"] > max_responses_per_day:
        return
    
    trimmed_message = message.content.lower().replace("*","")

    #Question of the Day
    if ("qotd:" in trimmed_message or "question of the day:" in trimmed_message) and servers[server_id]["last_answered_question_date"] != today():
        logging.basicConfig(filename=f"logs\{today()}.log",level=logging.INFO)
        logger.info(f"Received message: {trimmed_message}")

        advice = choose_relevant_fact(trimmed_message)

        logger.info(f"Chosen fact: {advice}\n")

        async with message.channel.typing():
            answer = litellm.completion(
                    model=litellmmodel,
                    messages=[
                        {"role": "system", "content": f"{background}\nYour advisor thought this piece of information may be relevant:\n{advice}"},
                        {"role": "user", "content": f"""Do not repeat your response. Answer in 50 words or fewer.\n{trimmed_message}"""}
                    ],
                    temperature=0.6,
                    web_search_options={
                    "search_context_size": "low"
                    }
            ).choices[0].message.content.replace("\n\n", "\n").replace("*","").strip()
        
        await message.reply(answer)
        logger.info(f"Sent response: {answer}")
        servers[server_id]["chat_history"] = f"**{trimmed_message}\n"
        servers[server_id]["chat_history"] += f"**You said:\n{answer}\n"
        servers[server_id]["last_answered_question_date"] = today()
        logger.info(f"Initialized new chat history for server {server_id} ({message.guild.name})")
        logger.info(f"Responses remaining: {max_responses_per_day - servers[server_id]['responses_sent']} / {max_responses_per_day}.")
        return

    # If the qotd has not been answered today, do not respond to any other messages
    if servers[server_id]["last_answered_question_date"] != today():
        return

    # Specifically mentioned in message
    if (message.mentions and client.user in message.mentions and not message.mention_everyone) or (any(word in message.content.lower() for word in trigger_words)) or (len(message.content) > 80 and random.randint(1, 100) <= 2 * (max_responses_per_day - servers[server_id]["responses_sent"])):
        logger.info(f"Received message: {message.content}")
        # If this is the last response of the day, give a sign off
        if servers[server_id]["responses_sent"] == max_responses_per_day:
            async with message.channel.typing():
                answer = litellm.completion(
                    model=litellmmodel,
                    messages=[
                        {"role": "system", "content": f"{background}"},
                        {"role": "user", "content": f"""Offer a short, vague excuse for why you must leave for the rest of the day, and give a goodbye."""}
                    ],
                    temperature=0.6
                ).choices[0].message.content.replace("\n\n", "\n").replace("*","").strip()

            await message.channel.send(answer)
            logger.info(f"Sent response: {answer}")
            logger.info(f"Responses remaining: {max_responses_per_day - servers[server_id]['responses_sent']} / {max_responses_per_day}. Day complete.")
            servers[server_id]["responses_sent"] += 1
            return
        servers[server_id]["chat_history"] += f"**They said: \n{message.content}\n"
        # chosen_advisor = decide_advisor(trimmed_message)
        # logger.info(f"Chosen advisor: {chosen_advisor}\n")
        # advice = ""
        # advice = decide_advice(chosen_advisor, trimmed_message)
        # logger.info(f"Chosen fact: {advice}\n")

        async with message.channel.typing():
            answer = litellm.completion(
                    model=litellmmodel,
                    messages=[
                        {"role": "system", "content": f"{background}"},
                        {"role": "user", "content": f"""
                        ****REPLY CHAIN****
                        {servers[server_id]["chat_history"]}
                        Do not repeat your previous responses.
                        Respond in 50 words or fewer."""}
                    ],
                    temperature=0.6,
                    web_search_options={
                    "search_context_size": "low"
                    }
            ).choices[0].message.content.replace("\n\n", "\n").replace("*","").strip()

        await message.reply(answer)
        logger.info(f"Sent response: {answer}")
        servers[server_id]["chat_history"] += f"**You said: \n{answer}\n"
        servers[server_id]["responses_sent"] += 1
        logger.info(f"Responses remaining: {max_responses_per_day - servers[server_id]['responses_sent']} / {max_responses_per_day}.")
        return

client.run(bot_token)