import sqlite3
from pathlib import Path
from typing import Tuple, Any, Union

from src.utils.config import config
from src.core import *

def execute_query(query: str, params: Union[Tuple[Any, ...], Tuple] = ()) -> sqlite3.Cursor:
    """Execute a single database query.
    
    Executes SQL queries against the SQLite database, automatically handling
    connection management and directory creation.
    
    Args:
        query (str): SQL query to execute
        params (Union[Tuple[Any, ...], Tuple]): Query parameters as a tuple
        
    Returns:
        sqlite3.Cursor: Cursor object with query results
        
    Raises:
        sqlite3.Error: If there's an error executing the query
    """
    path = Path(config.paths.guid_db)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(path) as conn:
        return conn.execute(query, params)

def init_db() -> None:
    """Initialize the database schema.
    
    Creates the database file if it doesn't exist and sets up the
    processed_articles table with the required schema. This table tracks
    which articles have been processed to avoid duplicate processing.
    
    The table schema includes:
    - blog_name: Name of the blog source
    - post_id: Unique post identifier
    - timestamp: When the article was processed
    - num_events: Number of events extracted from the article
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
