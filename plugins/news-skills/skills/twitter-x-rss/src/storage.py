from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from models import PostRecord, UserMeta, utc_now_iso


class JSONStorage:
    def __init__(self, root: str | Path = "data"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def user_dir(self, username: str) -> Path:
        path = self.root / username.lower()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def post_file(self, username: str, published_date: str) -> Path:
        return self.user_dir(username) / published_date / "posts.json"

    def ensure_day_dir(self, username: str, published_date: str) -> Path:
        day_dir = self.user_dir(username) / published_date
        day_dir.mkdir(parents=True, exist_ok=True)
        return day_dir

    def load_day_posts(self, username: str, published_date: str) -> list[dict]:
        path = self.post_file(username, published_date)
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def save_day_posts(self, username: str, published_date: str, records: list[dict]) -> None:
        day_dir = self.ensure_day_dir(username, published_date)
        path = day_dir / "posts.json"
        path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert_posts(self, username: str, posts: list[PostRecord]) -> dict:
        inserted = 0
        updated = 0
        touched_dates: set[str] = set()

        by_date: dict[str, list[PostRecord]] = {}
        for post in posts:
            by_date.setdefault(post.published_date, []).append(post)

        for published_date, date_posts in by_date.items():
            touched_dates.add(published_date)
            existing = self.load_day_posts(username, published_date)
            existing_by_id = {item["post_id"]: item for item in existing}

            for post in date_posts:
                payload = post.to_dict()
                if post.post_id in existing_by_id:
                    existing_payload = existing_by_id[post.post_id]
                    if "fetched_at" in existing_payload:
                        payload["fetched_at"] = existing_payload["fetched_at"]
                    if existing_payload != payload:
                        existing_by_id[post.post_id] = payload
                        updated += 1
                else:
                    existing_by_id[post.post_id] = payload
                    inserted += 1

            merged = sorted(existing_by_id.values(), key=lambda x: (x["published_at"], x["post_id"]))
            self.save_day_posts(username, published_date, merged)
            summary = {
                "username": username,
                "date": published_date,
                "count": len(merged),
                "updated_at": utc_now_iso(),
                "post_ids": [item["post_id"] for item in merged],
            }
            (self.ensure_day_dir(username, published_date) / "meta.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        meta = self.rebuild_user_meta(username)
        return {
            "inserted": inserted,
            "updated": updated,
            "touched_dates": sorted(touched_dates),
            "meta": meta.to_dict(),
        }

    def rebuild_user_meta(self, username: str) -> UserMeta:
        user_dir = self.user_dir(username)
        day_dirs = sorted([p for p in user_dir.iterdir() if p.is_dir() and p.name[:4].isdigit()])

        total_posts = 0
        first_date = None
        last_date = None
        last_post_at = None
        last_post_id = None

        for day_dir in day_dirs:
            posts_path = day_dir / "posts.json"
            if not posts_path.exists():
                continue
            posts = json.loads(posts_path.read_text(encoding="utf-8"))
            if not posts:
                continue
            total_posts += len(posts)
            day = day_dir.name
            first_date = first_date or day
            last_date = day
            latest = max(posts, key=lambda p: (p["published_at"], p["post_id"]))
            if last_post_at is None or (latest["published_at"], latest["post_id"]) > (last_post_at, last_post_id or ""):
                last_post_at = latest["published_at"]
                last_post_id = latest["post_id"]

        meta_path = user_dir / "meta.json"
        old_meta = {}
        if meta_path.exists():
            old_meta = json.loads(meta_path.read_text(encoding="utf-8"))

        meta = UserMeta(
            username=username,
            source=old_meta.get("source", "nitter-rss"),
            source_url=old_meta.get("source_url", f"https://nitter.net/{username}"),
            rss_url=old_meta.get("rss_url", f"https://nitter.net/{username}/rss"),
            display_name=old_meta.get("display_name"),
            last_checked_at=utc_now_iso(),
            last_post_at=last_post_at,
            last_post_id=last_post_id,
            total_posts=total_posts,
            total_days=len(day_dirs),
            date_range=f"{first_date}..{last_date}" if first_date and last_date else None,
        )
        meta_path.write_text(json.dumps(meta.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return meta

    def update_user_meta_fields(self, username: str, **fields) -> UserMeta:
        meta_path = self.user_dir(username) / "meta.json"
        current = {}
        if meta_path.exists():
            current = json.loads(meta_path.read_text(encoding="utf-8"))
        current.update(fields)
        meta_path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.rebuild_user_meta(username)
