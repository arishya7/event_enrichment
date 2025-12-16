import os

import mysql.connector as mysql
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

load_dotenv()
DB_PASSWORD = os.getenv("DB_PASSWORD")

DB_CONFIG = {
    "host": "192.168.50.166",
    "port": 3306,
    "user": "mmserver_db",
    "password": DB_PASSWORD,
    "database": "events_scraping",
    "charset": "utf8mb4",
}

MODEL_VERSION = "all-mpnet-base-v2"
FETCH_BATCH_SIZE = 128
ENCODE_BATCH_SIZE = 64


def stream_events(cursor):
    cursor.execute("SELECT id, title, blurb, description FROM events")
    while True:
        rows = cursor.fetchmany(FETCH_BATCH_SIZE)
        if not rows:
            break
        yield rows


def main():
    model = SentenceTransformer(MODEL_VERSION)
    conn = mysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM events")
    total = cursor.fetchone()[0]

    processed = 0
    for batch in stream_events(cursor):
        texts = [
            " ".join(filter(None, (title, blurb, description))).strip() or " "
            for (_, title, blurb, description) in batch
        ]
        embeddings = model.encode(
            texts, convert_to_numpy=True, batch_size=ENCODE_BATCH_SIZE
        ).astype(np.float32)

        for (event_id, _, _, _), emb in zip(batch, embeddings):
            cursor.execute(
                """
                INSERT INTO event_embeddings (id, embedding, embedding_model)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    embedding = VALUES(embedding),
                    embedding_model = VALUES(embedding_model)
                """,
                (event_id, emb.tobytes(), MODEL_VERSION),
            )

        conn.commit()
        processed += len(batch)
        tqdm.write(f"{processed}/{total} events embedded")

    cursor.close()
    conn.close()
    print(f"Embeddings backfilled for {processed} events using {MODEL_VERSION}.")


if __name__ == "__main__":
    main()
