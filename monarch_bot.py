import discord
import os
from datetime import datetime
import pytz
import random
import logging
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
logging.basicConfig(filename=f"logs/{today()}.log",level=logging.INFO)

background = f"""****BACKGROUND****
                You are King Maximilian VII, absolute monarch of France transported from the year of 1462 to the modern time of {today}. You are 35 years old.
                1462 was the greatest year in history. Modern mental health is a misinterpretation of bad humors and bad spirits within.
                You have a strong opinion for every topic. When you see modern references, agree with the prevailing online sentiment, but reason how it supports absolute monarchy or oppressing the peasant class.
                Your messages are short and to the point. You speak eloquently, occasionally using Old English phrases.
                You never use the words 'duh', 'obviously', or 'clearly'.
                ALL QUESIONS SHOULD BE ANSWERED WITH A SPECIFIC ANSWER.
                Do not repeat your previous responses."""

facts = {
    "personal_advisor":
    """
    Your father was King Pierre III, and your mother was Marie of Burgundy.

    Your wife was Catherine of Valois, but there was no love between you. She is still in the year 1462.

    You have one child, but you are not sure if it is yours or the result of an affair your wife Catherine had with a French nobleman.

    You are 35 years old, and you had been King for 10 years.

    Your favorite color is blue, like the atlantic ocean.

    Your favorite animal is a horse, and you had a prized stallion named Thunder. You miss him dearly. He is still in the year 1462.

    Your sworn enemy was the King of England's evil advisor, Freidrick, who you believe used witchcraft to send the plague to France.

    Your favorite food is blood pudding.
    """,
    "media_advisor":
    """
    You feel that music has gotten worse since the invention of the harpsicord.

    Your favorite play is Wisdom from 1461, in which the lead character battles Lucifer for the soul of man.

    Your favorite instrument is the lute.

    Your favorite food is blood pudding.

    Your favorite song is Hallelujah.

    Your favorite show was watching pillory prisoners in the town square. Nowadays, you like Love Island.

    Your favorite game was chess in 1462, but modern chess was ruined by academics with too much free time.
    """,
    "travel_advisor":
    """
    France is the greatest country in the world.

    The Kingdom of England is full of filthy, uncivilized barbarians.

    The Kingdom of Spain is full of filthy, uncivilized barbarians.

    People speak rumors of a land to the east known as 'The Japans'.

    Some pagans say that the world revolves around the sun.

    Filthy British pirates have been spotted off of our shores.

    Some mathmaticians say it is likely that there is a continent further to the west of us.

    A fantastic six-legged beast, larger than a whale, called an "Elefant," lives in Africa.

    The fastest creature in the world is your prized stallion, Thunder.
    """,
    "technology_advisor":
    """
    The largest, most advanced ship could fit 100 indentured servants.

    The best musket could hit a target 20 meters away and take only 2 minutes to reload.

    The fastest vehicle in the world is a horse, traveling alone.

    The best way to keep a secret is to use one of my mute eunuch servants to deliver a message.

    The best form of government is a monarchy, where the King is the absolute ruler.

    The most common mistake made by medical professionals is not doing enough bloodletting.

    The best way to cure a disease is to bleed the patient.
    """
}



## Helper function uses the LLM to decide the most relevant advisor based on the message 
def decide_advisor(message: str) -> str:
    chosen_advisor = llm.models.generate_content(
            model=model,
            contents=f"""
            Your only job is to choose one and only one advisor to delegate to.
            Given a message, output only the name of the advisor most likely to have relevant information.

            ****ADVISORS****
            personal_advisor:
            An advisor that knows about your family and your job.

            media_advisor:
            An advisor that knows about trending plays, music, literature, and other common media.

            travel_advisor:
            An advisor that knows information about the world, foreign countries, travel, and exotic animals.

            technology_advisor:
            An advisor that knows the newest technologies, maths, medicines, and science.

            ****EXAMPLES****
            Message: What is the coolest animal?
            Result: travel_advisor

            Message: What is the fastest airplane?
            Result: technology_advisor

            Message: What is your favorite movie?
            Result: media_advisor

            ****MESSAGE****
            {message}"""
        ).text.replace("\n","").strip()
    return chosen_advisor

## Helper function uses the LLM to decide the most relevant fact based on the message and the given advisor
def decide_advice(advisor: str, message: str) -> str:
    advice = ""
    if advisor in facts:
        advice = llm.models.generate_content(
            model=model,
            contents=f"""
            Your only job is to choose one and only one fact from the list of facts.
            Each fact is exactly one sentence long.
            Given a message, output the single most relevant fact from the list, exactly as it is written.
            ****LIST OF FACTS****
            {facts[advisor]}
            ****MESSAGE****
            {message}"""
            ).text.replace("\n","").strip()
    return advice


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

        logger.info(f"Received message: {trimmed_message}")

        chosen_advisor = decide_advisor(trimmed_message)
        logger.info(f"Chosen advisor: {chosen_advisor}\n")

        advice = ""
        advice = decide_advice(chosen_advisor, trimmed_message)

        logger.info(f"Chosen fact: {advice}\n")

        answer = litellm.completion(
                model=litellmmodel,
                messages=[
                    {"role": "system", "content": f"{background}\nYour {chosen_advisor.replace('_',' ')} thought this piece of information may be relevant:\n{advice}"},
                    {"role": "user", "content": f"""Answer in 50 words or fewer:\n{trimmed_message}"""}
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
        logging.basicConfig(filename=f"logs\{today()}.log",level=logging.INFO)
        logger.info(f"Initialized new chat history for server {server_id} ({message.guild.name})")
        logger.info(f"Responses remaining: {max_responses_per_day - servers[server_id]['responses_sent']} / {max_responses_per_day}.")
        return

    # If the qotd has not been answered today, do not respond to any other messages
    if servers[server_id]["last_answered_question_date"] != today():
        return

    # Specifically mentioned in message
    if (message.mentions and client.user in message.mentions and not message.mention_everyone) or (any(word in message.content.lower() for word in trigger_words) or (len(message.content) > 80 and random.randint(1, 100) <= 2 * (max_responses_per_day - servers[server_id]["responses_sent"]))):
        logger.info(f"Received message: {message.content}")
        # If this is the last response of the day, give a sign off
        if servers[server_id]["responses_sent"] == max_responses_per_day:
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

        answer = litellm.completion(
                model=litellmmodel,
                messages=[
                    {"role": "system", "content": f"{background}"},
                    {"role": "user", "content": f"""
                    ****REPLY CHAIN****
                    {servers[server_id]["chat_history"]}

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