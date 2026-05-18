from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal

PostType = Literal["tweet", "reply", "retweet", "quote", "unknown"]


@dataclass(slots=True)
class OriginalPost:
    author: str | None = None
    content: str | None = None
    post_id: str | None = None
    url: str | None = None


@dataclass(slots=True)
class PostRecord:
    post_id: str
    account_username: str
    account_display_name: str | None
    author_username: str
    display_name: str | None
    type: PostType
    title: str
    content_html: str
    content_text: str
    url: str
    source_url: str
    published_at: str
    published_date: str
    fetched_at: str
    guid: str | None = None
    original_post: OriginalPost | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        if self.original_post is None:
            data.pop("original_post", None)
        return data


@dataclass(slots=True)
class UserMeta:
    username: str
    source: str
    source_url: str
    rss_url: str
    display_name: str | None = None
    last_checked_at: str | None = None
    last_post_at: str | None = None
    last_post_id: str | None = None
    total_posts: int = 0
    total_days: int = 0
    date_range: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)



def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
