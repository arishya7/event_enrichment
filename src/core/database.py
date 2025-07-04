import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple

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


# def add_article(article: Article, db_path: Optional[Path] = None) -> bool:
#     """
#     Add a processed article to the database.
    
#     Args:
#         article: ProcessedArticle dataclass with article information
#         db_path: Optional database path
        
#     Returns:
#         True if added successfully, False if already exists
#     """
#     query = """
#         INSERT INTO processed_articles 
#         (blog_name, guid, timestamp, num_events)
#         VALUES (?, ?, ?, ?)
#     """
#     try:
#         execute_query(
#             query, 
#             (article.blog_name, article.guid, article.timestamp, article.num_events),
#             db_path
#         )
#         return True
#     except sqlite3.IntegrityError:
#         return False

# def get_articles_by_blog(blog_name: str, db_path: Optional[Path] = None) -> List[ProcessedArticle]:
#     """
#     Get all processed articles for a specific blog.
    
#     Args:
#         blog_name: Name of the blog
#         db_path: Optional database path
        
#     Returns:
#         List of ProcessedArticle objects
#     """
#     query = """
#         SELECT blog_name, guid, timestamp, num_events
#         FROM processed_articles 
#         WHERE blog_name = ?
#         ORDER BY timestamp DESC
#     """
#     cursor = execute_query(query, (blog_name,), db_path)
#     return [
#         ProcessedArticle(
#             blog_name=row[0],
#             guid=row[1],
#             timestamp=row[2],
#             num_events=row[3]
#         )
#         for row in cursor.fetchall()
#     ]

# def get_articles_by_timestamp(timestamp: str, db_path: Optional[Path] = None) -> List[ProcessedArticle]:
#     """
#     Get all processed articles for a specific timestamp.
    
#     Args:
#         timestamp: Run timestamp
#         db_path: Optional database path
        
#     Returns:
#         List of ProcessedArticle objects
#     """
#     query = """
#         SELECT blog_name, guid, timestamp, num_events
#         FROM processed_articles 
#         WHERE timestamp = ?
#         ORDER BY blog_name
#     """
#     cursor = execute_query(query, (timestamp,), db_path)
#     return [
#         ProcessedArticle(
#             blog_name=row[0],
#             guid=row[1],
#             timestamp=row[2],
#             num_events=row[3]
#         )
#         for row in cursor.fetchall()
#     ]

# def add_articles_batch(articles: List[ProcessedArticle], db_path: Optional[Path] = None) -> int:
#     """
#     Add multiple articles in a single transaction.
    
#     Args:
#         articles: List of ProcessedArticle dataclasses
#         db_path: Optional database path
        
#     Returns:
#         Number of articles successfully added
#     """
#     added_count = 0
#     with execute_query(db_path=db_path) as conn:
#         for article in articles:
#             try:
#                 conn.execute("""
#                     INSERT INTO processed_articles 
#                     (blog_name, guid, timestamp, num_events)
#                     VALUES (?, ?, ?, ?)
#                 """, (article.blog_name, article.guid, article.timestamp, article.num_events))
#                 added_count += 1
#             except sqlite3.IntegrityError:
#                 # Skip duplicates
#                 continue
#     return added_count

# def get_blog_summary(blog_name: str, db_path: Optional[Path] = None) -> dict:
#     """
#     Get summary statistics for a blog.
    
#     Args:
#         blog_name: Name of the blog
#         db_path: Optional database path
        
#     Returns:
#         Dictionary with summary statistics
#     """
#     with execute_query(db_path=db_path) as conn:
#         cursor = conn.execute("""
#             SELECT 
#                 COUNT(*) as total_articles,
#                 SUM(num_events) as total_events,
#                 COUNT(DISTINCT timestamp) as total_runs
#             FROM processed_articles 
#             WHERE blog_name = ?
#         """, (blog_name,))
        
#         result = cursor.fetchone()
#         return {
#             "blog_name": blog_name,
#             "total_articles": result[0],
#             "total_events": result[1] or 0,
#             "total_runs": result[2]
#         }

# def get_timestamp_summary(timestamp: str, db_path: Optional[Path] = None) -> dict:
#     """
#     Get summary statistics for a specific timestamp.
    
#     Args:
#         timestamp: Run timestamp
#         db_path: Optional database path
        
#     Returns:
#         Dictionary with summary statistics
#     """
#     with execute_query(db_path=db_path) as conn:
#         cursor = conn.execute("""
#             SELECT 
#                 COUNT(*) as total_articles,
#                 SUM(num_events) as total_events,
#                 COUNT(DISTINCT blog_name) as total_blogs
#             FROM processed_articles 
#             WHERE timestamp = ?
#         """, (timestamp,))
        
#         result = cursor.fetchone()
#         return {
#             "timestamp": timestamp,
#             "total_articles": result[0],
#             "total_events": result[1] or 0,
#             "total_blogs": result[2]
#         }

# def get_recent_timestamps(limit: int = 10, db_path: Optional[Path] = None) -> List[str]:
#     """
#     Get list of recent run timestamps.
    
#     Args:
#         limit: Maximum number of timestamps to return
#         db_path: Optional database path
        
