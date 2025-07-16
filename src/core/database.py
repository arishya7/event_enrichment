import sqlite3
from pathlib import Path
from typing import Tuple

from src.utils.config import config
from src.core import *

def execute_query(query: str, params: Tuple = ()) -> sqlite3.Cursor:
    """
    Execute a single database query.
    
    Args:
        query: SQL query to execute
        params: Query parameters
        db_path: Optional database path
        
    Returns:
        sqlite3.Cursor object with query results
    """
    path = Path(config.paths.guid_db)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(path) as conn:
        return conn.execute(query, params)

def init_db() -> None:
    """
    Initialize the database schema.
    
    Args:
        db_path: Optional database path
    """
    # Create database file if it doesn't exist
    path = Path(config.paths.guid_db)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()

    create_table_sql = """
        CREATE TABLE IF NOT EXISTS processed_articles (
            blog_name TEXT NOT NULL,
            post_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            num_events INTEGER DEFAULT 0,
            PRIMARY KEY (blog_name, post_id)
        )
    """
    execute_query(create_table_sql)
