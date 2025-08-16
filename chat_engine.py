import litellm
from database import choose_relevant_facts, update_fact
from server_manager import add_to_chat_history
from utils import today, old_times_today

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
                You are King Maximilian VII, absolute monarch of France on the day {past_date}. You live in the 15th century.
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

def generate_response(
    message: str, 
    config: dict,
    facts_collection,
    server_id: int = 0,
    additional_prompt: str = "", 
    username: str = "",
    server_state: dict = None,
    logger = None
) -> str:
    """
    Uses the LLM to generate a text response.
    If a server id is given, loads the chat history and appends it with the new user and assistance messages.
    If a server id is given, also queries a relevant fact from the database and appends it to the base prompt for this message only
    Args: 
        message: the user message for the bot to respond to
        config: configuration dictionary
        facts_collection: ChromaDB facts collection
        server_id: the id of the discord server for the bot to load its internal memory
        additional_prompt: any additional instuctions to append to the base prompt for this message only
        username: name of the user for the bot to respond to
        server_state: server state dictionary
    Returns:
        String/text for the bot to say 
    """
    relevant_facts = []
    referenced_fact_ids = []
    if server_id and facts_collection:
        relevant_facts = choose_relevant_facts(facts_collection, message, config['database']['relevance_threshold'])
        referenced_fact_ids = [fact_id for fact_id, _ in relevant_facts]
        
        if logger and relevant_facts:
            logger.info(f"Facts pulled into prompt ({len(relevant_facts)} facts):")
            for fact_id, fact_content in relevant_facts:
                logger.info(f"  ID {fact_id}: {fact_content}")
        elif logger:
            logger.info("No relevant facts found for this message")
    
    peasant_unrest = server_state['peasant_unrest_percentage'] if server_state else 0
    
    system_prompt = writer_instructions.format(peasant_unrest_percentage=peasant_unrest)    
    system_prompt += background.format(past_date=old_times_today(), present_date=today())

    if relevant_facts:
        facts_text = "\n".join([f"- {fact_content}" for _, fact_content in relevant_facts])
        system_prompt += f"\nYour advisor thought this information may be relevant:\n{facts_text}"

    system_prompt += f"\n{additional_prompt}"

    if server_id and server_state and server_state['active_summary']:
        system_prompt += f"\nSummary of the messages so far: {server_state['active_summary']}"

    message_context = [{"role": "system", "content": system_prompt}]
    
    if server_id and server_state:
        add_to_chat_history(server_id, "user", f"{username}: {message}")
        message_context.extend(server_state['chat_history'])
    
    # Note web search is enabled. LiteLLM web search works with Gemini, Grok, and a few others, but will incur additonal api costs.
    response = litellm.completion(
        model=config['llm']['model'],
        temperature=config['llm']['temperature'],
        messages=message_context,
        web_search_options={
            "search_context_size": config['llm']['web_search']['context_size']
        }
    )
    
    answer = response.choices[0].message.content.replace("\n\n", "\n").replace("*", "").replace('"', '')
    max_length = config['llm']['max_response_length']
    answer = (answer[:max_length] + "...") if len(answer) > max_length else answer

    if server_id and server_state:
        add_to_chat_history(server_id, "assistant", answer)
    
    # Extract and update facts if enabled and we have referenced facts
    if (server_id and facts_collection and referenced_fact_ids and 
        config.get('bot', {}).get('auto_learn_facts', False)):
        extract_and_update_facts(answer, relevant_facts, facts_collection, config, logger)
    
    return answer

def extract_and_update_facts(response: str, referenced_facts: list, facts_collection, config: dict, logger = None):
    """
    Analyzes the bot's response for new details and updates existing facts.
    Args:
        response: The bot's generated response
        referenced_facts: List of (id, content) tuples for facts used in generating the response
        facts_collection: ChromaDB collection instance
        config: Configuration dictionary
        logger: Logger instance for tracking updates
    """
    if not referenced_facts:
        return
    
    # Create prompt for fact extraction
    fact_extraction_prompt = f"""
Analyze the following response from King Maximilian VII and determine if any of the referenced facts should be updated with new information.

Referenced facts:
{chr(10).join([f"ID {fact_id}: {content}" for fact_id, content in referenced_facts])}

King's response:
"{response}"

For each referenced fact that should be updated with new information from the response, provide:
- The fact ID
- The updated fact content (incorporating the new details while preserving the original structure). Content should include a brief description as well as the King's feelings on it.

Fact content should be no more than 200 characters long.
Only suggest updates if the response contains genuinely new information that would enhance the fact. 
Do not update facts just for minor rewording or stylistic changes.
If no updates are needed, respond with "NO_UPDATES".

Format your response as:
ID: [fact_id]
UPDATED_FACT: [new content]

ID: [fact_id]  
UPDATED_FACT: [new content]
"""
    
    try:
        if logger:
            logger.info(f"Analyzing response for fact updates using {len(referenced_facts)} referenced facts")
            
        extraction_response = litellm.completion(
            model=config['llm']['model'],
            temperature=0.1,  # Low temperature for more consistent fact extraction
            messages=[{"role": "user", "content": fact_extraction_prompt}]
        )
        
        extraction_text = extraction_response.choices[0].message.content.strip()
        
        if extraction_text != "NO_UPDATES":
            if logger:
                logger.info("LLM identified potential fact updates")
                
            # Parse the response and update facts
            lines = extraction_text.split('\n')
            current_id = None
            current_fact = None
            updates_made = 0
            
            for line in lines:
                line = line.strip()
                if line.startswith('ID:'):
                    if current_id and current_fact:
                        # Update the previous fact
                        update_fact(facts_collection, current_id, current_fact, logger)
                        updates_made += 1
                    current_id = line.replace('ID:', '').strip()
                    current_fact = None
                elif line.startswith('UPDATED_FACT:'):
                    current_fact = line.replace('UPDATED_FACT:', '').strip()
            
            # Update the last fact if exists
            if current_id and current_fact:
                update_fact(facts_collection, current_id, current_fact, logger)
                updates_made += 1
            
            if logger:
                logger.info(f"Completed fact updates: {updates_made} facts updated")
        else:
            if logger:
                logger.info("No fact updates needed based on response analysis")
                
    except Exception as e:
        if logger:
            logger.error(f"Error during fact extraction: {str(e)}")
        # Silently fail to avoid disrupting the main conversation flow
        pass