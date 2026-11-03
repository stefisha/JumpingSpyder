import os
import json
import re
import time
import traceback
from datetime import datetime
from dotenv import load_dotenv
from fetcher import get_user_id, get_latest_tweets
from classifier import classify_tweet_with_context
from notifier import send_telegram_message
from memory import load_processed_ids, save_processed_id
import requests

load_dotenv()
TRACKED_USERS = os.getenv("TRACKED_USERS", "").split(",")

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def clean_tweet_text(text):
    return re.sub(r"https?://\S+", "", text).strip()

def escape_markdown(text):
    if not text:
        return ""
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
    return text

def main():
    log("🚀 Bot started.")
    processed_ids = load_processed_ids()

    for username in TRACKED_USERS:
        username = username.strip()
        if not username:
            continue

        try:
            log(f"🔍 Processing user: @{username}")
            try:
                user_id = get_user_id(username)
                tweets = get_latest_tweets(user_id, max_results=5)
            except requests.exceptions.HTTPError as err:
                if err.response.status_code == 429:
                    log(f"⏱️ Rate limit hit while fetching @{username}. Skipping...")
                    continue
                raise

            if not tweets:
                log(f"ℹ️ No tweets found for @{username}")
                continue

            latest_tweet = tweets[0]
            tweet_id = latest_tweet.get("id")
            text = latest_tweet.get("text", "")

            if not text.strip():
                log(f"📷 Tweet from @{username} contains no text, skipping media-only post.")
                continue

            if tweet_id in processed_ids:
                log(f"⏩ Already processed tweet ID {tweet_id}, skipping...")
                continue

            context_tweets = [clean_tweet_text(t.get("text", "")) for t in tweets if t.get("text")]
            context_block = "\n".join(f"- {t}" for t in context_tweets)

            latest_clean = clean_tweet_text(text)

            log(f"🧠 Classifying tweet from @{username}: {latest_clean}")
            result = classify_tweet_with_context(context_block, latest_clean)
            log(f"📦 Classification result: {result}")

            try:
                data = json.loads(result)
                signal = data.get("signal", "IGNORE")
                normal = data.get("normal", True)
                reason = data.get("reason", "")
                tweet_text = data.get("tweet", text)

                formatted_tweet = escape_markdown(clean_tweet_text(tweet_text))
                escaped_reason = escape_markdown(reason)
                escaped_username = escape_markdown(username)

                if signal == "IGNORE":
                    log(f"🛑 Signal is IGNORE, not sending message.")
                else:
                    msg = (
                        f"🚨 *Signal Detected!*\n\n"
                        f"*Author:* @{escaped_username}\n"
                        f"*Normal:* `{normal}`\n"
                        f"*Tweet:* {formatted_tweet}\n"
                        f"*Signal:* `{signal}`\n"
                        f"*Reason:* {escaped_reason}"
                    )
                    send_telegram_message(msg)
                    log(f"📨 Sent alert for tweet ID {tweet_id}")

                save_processed_id(tweet_id, username, text)
                log(f"✅ Tweet ID {tweet_id} saved to memory.")

            except Exception as parse_err:
                log(f"⚠️ Failed to parse or notify: {parse_err}")
                log(traceback.format_exc())

        except Exception as e:
            log(f"❌ Error processing @{username}: {e}")
            log(traceback.format_exc())

    log("🏁 Bot finished.")

if __name__ == "__main__":
    main()
