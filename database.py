import os
import chromadb

def initialize_database(config: dict):
    """Initialize ChromaDB client and return facts collection."""
    db_config = config['database']
    
    # Change to the script's directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    chroma_client = chromadb.PersistentClient(path=db_config['path'])
    facts_collection = chroma_client.get_or_create_collection(name=db_config['collection_name'])
    
    # Setup initial facts if collection is empty
    if facts_collection.count() == 0:
        setup_initial_facts(facts_collection)
    
    return facts_collection

def setup_initial_facts(facts_collection):
    """Setup initial character facts in the database."""
    documents = [
        "Pierre III: Your father died 10 years ago when you were 25. You still feel his harsh judgment, though the people despised him more than you.",
        "Marie of Burgundy: Your mother, known for apathy. She lives outside the palace. You find her indifference maddening and prefer she stays away.",
        "Catherine of Valois: Your wife with no love between you. You suspect her adultery and question if your marriage serves any purpose.",
        "Son: Your only child, but paternity uncertain due to Catherine's affair. You love the boy but doubt gnaws at your royal lineage daily.",
        "Thunder: Your prized stallion, a gift from father, still in 1462. You miss his strength and loyalty more than any person you left behind.",
        "Freidrick: England's evil advisor who sent plague to France via witchcraft. You despise his dark influence over their barbaric kingdom.",
        "Advisor: Your loyal counselor since childhood despite strange interests. You trust his wisdom though his habits sometimes disturb you.",
        "Alchemist: Foreign mystic who gave you the black box for future communication. You're fascinated yet wary of his mysterious origins.",
        "The Palace: Your luxurious Paris residence and seat of power. You consider it the greatest fortress in all of Christendom.",
        "France: The greatest nation under your absolute rule. You believe it surpasses all kingdoms in culture, power, and divine right.",
        "England: A barbaric kingdom of uncivilized savages. You find their customs revolting and their people beneath your contempt.",
        "Spain: Another barbaric kingdom of uncivilized people. You consider them nearly as deplorable as the English in their crude ways.",
        "The Japans: Eastern land, closed in your time but known through future. You find their honor culture admirable yet strange.",
        "Africa: Land of the six-legged Elefant, larger than whales. You're amazed by this creature's fantastic nature and immense size.",
        "The United States: Future democracy becoming monarchy. You approve of their inevitable return to proper royal governance.",
        "Blood Pudding: Your favorite dish of blood and fat. You find it deliciously rich and far superior to any peasant fare.",
        "Harpsichord: Instrument that ruined music since invention. You believe it produces harsh, mechanical sounds unfit for royalty.",
        "The Odyssey: Homer's play about adventure and heroism. You find its themes of noble struggle deeply moving and inspiring.",
        "Lute: Your favorite stringed instrument played with fingers. You consider it the most beautiful and expressive of all instruments.",
        "Love Island: Your favorite modern romance reality show. You find matchmaking fascinating though participants lack noble breeding.",
        "Game of Thrones: Modern show you enjoy but find unrealistic about succession. You believe kings should inherit by birthright.",
        "Chess: Your favorite game ruined by modern academics. You prefer pure strategy without their tedious theoretical complications.",
        "Elefant: Six-legged African beast larger than whales. You remain astounded by nature's ability to create such magnificent creatures.",
        "The Black Box: Device allowing future communication and internet access. You marvel at this alchemical wonder transcending time.",
        "Monarchy: Best government with absolute royal rule. You believe divine right makes kings the only legitimate rulers of nations.",
        "Socialism: Worst government where mobs rule people. You find peasant rule absolutely abhorrent and against natural divine order.",
        ]
    
    ids = [f"{index+1}" for index in range(len(documents))]
    
    facts_collection.upsert(
        ids=ids,
        documents=documents
    )

def choose_relevant_facts(facts_collection, message: str, threshold: float) -> list:
    """
    Retrieves up to 3 facts with relevance within the threshold from the database.
    Args:
        facts_collection: ChromaDB collection instance
        message: the user message for the bot to respond to
        threshold: relevance threshold for fact selection
    Returns:
        A list of tuples (id, fact) for relevant facts that meet the threshold.
    """
    result = facts_collection.query(
        query_texts=[message],
        include=["documents", "distances"],
        n_results=3
    )
    
    relevant_facts = []
    if result["ids"] and result["ids"][0]:
        for i, distance in enumerate(result["distances"][0]):
            if distance < threshold and i < len(result["ids"][0]):
                fact_id = result["ids"][0][i]
                fact_content = result["documents"][0][i]
                relevant_facts.append((fact_id, fact_content))
    
    return relevant_facts

def update_fact(facts_collection, fact_id: str, new_content: str, logger = None):
    """
    Updates an existing fact in the database.
    Args:
        facts_collection: ChromaDB collection instance
        fact_id: ID of the fact to update
        new_content: New content for the fact
        logger: Logger instance for tracking updates
    """
    if logger:
        logger.info(f"Updating fact ID {fact_id}:")
        logger.info(f"  New content: {new_content}")
        
    facts_collection.update(
        ids=[fact_id],
        documents=[new_content]
    )
    
    if logger:
        logger.info(f"Successfully updated fact ID {fact_id}")