from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal

PostKind = Literal["tweet", "reply", "quote", "unknown"]
AccountPostRelationship = Literal["authored", "reposted"]
SyncStatus = Literal["success", "failed"]


def normalize_username(value: str) -> str:
    return value.strip().lstrip("@").lower()


def utc_now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def ts_to_iso(value: int | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ReferencedPost:
    author_username: str | None = None
    content_text: str | None = None
    post_id: str | None = None
    url: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Post:
    post_id: str
    author_username: str
    kind: PostKind
    content_text: str
    content_html: str
    url: str
    published_ts: int
    referenced_post: ReferencedPost | None = None


@dataclass(frozen=True, slots=True)
class FeedPost:
    account_username: str
    account_display_name: str | None
    relationship: AccountPostRelationship
    feed_title: str
    source_url: str
    guid: str | None
    post: Post
    raw_xml: str | None = None
    first_seen_ts: int | None = None
    last_seen_ts: int | None = None

    @property
    def display_type(self) -> str:
        return "retweet" if self.relationship == "reposted" else self.post.kind

    def to_dict(self) -> dict:
        referenced_post = self.post.referenced_post
        return {
            "post_id": self.post.post_id,
            "account": {
                "username": self.account_username,
                "display_name": self.account_display_name,
                "relationship": self.relationship,
            },
            "author_username": self.post.author_username,
            "type": self.display_type,
            "kind": self.post.kind,
            "content_text": self.post.content_text,
            "content_html": self.post.content_html,
            "url": self.post.url,
            "published_ts": self.post.published_ts,
            "published_at": ts_to_iso(self.post.published_ts),
            "referenced_post": referenced_post.to_dict() if referenced_post else None,
            "source": {
                "title": self.feed_title,
                "url": self.source_url,
                "guid": self.guid,
            },
            "observed": {
                "first_seen_ts": self.first_seen_ts,
                "first_seen_at": ts_to_iso(self.first_seen_ts),
                "last_seen_ts": self.last_seen_ts,
                "last_seen_at": ts_to_iso(self.last_seen_ts),
            },
        }


@dataclass(frozen=True, slots=True)
class ParsedFeed:
    username: str
    display_name: str | None
    source_url: str
    posts: list[FeedPost]
    source_item_count: int
    failed_item_count: int


@dataclass(frozen=True, slots=True)
class StorageStats:
    inserted_posts: int = 0
    updated_posts: int = 0
    inserted_account_posts: int = 0
    updated_account_posts: int = 0
    inserted_source_items: int = 0
    updated_source_items: int = 0
    total_account_posts: int = 0
    last_post_id: str | None = None
    last_post_ts: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SyncResult:
    username: str
    status: SyncStatus
    requested_url: str
    started_ts: int
    finished_ts: int
    final_url: str | None = None
    http_status: int | None = None
    source_item_count: int = 0
    parsed_post_count: int = 0
    failed_item_count: int = 0
    stats: StorageStats | None = None
    posts: list[FeedPost] = field(default_factory=list)
    error: str | None = None

    def summary_dict(self, *, include_posts: bool = False) -> dict:
        result = {
            "username": self.username,
            "status": self.status,
            "requested_url": self.requested_url,
            "final_url": self.final_url,
            "http_status": self.http_status,
            "started_ts": self.started_ts,
            "started_at": ts_to_iso(self.started_ts),
            "finished_ts": self.finished_ts,
            "finished_at": ts_to_iso(self.finished_ts),
            "duration_seconds": max(0, self.finished_ts - self.started_ts),
            "source_item_count": self.source_item_count,
            "parsed_post_count": self.parsed_post_count,
            "failed_item_count": self.failed_item_count,
            "changes": self.stats.to_dict() if self.stats else None,
            "error": self.error,
        }
        if include_posts:
            result["posts"] = [post.to_dict() for post in self.posts]
        return result
