"""Paginated recent-window collection with canonical account identifiers."""

import json
import re
from datetime import datetime
from urllib.parse import urlencode

from .domain import Post
from .http import ProviderError


class FixtureSource:
    def __init__(self, path):
        self.path = path

    def fetch(self):
        with open(self.path, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list) or len(data) > 10000:
            raise ValueError("Fixture must be a list of at most 10000 posts")
        fields = {"source", "id", "author", "text", "url", "published_at"}
        if any(not isinstance(row, dict) or set(row) != fields for row in data):
            raise ValueError(
                "Each fixture post must contain exactly the six documented source fields"
            )
        return [Post(**row) for row in data]


class XSource:
    def __init__(self, http, bearer, username, pages=3, since=None):
        if not re.fullmatch(r"[A-Za-z0-9_]{1,15}", username):
            raise ValueError("Invalid X username")
        self.http, self.bearer, self.username, self.pages = http, bearer, username.lower(), pages
        self.since = since

    def fetch(self):
        headers = {"Authorization": f"Bearer {self.bearer}"}
        user = self.http.request(
            "GET", f"https://api.x.com/2/users/by/username/{self.username}", headers=headers
        )
        user_id = user["data"]["id"]
        if not isinstance(user_id, str) or not user_id.isdigit():
            raise ValueError("Invalid X user ID")
        posts, token = [], None
        for _ in range(self.pages):
            params = {
                "max_results": 100,
                "exclude": "retweets,replies",
                "tweet.fields": "created_at",
            }
            if self.since:
                params["start_time"] = self.since
            if token:
                params["pagination_token"] = token
            data = self.http.request(
                "GET",
                f"https://api.x.com/2/users/{user_id}/tweets?{urlencode(params)}",
                headers=headers,
            )
            if data.get("errors"):
                raise ProviderError("X returned partial timeline errors")
            for item in data.get("data", []):
                posts.append(
                    Post(
                        "x",
                        item["id"],
                        self.username,
                        item["text"],
                        f"https://x.com/{self.username}/status/{item['id']}",
                        item["created_at"],
                    )
                )
            token = data.get("meta", {}).get("next_token")
            if not token:
                return posts
        if token:
            raise ProviderError("X page limit reached; increase --pages to collect the full window")
        return posts


class YouTubeSource:
    """Classify title/description metadata. No claim of transcript or full-video analysis."""

    def __init__(self, http, api_key, channel_id, pages=3, since=None):
        if not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", channel_id):
            raise ValueError("YouTube requires a canonical UC channel ID")
        self.http, self.api_key, self.channel_id, self.pages = http, api_key, channel_id, pages
        self.since = datetime.fromisoformat(since.replace("Z", "+00:00")) if since else None

    def get(self, resource, **params):
        params["key"] = self.api_key
        return self.http.request(
            "GET", f"https://www.googleapis.com/youtube/v3/{resource}?{urlencode(params)}"
        )

    def fetch(self):
        channel = self.get("channels", part="contentDetails", id=self.channel_id)
        items = channel.get("items", [])
        if not items:
            raise ProviderError("YouTube channel unavailable")
        uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        posts, token = [], None
        for _ in range(self.pages):
            params = {"part": "snippet,contentDetails", "playlistId": uploads, "maxResults": 50}
            if token:
                params["pageToken"] = token
            data = self.get("playlistItems", **params)
            for item in data.get("items", []):
                snippet = item["snippet"]
                if snippet.get("title") in ("Private video", "Deleted video"):
                    continue
                details = item["contentDetails"]
                published = details.get("videoPublishedAt", snippet["publishedAt"])
                if (
                    self.since
                    and datetime.fromisoformat(published.replace("Z", "+00:00")) < self.since
                ):
                    return posts
                text = snippet["title"] + "\n" + snippet.get("description", "")
                posts.append(
                    Post(
                        "youtube",
                        details["videoId"],
                        self.channel_id,
                        text,
                        f"https://www.youtube.com/watch?v={details['videoId']}",
                        details.get("videoPublishedAt", snippet["publishedAt"]),
                    )
                )
            token = data.get("nextPageToken")
            if not token:
                return posts
        if token:
            raise ProviderError(
                "YouTube page limit reached; increase --pages to collect the full window"
            )
        return posts
