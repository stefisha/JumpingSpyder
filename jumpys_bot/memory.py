import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def load_processed_ids():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT tweet_id FROM processed_tweets;")
            rows = cur.fetchall()
            return set(row[0] for row in rows)

def save_processed_id(tweet_id, username, tweet_text):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO processed_tweets (tweet_id, username, tweet_text)
                VALUES (%s, %s, %s)
                ON CONFLICT (tweet_id) DO NOTHING;
                """,
                (tweet_id, username, tweet_text)
            )
            conn.commit()
