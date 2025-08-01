import json
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Any
from dotenv import load_dotenv
import os

load_dotenv()

def dict_to_namespace(d: Dict[str, Any]) -> SimpleNamespace:
    """Convert a dictionary to a SimpleNamespace recursively
        E.g. config.paths.guid_db instead of config["paths"]["guid_db"]"""
    for key, value in d.items():
        if isinstance(value, dict):
            d[key] = dict_to_namespace(value)
    return SimpleNamespace(**d)

def load_json_file(file_path: Path) -> Dict:
    """Load a JSON file and return its contents"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found at {file_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in configuration file at {file_path}")

def load_text_file(file_path: Path) -> str:
    """Load a text file and return its contents"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Text file not found at {file_path}")

# Config directory path
CONFIG_DIR = Path(__file__).parent.parent.parent / 'config'

# Load main configuration
config = dict_to_namespace(load_json_file(CONFIG_DIR / 'config.json'))

# Load event schema - keep as dictionary for Gemini API compatibility
config.event_schema = load_json_file(CONFIG_DIR / 'event_schema.json')

# Load system instructions
config.system_instructions = SimpleNamespace(
    with_schema=load_text_file(CONFIG_DIR / 'system_instruction_w_schema.txt'),
    with_internet=load_text_file(CONFIG_DIR / 'system_instruction_w_internet.txt')
)
# Load API key
config.google_api_key = os.getenv("GOOGLE_API_KEY")
if not config.google_api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not found")

config.cx = os.getenv("cx")
if not config.cx:
    raise ValueError("cx environment variable not found")

config.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
if not config.aws_access_key_id:
    raise ValueError("AWS_ACCESS_KEY_ID environment variable not found")

config.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
if not config.aws_secret_access_key:
    raise ValueError("AWS_SECRET_ACCESS_KEY environment variable not found")

