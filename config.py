import yaml
import os
from dotenv import load_dotenv

load_dotenv()

def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_env_vars() -> dict:
    """Get environment variables for sensitive data."""
    return {
        'bot_token': os.getenv("BOT_TOKEN"),
        'gemini_api_key': os.getenv("GEMINI_API_KEY")
    }