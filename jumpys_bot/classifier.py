import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = (
    "You are an expert crypto analyst. Detect valuable trading signals from tweets. "
    "You are cautious and only provide BUY or SELL signals when you are at least 90% certain. "
    "If you're not confident, default to IGNORE. "
    "Also evaluate if the tweet seems normal (usual for this account) or abnormal (suspicious, off-brand, possibly compromised)."
)

def classify_tweet_with_context(context_block, latest_tweet_text):
    prompt = f'''Here are the user's latest tweets:

{context_block}

Focus on analyzing the *most recent* tweet only:

"{latest_tweet_text}"

Respond in the format:

{{
  "tweet": "{latest_tweet_text}",
  "normal": true|false,
  "signal": "BUY" | "SELL" | "IGNORE",
  "reason": "Brief, punchy explanation (1–2 sentences max). Focus on sentiment or signal logic. Assume I am a trader."
}}'''

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content
