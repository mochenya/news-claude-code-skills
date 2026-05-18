from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urlparse

from models import OriginalPost, PostRecord, utc_now_iso

DC_CREATOR = "{http://purl.org/dc/elements/1.1/}creator"
TITLE_RE_REPLY = re.compile(r"^R to @(?P<target>[A-Za-z0-9_]+):\s*(?P<body>.*)$", re.IGNORECASE | re.DOTALL)
TITLE_RE_RETWEET = re.compile(r"^(RT|Retweeted) by @(?P<who>[A-Za-z0-9_]+):\s*(?P<body>.*)$", re.IGNORECASE | re.DOTALL)
TITLE_RE_RETWEET_ALT = re.compile(r"^RT by @(?P<who>[A-Za-z0-9_]+):\s*(?P<body>.*)$", re.IGNORECASE | re.DOTALL)
STATUS_ID_RE = re.compile(r"/status/(?P<id>\d+)")
STATUS_USER_ID_RE = re.compile(r"https?://[^/]+/(?P<user>[A-Za-z0-9_]+)/status/(?P<id>\d+)", re.IGNORECASE)
BLOCKQUOTE_RE = re.compile(r"<blockquote>(?P<body>.*?)</blockquote>", re.IGNORECASE | re.DOTALL)
BLOCK_AUTHOR_RE = re.compile(r"<b>\s*(?P<author>.*?)\s*</b>", re.IGNORECASE | re.DOTALL)
BLOCK_CITE_LINK_RE = re.compile(r"<cite>\s*<a\s+href=\"(?P<url>[^\"]+)\"", re.IGNORECASE | re.DOTALL)
BLOCK_FOOTER_RE = re.compile(r"<footer>.*?</footer>", re.IGNORECASE | re.DOTALL)
HR_RE = re.compile(r"<hr\s*/?>", re.IGNORECASE)
USERNAME_RE = re.compile(r"@(?P<user>[A-Za-z0-9_]+)")
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


class HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"br", "p", "div", "li"}:
            self.parts.append("\n")

    def get_text(self) -> str:
        joined = "".join(self.parts)
        return WS_RE.sub(" ", joined.replace("\xa0", " ")).strip()


@dataclass(slots=True)
class ParsedFeed:
    username: str
    display_name: str | None
    source_url: str
    posts: list[PostRecord]



def _strip_html(value: str) -> str:
    parser = HTMLTextExtractor()
    parser.feed(value)
    parser.close()
    text = parser.get_text()
    if not text:
        text = html.unescape(TAG_RE.sub(" ", value))
        text = WS_RE.sub(" ", text).strip()
    return text


def _split_main_and_quote_html(description: str) -> tuple[str, str | None]:
    quote_html = None
    if bm := BLOCKQUOTE_RE.search(description or ""):
        quote_html = bm.group(0)

    main_html = BLOCKQUOTE_RE.sub("", description or "")
    main_html = BLOCK_FOOTER_RE.sub("", main_html)
    main_html = HR_RE.sub(" ", main_html)
    return main_html, quote_html