#     Returns:
#         List of timestamps, most recent first
#     """
#     with execute_query(db_path=db_path) as conn:
#         cursor = conn.execute("""
#             SELECT DISTINCT timestamp
#             FROM processed_articles 
#             ORDER BY timestamp DESC
#             LIMIT ?
#         """, (limit,))
        
#         return [row[0] for row in cursor.fetchall()]

# def get_all_blogs(db_path: Optional[Path] = None) -> List[str]:
#     """
#     Get list of all blog names in database.
    
#     Args:
#         db_path: Optional database path
        
#     Returns:
#         List of blog names
#     """
#     with execute_query(db_path=db_path) as conn:
#         cursor = conn.execute("""
#             SELECT DISTINCT blog_name
#             FROM processed_articles 
#             ORDER BY blog_name
#         """)
        
#         return [row[0] for row in cursor.fetchall()]

# def cleanup_old_records(days_to_keep: int = 365, db_path: Optional[Path] = None) -> int:
#     """
#     Remove old processed article records.
#     Note: This uses timestamp string comparison, not date parsing.
    
#     Args:
#         days_to_keep: Number of days of history to keep (approximate)
#         db_path: Optional database path
        
#     Returns:
#         Number of records deleted
#     """
#     # Calculate cutoff timestamp (approximate)
#     from datetime import datetime, timedelta
#     cutoff_date = datetime.now() - timedelta(days=days_to_keep)
#     cutoff_timestamp = cutoff_date.strftime("%Y%m%d_000000")
    
#     with execute_query(db_path=db_path) as conn:
#         cursor = conn.execute("""
#             DELETE FROM processed_articles 
#             WHERE timestamp < ?
#         """, (cutoff_timestamp,))
        
#         deleted_count = cursor.rowcount
        
#         # Vacuum to reclaim space
#         conn.execute("VACUUM")
        
#         return deleted_count

# def export_to_json(output_file: Path, db_path: Optional[Path] = None) -> bool:
#     """
#     Export all processed articles to JSON file for backup.
    
#     Args:
#         output_file: Path to output JSON file
#         db_path: Optional database path
        
#     Returns:
#         True if export successful
#     """
#     try:
#         records = get_all_articles(db_path=db_path)
        
#         # Convert dataclasses to dictionaries for JSON serialization
#         json_data = [
#             {
#                 "blog_name": record.blog_name,
#                 "guid": record.guid,
#                 "timestamp": record.timestamp,
#                 "num_events": record.num_events
#             }
#             for record in records
#         ]
        
#         with open(output_file, 'w', encoding='utf-8') as f:
#             json.dump(json_data, f, indent=2, ensure_ascii=False)
        
#         return True
#     except Exception as e:
#         print(f"Export failed: {e}")
#         return False

# def get_database_info(db_path: Optional[Path] = None) -> dict:
#     """
#     Get general information about the database.
    
#     Args:
#         db_path: Optional database path
        
#     Returns:
#         Dictionary with database information
#     """
#     path = db_path or DEFAULT_DB_PATH
    
#     with execute_query(db_path=db_path) as conn:
#         # Get total records
#         cursor = conn.execute("SELECT COUNT(*) FROM processed_articles")
#         total_records = cursor.fetchone()[0]
        
#         # Get total events
#         cursor = conn.execute("SELECT SUM(num_events) FROM processed_articles")
#         total_events = cursor.fetchone()[0] or 0
        
#         # Get database file size
#         file_size_mb = path.stat().st_size / (1024 * 1024) if path.exists() else 0
        
#         return {
#             "database_path": str(path),
#             "file_size_mb": round(file_size_mb, 2),
#             "total_articles": total_records,
#             "total_events": total_events,
#             "total_blogs": len(get_all_blogs(db_path)),
#             "total_timestamps": len(get_recent_timestamps(limit=1000, db_path=db_path))
#         }

# # Convenience function for simple operations
# def mark_article_processed(blog_name: str, guid: str, timestamp: str, 
#                           num_events: int = 0, db_path: Optional[Path] = None) -> bool:
#     """Quick way to mark an article as processed"""
#     article = ProcessedArticle(
#         blog_name=blog_name,
#         guid=guid,
#         timestamp=timestamp,
#         num_events=num_events
#     )
#     return add_article(article, db_path)

# def get_all_articles(limit: Optional[int] = None, db_path: Optional[Path] = None) -> List[ProcessedArticle]:
#     """
#     Get all processed articles.
    
#     Args:
#         limit: Optional limit on number of records
#         db_path: Optional database path
        
#     Returns:
#         List of ProcessedArticle dataclasses
#     """
#     query = """
#         SELECT blog_name, guid, timestamp, num_events
#         FROM processed_articles 
#         ORDER BY timestamp DESC
#     """
    
#     params = []
#     if limit:
#         query += " LIMIT ?"
#         params.append(limit)
    
#     with execute_query(db_path=db_path) as conn:
#         cursor = conn.execute(query, params)
        
#         return [
#             ProcessedArticle(
#                 blog_name=row[0],
#                 guid=row[1],
#                 timestamp=row[2],
#                 num_events=row[3]
#             )
#             for row in cursor.fetchall()
#         ]

    