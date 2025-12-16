import numpy as np
import mysql.connector as mysql
from dotenv import load_dotenv
import os
from sentence_transformers import SentenceTransformer

load_dotenv()
DB_CONFIG = {
    "host": "192.168.50.166",
    "port": 3306,
    "user": "mmserver_db",
    "password": os.getenv("DB_PASSWORD"),
    "database": "events_scraping",
    "charset": "utf8mb4",
}

EMBEDDING_MODEL = "all-mpnet-base-v2"
_embedding_model = SentenceTransformer(EMBEDDING_MODEL)


def upsert_event_embedding(cursor, event_id: int, title: str, blurb: str, description: str) -> None:
    """Embed a single event once and store it."""
    text = " ".join(filter(None, (title, blurb, description))).strip() or " "
    vector = _embedding_model.encode([text], convert_to_numpy=True).astype(np.float32)[0]
    cursor.execute(
        """
        INSERT INTO event_embeddings (id, embedding, embedding_model)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            embedding = VALUES(embedding),
            embedding_model = VALUES(embedding_model)
        """,
        (event_id, vector.tobytes(), EMBEDDING_MODEL),
    )


def main():
    conn = mysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT e.id, e.title, e.blurb, e.description
        FROM events e
        LEFT JOIN event_embeddings emb ON emb.id = e.id
        WHERE emb.id IS NULL
        """
    )
    rows = cursor.fetchall()
    print(f"Found {len(rows)} events missing embeddings")
    for event_id, title, blurb, description in rows:
        upsert_event_embedding(cursor, event_id, title, blurb, description)
    conn.commit()
    cursor.close()
    conn.close()
    print("Embeddings updated successfully")


if __name__ == "__main__":
    main()


#to run this file:
#python Scripts/update_embeddings.py