def _parse_datetime(value: str) -> datetime:
    dt = parsedate_to_datetime(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _build_x_status_url(username: str, post_id: str) -> str:
    clean_user = username.strip().lstrip("@")
    return f"https://x.com/{clean_user}/status/{post_id}"


def _normalize_status_url(
    url: str | None,
    *,
    fallback_user: str | None = None,
    fallback_post_id: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    if url and (m := STATUS_USER_ID_RE.search(url)):
        user = m.group("user")
        post_id = m.group("id")
        return _build_x_status_url(user, post_id), user, post_id

    if fallback_user and fallback_post_id:
        return _build_x_status_url(fallback_user, fallback_post_id), fallback_user, fallback_post_id

    return None, fallback_user, fallback_post_id


def _extract_original_post_from_quote(content_html: str) -> OriginalPost | None:
    if not content_html:
        return None
    block_m = BLOCKQUOTE_RE.search(content_html)
    if not block_m:
        return None

    block_html = block_m.group("body")

    author = None
    if am := BLOCK_AUTHOR_RE.search(block_html):
        author_raw = _strip_html(am.group("author"))
        if author_raw:
            # Example: "X Freeze (@XFreeze)"
            if um := USERNAME_RE.search(author_raw):
                author = um.group("user")
            else:
                author = author_raw

    quote_url = None
    quote_post_id = None
    if cm := BLOCK_CITE_LINK_RE.search(block_html):
        raw_quote_url = cm.group("url")
        normalized_url, parsed_user, parsed_post_id = _normalize_status_url(raw_quote_url)
        quote_url = normalized_url
        quote_post_id = parsed_post_id
        if not author and parsed_user:
            author = parsed_user

    body_for_text = BLOCK_FOOTER_RE.sub("", block_html)
    body_for_text = BLOCK_AUTHOR_RE.sub("", body_for_text, count=1)
    quoted_text = _strip_html(body_for_text)

    if author and quoted_text:
        quoted_text = re.sub(
            rf"^[^)]*\(@{re.escape(author)}\)\s*",
            "",
            quoted_text,
            count=1,
            flags=re.IGNORECASE,
        ).strip()

    if not (author or quoted_text or quote_url or quote_post_id):
        return None

    if (not quote_url) and author and quote_post_id:
        quote_url = _build_x_status_url(author, quote_post_id)

    return OriginalPost(
        author=author,
        content=quoted_text or None,
        post_id=quote_post_id,
        url=quote_url,
    )


def _extract_original_post_from_reply(title: str, content_text: str) -> OriginalPost | None:
    if not (m := TITLE_RE_REPLY.match(title.strip())):
        return None
    target = m.group("target")
    # RSS 对回复场景通常只给到“当前回复内容”，拿不到被回复原帖正文。
    return OriginalPost(author=target or None, content=None, post_id=None, url=None)


def _extract_original_post_from_retweet(title: str, content_text: str, content_html: str, creator: str) -> OriginalPost | None:
    title = title.strip()
    body = None
    if m := TITLE_RE_RETWEET.match(title):
        body = m.group("body").strip() or content_text
    elif m := TITLE_RE_RETWEET_ALT.match(title):
        body = m.group("body").strip() or content_text

    source_url = None
    post_id = None
    original_author = creator
    if su := STATUS_USER_ID_RE.search(content_html):
        raw_source_url = su.group(0)
        normalized_url, parsed_user, parsed_post_id = _normalize_status_url(raw_source_url)
        source_url = normalized_url
        post_id = parsed_post_id
        if parsed_user:
            original_author = parsed_user

    return OriginalPost(
        author=original_author or creator,
        content=body or content_text or None,
        post_id=post_id,
        url=source_url,
    )


def _detect_type_and_original_post(
    *,
    title: str,
    content_text: str,
    content_html: str,
    creator: str,
) -> tuple[str, OriginalPost | None]:
    normalized_title = title.strip()
    if TITLE_RE_REPLY.match(normalized_title):
        return "reply", _extract_original_post_from_reply(normalized_title, content_text)
    if TITLE_RE_RETWEET.match(normalized_title) or TITLE_RE_RETWEET_ALT.match(normalized_title):
        return "retweet", _extract_original_post_from_retweet(normalized_title, content_text, content_html, creator)

    lowered = f"{normalized_title} {content_text} {content_html}".lower()
    if "<blockquote>" in content_html.lower() or "quote tweet" in lowered or "quoted" in lowered:
        return "quote", _extract_original_post_from_quote(content_html)

    return "tweet", None



def _status_id_from_link(link: str, guid: str | None) -> str:
    for candidate in (link, guid or ""):
        if m := STATUS_ID_RE.search(candidate):
            return m.group("id")
    if guid and guid.isdigit():
        return guid
    parsed = urlparse(link)
    tail = parsed.path.rstrip("/").split("/")[-1]
    if tail.isdigit():
        return tail
    raise ValueError(f"Unable to determine post id from link={link!r} guid={guid!r}")



def parse_rss(xml_text: str, username: str, rss_url: str) -> ParsedFeed:
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("RSS channel not found")

    feed_title = (channel.findtext("title") or "").strip()
    source_url = (channel.findtext("link") or rss_url).strip()

    display_name = None
    if " / @" in feed_title:
        display_name = feed_title.split(" / @", 1)[0].strip()
    elif feed_title:
        display_name = feed_title.strip()

    posts: list[PostRecord] = []
    fetched_at = utc_now_iso()
    items = channel.findall("item")
    failed_items = 0

    for item in items:
        try:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            guid = (item.findtext("guid") or "").strip() or None
            description = item.findtext("description") or ""
            creator = (item.findtext(DC_CREATOR) or username).strip().lstrip("@")
            account_username = username.strip().lstrip("@")
            pub_date_raw = (item.findtext("pubDate") or "").strip()
            published_dt = _parse_datetime(pub_date_raw)
            published_at = published_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
            published_date = published_dt.date().isoformat()

            main_html, _ = _split_main_and_quote_html(description)
            main_text = _strip_html(main_html)

            post_type, original_post = _detect_type_and_original_post(
                title=title,
                content_text=main_text,
                content_html=description,
                creator=creator,
            )
            post_id = _status_id_from_link(link, guid)

            normalized_url = f"https://x.com/{creator}/status/{post_id}"

            content_text = main_text
            if post_type == "reply":
                if rm := TITLE_RE_REPLY.match(title):
                    reply_body = (rm.group("body") or "").strip()
                    if reply_body:
                        content_text = reply_body
            elif post_type == "retweet":
                if rm := TITLE_RE_RETWEET.match(title):
                    rt_body = (rm.group("body") or "").strip()
                    if rt_body:
                        content_text = rt_body
                elif rm := TITLE_RE_RETWEET_ALT.match(title):
                    rt_body = (rm.group("body") or "").strip()
                    if rt_body:
                        content_text = rt_body

            if not content_text:
                content_text = _strip_html(description)

            if post_type == "reply":
                author_username = account_username
            else:
                author_username = creator

            posts.append(
                PostRecord(
                    post_id=post_id,
                    account_username=account_username,
                    account_display_name=display_name,
                    author_username=author_username,
                    display_name=display_name,
                    type=post_type,
                    title=title,
                    content_html=description,
                    content_text=content_text,
                    url=normalized_url,
                    source_url=link,
                    published_at=published_at,
                    published_date=published_date,
                    fetched_at=fetched_at,
                    guid=guid,
                    original_post=original_post,
                )
            )
        except Exception:
            failed_items += 1
            continue

    if items and failed_items == len(items):
        raise ValueError("all rss items failed to parse")

    posts.sort(key=lambda p: (p.published_at, p.post_id))
    return ParsedFeed(username=username, display_name=display_name, source_url=source_url, posts=posts)
