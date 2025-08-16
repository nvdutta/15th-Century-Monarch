# Lost 15th Century Monarch
<img src="/example-chat.jpg" height="120px">

<img src="https://upload.wikimedia.org/wikipedia/commons/2/29/Ranc_Jean_Louis_XIV_Fabre_museum.jpg" align="right" height="180px" />

This is King Maximilian VII.

A fictitious 15th century monarch that answers ice breaker questions.

Built to run as a discord bot and respond to "qotd" messages as well as direct mentions.

Uses discord.py for Discord API, sends prompts to Google Gemini 2.5 Flash.

## How It Works

Lost 15th Century Monarch, or Monarch Bot, uses a simple yet effective fact-retrieval system powered by ChromaDB vector search.

The bot maintains character consistency by storing 40+ character facts in a vector database. When responding to messages, it performs semantic search to find up to 3 relevant facts and incorporates them into the response generation. The bot also learns and updates its facts based on new information revealed in conversations.

Monarch Bot responds to two different types of messages in channels named "qotd":

- *Question of the Day*: Messages containing "QOTD:" or "question of the day:" (case insensitive)
  - Resets daily chat history and increments peasant unrest
  - Limited to 50 words per response
- *Direct Mentions*: Messages that mention the bot directly
  - Only responds after QOTD has been answered for the day
  - Limited to 3 additional responses per server per day

The bot implements an advanced retrieval-augmented generation (RAG) pattern with learning capabilities:

1. **Message Received**: Bot checks if it's in a "qotd" channel and meets response criteria
2. **Fact Retrieval**: ChromaDB performs semantic search across character facts, returning up to 3 relevant facts
3. **Context Building**: Relevant facts (similarity distance < 1.60) are added to the system prompt
4. **Response Generation**: Google Gemini generates a response as King Maximilian VII using facts, character background, and chat history
5. **Fact Learning**: Bot analyzes its own response for new character details and updates existing facts automatically

Now introducing: **Peasant Unrest Percentage**: A narrative element that increases daily, affecting the tone and urgency of responses.
An experiment into storing character states to keep a consistent narrative without bloating the context sent to the LLM.
> Note: In the current implementation, the Monarch Bot has a set lifespan of 100 question-of-the-day uses per server.

The character facts cover:

```
Your father was King Pierre III, and your mother was Marie of Burgundy.
Your favorite food is blood pudding.
The best form of government is a monarchy, where the King is the absolute ruler.
The most common mistake made by medical professionals is not doing enough bloodletting.
...
```

Message → Semantic Search → Relevant Facts → LLM Response → Fact Learning → Discord Message

```mermaid
graph TD
    A[Receive Discord Message] --> B{Channel = 'qotd'?}
    B -->|No| Z[Ignore Message]
    B -->|Yes| C{QOTD or Mention?}
    
    C -->|QOTD| D[Reset Chat History]
    C -->|Mention| E{QOTD Answered Today?}
    
    E -->|No| Z
    E -->|Yes| F{Under Daily Limit?}
    F -->|No| Z
    F -->|Yes| G[ChromaDB Semantic Search]
    
    D --> H[Increment Peasant Unrest]
    H --> G
    
    G --> I{Relevant Facts Found?}
    I -->|Yes distance < 1.60| J[Add Facts to System Prompt]
    I -->|No| K[Use Base System Prompt]
    
    J --> L[Google Gemini 2.5 Flash]
    K --> L
    
    L --> M[Generate King Maximilian VII Response]
    M --> N[Analyze Response for New Facts]
    N --> O[Update Existing Facts if Needed]
    O --> P[Post-process Response]
    P --> Q[Send Discord Message]
    Q --> R[Update Chat History]
    
    subgraph ChromaDB[ChromaDB Vector Database]
        S[40+ Character Facts]
    end
    
    subgraph Memory[Server Memory]
        T[Chat History]
        U[Response Count]
        V[Peasant Unrest %]
        W[Last QOTD Date]
    end
    
    G -.-> S
    O -.-> S
    Q -.-> T
    Q -.-> U
    H -.-> V
    D -.-> W
    
    style L fill:#fff3e0,color:#000000
    style S fill:#e8f5e8,color:#000000
    style Memory fill:#bae1ff, color:#000000
```

## How to Use this Repository

You can run this bot yourself by cloning this repo:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file with:
   ```
   BOT_TOKEN=your_discord_bot_token
   GEMINI_API_KEY=your_gemini_api_key
   ```
   Get tokens from [Discord Developer Portal](https://discord.com/developers/applications) and [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key).

3. Initialize the facts database:
   ```bash
   python -c "from database import initialize_database; from config import load_config; initialize_database(load_config())"
   ```

4. Run the bot:
   ```bash
   python main.py
   ```

> Note: The Gemini free tier may have rate limits. A paid account provides more reliable service for active servers.

## Key Features

- **Channel Restriction**: Only responds in channels named "qotd"
- **Daily Limits**: 1 QOTD response + 3 mentions per server per day
- **Peasant Unrest**: Narrative element that increases daily, affecting response tone
- **Fact Learning**: Automatically updates character facts based on new information in conversations
- **Multi-Fact Retrieval**: Uses up to 3 relevant facts per response for richer context
- **Web Search**: Enabled in LLM calls for current events (increases API costs)
- **Comprehensive Logging**: Tracks fact retrieval, updates, and all bot interactions
- **Character Consistency**: Vector search ensures relevant facts inform responses

## Advanced Features

- **Auto-Learning System**: Configurable fact learning that evolves the character's knowledge
- **Fact Tracking**: Each fact has a unique ID for precise updates and logging
- **Smart Fact Updates**: Only updates facts with genuinely new information, not stylistic changes
- **Error Resilience**: Fact learning fails silently to avoid disrupting conversations

This codebase provides a sophisticated foundation for character-based Discord bots using advanced RAG (Retrieval-Augmented Generation) with learning capabilities. The fact database and character prompts can be easily modified for different personas.




