"""Validated contracts shared by offline and live adapters."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

LABELS = ("BULLISH", "BEARISH", "NEUTRAL", "UNCERTAIN")
RISKS = ("CLEAR", "FLAGGED", "UNKNOWN")


def bounded(value, name, maximum):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must be a nonempty string of at most {maximum} characters")
    return value


@dataclass(frozen=True)
class Post:
    source: str
    id: str
    author: str
    text: str
    url: str
    published_at: str

    def __post_init__(self):
        if self.source not in ("x", "youtube", "fixture"):
            raise ValueError("Unsupported source")
        for key, limit in (("id", 200), ("author", 200), ("text", 20000), ("url", 2000)):
            bounded(getattr(self, key), key, limit)
        parsed = urlparse(self.url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Source URL must be an absolute HTTPS URL without credentials")
        bounded(self.published_at, "published_at", 60)
        try:
            stamp = datetime.fromisoformat(self.published_at.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("published_at must be a valid ISO timestamp") from None
        if stamp.tzinfo is None:
            raise ValueError("published_at must include a timezone")
        object.__setattr__(
            self, "published_at", stamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        )

    @property
    def key(self):
        return f"{self.source}:{self.id}"

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Classification:
    label: str
    risk: str
    summary: str
    evidence: str

    @classmethod
    def validate(cls, value, post):
        if not isinstance(value, dict) or set(value) != {"label", "risk", "summary", "evidence"}:
            raise ValueError("Classification must contain exactly label, risk, summary, evidence")
        if value["label"] not in LABELS or value["risk"] not in RISKS:
            raise ValueError("Invalid classification enum")
        bounded(value["summary"], "summary", 600)
        bounded(value["evidence"], "evidence", 600)
        if value["evidence"] not in post.text:
            raise ValueError("Evidence must be an exact excerpt of the source text")
        return cls(**value)

    @property
    def alertable(self):
        return self.label in ("BULLISH", "BEARISH") and self.risk == "CLEAR"

    def to_dict(self):
        return asdict(self)
