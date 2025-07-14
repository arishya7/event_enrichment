#!/usr/bin/env python3
"""
Script to verify and display contents of guid.db database.
"""

import sqlite3
from pathlib import Path
from src.core.database import execute_query
from src.utils.config import config


def verify_database():
    """Display statistics and sample data from guid.db."""
    
    try:
        # Check if database file exists
        db_path = Path(config.paths.guid_db)
        if not db_path.exists():
            print(f"Database file not found at: {db_path}")
            return
        
        print(f"Database location: {db_path}")
        print(f"Database size: {db_path.stat().st_size / 1024:.2f} KB\n")
        
        # Get total count of records
        count_result = execute_query("SELECT COUNT(*) FROM processed_articles").fetchone()
        total_records = count_result[0] if count_result else 0
        print(f"Total articles in database: {total_records}")
        
        if total_records == 0:
            print("No records found in database.")
            return
        
        # Get count by blog
        blog_stats = execute_query("""
            SELECT blog_name, COUNT(*) as article_count, SUM(num_events) as total_events
            FROM processed_articles 
            GROUP BY blog_name 
            ORDER BY article_count DESC
        """).fetchall()
        
        print("\n=== Statistics by Blog ===")
        print(f"{'Blog Name':<20} {'Articles':<10} {'Total Events':<12}")
        print("-" * 45)
        for blog_name, article_count, total_events in blog_stats:
            print(f"{blog_name:<20} {article_count:<10} {total_events or 0:<12}")
        
        # Get total events
        total_events_result = execute_query("SELECT SUM(num_events) FROM processed_articles").fetchone()
        total_events = total_events_result[0] if total_events_result and total_events_result[0] else 0
        print(f"\nTotal events across all articles: {total_events}")
        
        # Show sample records
        print("\n=== Sample Records ===")
        sample_records = execute_query("""
            SELECT blog_name, post_id, timestamp, num_events 
            FROM processed_articles 
            ORDER BY num_events DESC 
            LIMIT 10
        """).fetchall()
        
        print(f"{'Blog':<15} {'Post ID':<10} {'Events':<8} {'Timestamp':<25}")
        print("-" * 70)
        for blog_name, post_id, timestamp, num_events in sample_records:
            # Truncate timestamp for display
            display_timestamp = timestamp[:19] if timestamp else "N/A"
            print(f"{blog_name:<15} {post_id:<10} {num_events:<8} {display_timestamp:<25}")
        
        # Show records with most events
        print("\n=== Articles with Most Events ===")
        top_articles = execute_query("""
            SELECT blog_name, post_id, num_events 
            FROM processed_articles 
            ORDER BY num_events DESC 
            LIMIT 5
        """).fetchall()
        
        for blog_name, post_id, num_events in top_articles:
            print(f"{blog_name} (post {post_id}): {num_events} events")
        
    except Exception as e:
        print(f"Error verifying database: {e}")


if __name__ == "__main__":
    verify_database() 