"""Destinations are explicit; preview never contacts Telegram."""

import hashlib

from .http import ProviderError


class PreviewSink:
    destination = "local-review"

    def send(self, post, result):
        # The report is the preview destination. No external message is sent.
        return None


class TelegramSink:
    def __init__(self, http, token, chat_id):
        self.http, self.token, self.chat_id = http, token, chat_id
        # A preview or a different bot/chat must not consume this destination's pending work.
        identity = f"{token.split(':')[0]}:{chat_id}"
        self.destination = "telegram:" + hashlib.sha256(identity.encode()).hexdigest()[:24]

    def send(self, post, result):
        message = (
            f"JumpingSpyder | {result.label}\n"
            f"{post.source} / {post.author}\n\n"
            f"{result.summary}\n\nSource excerpt: {result.evidence}\n\n"
            f"{post.url}\nReference: {post.key}\n\n"
            "Source-content classification. Not a return prediction."
        )
        data = self.http.request(
            "POST",
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            body={
                "chat_id": self.chat_id,
                "text": message,
                "link_preview_options": {"is_disabled": True},
            },
        )
        if data.get("ok") is not True or not isinstance(
            data.get("result", {}).get("message_id"), int
        ):
            raise ProviderError("Telegram did not acknowledge the message")
