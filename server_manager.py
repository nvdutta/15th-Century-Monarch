from utils import today

# Dictionary to store server-specific details
servers = {}

def get_server_state(server_id: int, server_name: str) -> dict:
    """Get or initialize server state."""
    global servers
    
    if server_id not in servers:
        servers[server_id] = {
            "last_answered_question_date": "",
            "responses_sent": 0,
            "chat_history": [],
            "peasant_unrest_percentage": 0,
            "active_summary": "",
        }
    
    return servers[server_id]

def update_server_state(server_id: int, **kwargs) -> None:
    """Update server state with provided key-value pairs."""
    global servers
    
    if server_id in servers:
        for key, value in kwargs.items():
            if key in servers[server_id]:
                servers[server_id][key] = value

def reset_daily_chat(server_id: int) -> None:
    """Reset chat history and increment peasant unrest for new QOTD."""
    global servers
    
    if server_id in servers:
        servers[server_id]['chat_history'] = []
        servers[server_id]['peasant_unrest_percentage'] += 1
        servers[server_id]["last_answered_question_date"] = today()

def add_to_chat_history(server_id: int, role: str, content: str) -> None:
    """Add a message to the server's chat history."""
    global servers
    
    if server_id in servers:
        servers[server_id]['chat_history'].append({"role": role, "content": content})

def can_respond(server_id: int, max_responses: int) -> bool:
    """Check if bot can respond based on daily limits."""
    global servers
    
    if server_id not in servers:
        return True
    
    # Check if peasant unrest is too high (king is dead)
    if servers[server_id]['peasant_unrest_percentage'] >= 101:
        return False
    
    # Check daily response limit
    return servers[server_id]["responses_sent"] <= max_responses

def increment_responses(server_id: int) -> None:
    """Increment the response counter for a server."""
    global servers
    
    if server_id in servers:
        servers[server_id]["responses_sent"] += 1

def is_qotd_answered_today(server_id: int) -> bool:
    """Check if QOTD has been answered today."""
    global servers
    
    if server_id not in servers:
        return False
    
    return servers[server_id]["last_answered_question_date"] == today()