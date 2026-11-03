import requests
import os
from dotenv import load_dotenv

load_dotenv()

BEARER_TOKEN = os.getenv("BEARER_TOKEN")
TRACKED_USERS = os.getenv("TRACKED_USERS", "").split(",")

def get_user_id(username):
    url = f"https://api.twitter.com/2/users/by/username/{username.strip()}"
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 429:
        raise Exception("Rate limit hit")

    try:
        return response.json()['data']['id']
    except KeyError:
        raise Exception(f"User not found or malformed response: {response.text}")


#def get_user_id(username):
#    url = f"https://api.twitter.com/2/users/by/username/{username.strip()}"
#    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
#    response = requests.get(url, headers=headers)
#    response.raise_for_status()
#    return response.json()['data']['id']

def get_latest_tweets(user_id, max_results=5):
    url = f"https://api.twitter.com/2/users/{user_id}/tweets"
    params = {
        "max_results": max_results,
        "tweet.fields": "created_at",
        "exclude": "retweets,replies"
    }
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json().get('data', [])

if __name__ == "__main__":
    for username in TRACKED_USERS:
        if username.strip():
            try:
                user_id = get_user_id(username)
                tweets = get_latest_tweets(user_id)
                print(f"\nLatest original tweets from @{username}:")
                for tweet in tweets:
                    created_at = tweet.get('created_at', 'unknown time')
                    text = tweet.get('text', '[no text]')
                    print(f"- [{created_at}] {text}")
            except Exception as e:
                print(f"Error fetching tweets for {username}: {e}")
