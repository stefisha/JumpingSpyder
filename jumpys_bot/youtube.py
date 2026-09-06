import os
import re
import json
import requests
import psycopg2
import logging
from datetime import datetime
from googleapiclient.discovery import build
from dotenv import load_dotenv
from langchain_community.document_loaders import YoutubeLoader
from langchain.prompts import PromptTemplate
from langchain_openai import OpenAI

# === LOAD ENV ===
load_dotenv()

# === CONFIG ===
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DATABASE_URL = os.getenv("DATABASE_URL")
CHANNELS = [c.strip() for c in os.getenv("TRACKED_CHANNELS", "").split(",") if c.strip()]

# === Logging ===
logging.basicConfig(
    filename="youtube.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# === Markdown Escape ===
def escape_markdown(text):
    special_chars = r"_*[]()~`>#+-=|{}.!"
    return ''.join(f'\\{c}' if c in special_chars else c for c in text)

# === Telegram Notify ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "MarkdownV2"
    }
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        logging.error(f"Failed to send Telegram message: {response.text}")

# === Initialize LLM ===
llm = OpenAI(temperature=0, api_key=OPENAI_API_KEY)

# === Prompt Template ===
combined_analysis_prompt = PromptTemplate(
    input_variables=["transcript"],
    template="""
You are a crypto investor reviewing a transcript from a YouTube video.

Your task is to:
1. Determine if this video upload appears *normal* or *irregular* for the channel (e.g., was the account hacked?).
2. Detect whether the video contains any trading signal (BUY, SELL, or IGNORE).
   - Only assign BUY or SELL if you are 90% confident it's an impactful signal.
   - Consider financial language, urgency, emotional cues, or mentions of assets.
   - If it's spammy, hype-driven, or scam-like, still identify the intended signal.

Respond in the following exact format:

{{
  "transcript_snippet": "{{short snippet from transcript}}",
  "normal": true|false,
  "signal": "BUY" | "SELL" | "IGNORE",
  "reason": "Brief, punchy explanation (1–2 sentences max). Focus on sentiment or signal logic. Assume I am a trader."
}}

Now analyze this transcript:

"{transcript}"
"""
)

classification_chain = combined_analysis_prompt | llm

# === Database Logic ===
def insert_video(video_id, title, published_at, normal, signal, reason):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO youtube_videos (video_id, title, published_at, normal, signal, reason)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (video_id) DO NOTHING;
    """, (video_id, title, published_at, normal, signal, reason))
    conn.commit()
    cur.close()
    conn.close()

def video_already_processed(video_id):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM youtube_videos WHERE video_id = %s LIMIT 1;", (video_id,))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists

# === Get Latest Video and Title ===
def get_latest_video_url_and_title(channel_name, api_key):
    youtube = build('youtube', 'v3', developerKey=api_key)

    search_response = youtube.search().list(
        part='snippet',
        q=channel_name,
        type='channel',
        maxResults=1
    ).execute()

    if not search_response.get('items'):
        raise Exception(f"Channel '{channel_name}' not found.")

    channel_id = search_response['items'][0]['snippet']['channelId']

    videos_response = youtube.search().list(
        part='snippet',
        channelId=channel_id,
        order='date',
        type='video',
        maxResults=1
    ).execute()

    if not videos_response.get('items'):
        raise Exception("No recent videos found.")

    video = videos_response['items'][0]
    video_id = video['id']['videoId']
    video_title = video['snippet']['title']
    published_at = video['snippet']['publishedAt']
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    return video_id, video_title, published_at, video_url

# === Classify Transcript ===
def classify_video_transcript(video_url):
    loader = YoutubeLoader.from_youtube_url(video_url, add_video_info=False)
    transcript_docs = loader.load()

    if not transcript_docs:
        raise Exception("Transcript not found or disabled.")

    transcript_text = transcript_docs[0].page_content[:3000]
    response = classification_chain.invoke({"transcript": transcript_text})

    try:
        data_block = re.search(r"\{(.|\n)*?\}", response).group(0)
        parsed = json.loads(data_block)
    except Exception as e:
        raise Exception(f"Failed to parse response: {response}\n{e}")

    return parsed["transcript_snippet"], parsed["normal"], parsed["signal"], parsed["reason"]

# === Main ===
def main():
    for channel in CHANNELS:
        logging.info(f"🔍 Checking latest video from '{channel}'...")
        try:
            video_id, video_title, published_at, video_url = get_latest_video_url_and_title(channel, YOUTUBE_API_KEY)
            logging.info(f"🎥 Found video: {video_url}")

            if video_already_processed(video_id):
                logging.info("⏩ Already processed video, skipping.")
                continue

            logging.info("📝 Analyzing transcript...")
            snippet, normal, signal, reason = classify_video_transcript(video_url)

            logging.info(f"✅ Classification Result: Signal={signal}, Normal={normal}")
            insert_video(video_id, video_title, published_at, normal, signal, reason)

            title = escape_markdown(video_title)
            reason_text = escape_markdown(reason)

            message = f"*New video from @{channel}*:\n*{title}*\n\n*Signal:* {signal}\n*Normal upload:* {normal}\n*Reason:* {reason_text}"
            send_telegram_message(message)

        except Exception as e:
            error_msg = f"❌ Error for channel '{channel}': {e}"
            logging.error(error_msg)
            send_telegram_message(escape_markdown(error_msg))

if __name__ == "__main__":
    main()
