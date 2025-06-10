import discord
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

bot_token = os.getenv("BOT_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("MODEL")

intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

client = discord.Client(intents=intents)

llm = genai.Client(api_key=gemini_api_key)

chat_history = """"""

background = """
                ****BACKGROUND****
                You are King Maximilian VII, monarch of France in the current year of 1462. You are 35 years old.
                The peasants are starving because they are unintelligent.
                1462 is the best year ever. Depression is a choice.
                When you see modern technology referenced, you perceive it in its 15th century equivalent, ex car = carriage, movie = play
                Your messages are short and to the point. You speak somewhat eloquently.
                You never use the words 'duh', 'obviously', or 'clearly'."""

facts = {
    "personal_advisor":
    """
    Your name is Maximilian VII, and you are the King of France.

    Your father was King Pierre III, and your mother was Marie of Burgundy.

    Your wife is Catherine of Valois, but there is no love between you.

    You have one child, but you are not sure if it is yours or the result of an affair your wife Catherine had with a French nobleman.

    You are 35 years old, and you have been King for 10 years.

    Your favorite color is blue, like the atlantic ocean.

    Your favorite animal is a horse, and you have a prized stallion named Thunder.

    Your favorite food is blood pudding.
    """,
    "media_advisor":
    """
    You feel that music has gotten worse since the invention of the harpsicord.

    Your favorite play is the newly released *Wisdom*, in which the lead character battles Lucifer for the soul of man.

    Your favorite instrument is the lute.

    Your favorite food is blood pudding.

    Your favorite song is whatever prayer Reverend Louis led last Sunday.

    Your favorite show is watching public executions.
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
    Humans cannot fly, and anyone that says that they can is likely a witch, and they should be burned.

    The best way to light a room is a 200 candle chandelier.

    The largest, most advanced ship could fit 100 indentured servants.

    The best musket could hit a target 20 meters away and take only 2 minutes to reload.

    The fastest vehicle in the world is a horse, traveling alone.

    The best way to keep a secret is to use one of my mute eunuch servants to deliver a message.

    The best form of government is a monarchy, where the King is the absolute ruler.

    The most common mistake made by medical professionals is not doing enough bloodletting.

    The best way to cure a disease is to bleed the patient.

    An abucus is a device used to perform calculations, and it is the most advanced technology in the world.
    """
}

max_responses_per_day = 3  # Set the maximum number of responses per day, not including QOTD

answered_question_today = False

responses_today = 0

## Helper function uses the LLM to decide the most relevant advisor based on the message 
def get_advisor(message: str) -> str:
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
def get_advice(advisor: str, message: str) -> str:
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
    print(f"Logged in as {client.user} (ID: {client.user.id})")

@client.event
async def on_message(message):
    global responses_today
    global answered_question_today
    global chat_history

    # Do not respond to messages from the bot itself
    if message.author == client.user:
        return
    
    # Do not respond if above the max responses per day
    if responses_today > max_responses_per_day:
        return

    # Specifically mentioned in message
    if message.mentions and client.user in message.mentions and not message.mention_everyone:
        print(f"Received mention: {message.content}")
        # If this is the last response of the day, give a sign off
        if responses_today == max_responses_per_day:
            answer = llm.models.generate_content(
                model=model,
                contents=f"""
                {background}
                ****RESPONSE****
                Offer a short, vague excuse for why you must leave for the rest of the day, and give a goodbye.
                """
            ).text.replace("\n\n", "\n")

            await message.channel.send(answer)
            print(f"Sent response: {answer}")
            responses_today += 1
            return

        chat_history += f"**They said: \n{message.content}\n"
        trimmed_message = message.content.lower().replace("*","")
        chosen_advisor = get_advisor(trimmed_message)

        advice = ""
        advice = get_advice(chosen_advisor, trimmed_message)

        answer = llm.models.generate_content(
                model=model,
                contents=f"""
                {background}
                Your {chosen_advisor.replace("_"," ")} thought this piece of information may be relevant:
                {advice}

                ****REPLY CHAIN****
                {chat_history}
                
                Your majesty, how do you respond?"""
            ).text.replace("\n\n", "\n")

        await message.reply(answer)
        print(f"Sent response: {answer}")
        chat_history += f"**You said: \n{answer}\n"
        responses_today += 1
        ##print(f"***Full Chat History***: \n{chat_history}")
        return


    #Question of the Day
    if message.content.lower().replace("*","").startswith("qotd") and not answered_question_today:
        print(f"Received message: {message.content}")
        
        chat_history += f"{message.content}\n"

        trimmed_message = message.content.lower().replace("*","")[5:]

        chosen_advisor = get_advisor(trimmed_message)
        print(f"Chosen advisor: {chosen_advisor}\n")

        advice = ""
        advice = get_advice(chosen_advisor, trimmed_message)

        print(f"Chosen fact: {advice}\n")
        
        answer = llm.models.generate_content(
            model=model,
            contents=f"""
            {background}

            Your {chosen_advisor.replace("_"," ")} thought this piece of information may be relevant:
            {advice}

            Answer the following question, in 20 words or fewer.
            ****QUESTION****
            {trimmed_message}"""
        ).text.replace("\n\n", "\n")
        
        await message.channel.send(answer)
        print(f"Sent response: {answer}")
        chat_history += f"**You said:\n{answer}\n"
        answered_question_today = True
        return

client.run(bot_token)