from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urlparse

from models import (
    AccountPostRelationship,
    FeedPost,
    ParsedFeed,
    Post,
    PostKind,
    ReferencedPost,
    normalize_username,
)

DC_CREATOR = "{http://purl.org/dc/elements/1.1/}creator"
TITLE_RE_REPLY = re.compile(r"^R to @(?P<target>[A-Za-z0-9_]+):\s*(?P<body>.*)$", re.IGNORECASE | re.DOTALL)
TITLE_RE_RETWEET = re.compile(
    r"^(?:RT|Retweeted) by @(?P<who>[A-Za-z0-9_]+):\s*(?P<body>.*)$",
    re.IGNORECASE | re.DOTALL,
)
STATUS_ID_RE = re.compile(r"/status/(?P<id>\d+)")
STATUS_USER_ID_RE = re.compile(
    r"https?://[^/]+/(?P<user>[A-Za-z0-9_]+)/status/(?P<id>\d+)",
    re.IGNORECASE,
)
BLOCKQUOTE_RE = re.compile(r"<blockquote>(?P<body>.*?)</blockquote>", re.IGNORECASE | re.DOTALL)
BLOCK_AUTHOR_RE = re.compile(r"<b>\s*(?P<author>.*?)\s*</b>", re.IGNORECASE | re.DOTALL)
BLOCK_CITE_LINK_RE = re.compile(r'<cite>\s*<a\s+href="(?P<url>[^"]+)"', re.IGNORECASE | re.DOTALL)
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


def _strip_html(value: str) -> str:
    parser = HTMLTextExtractor()
    parser.feed(value)
    parser.close()
    text = parser.get_text()
    if not text:
        text = WS_RE.sub(" ", html.unescape(TAG_RE.sub(" ", value))).strip()
    return text


def _split_main_and_quote_html(description: str) -> tuple[str, str | None]:
    quote_match = BLOCKQUOTE_RE.search(description)
    quote_html = quote_match.group(0) if quote_match else None
    main_html = BLOCKQUOTE_RE.sub("", description)
    main_html = BLOCK_FOOTER_RE.sub("", main_html)
    main_html = HR_RE.sub(" ", main_html)
    return main_html.strip(), quote_html


def _parse_published_ts(value: str) -> int:
    dt = parsedate_to_datetime(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.astimezone(timezone.utc).timestamp())


def _build_x_status_url(username: str, post_id: str) -> str:
    return f"https://x.com/{normalize_username(username)}/status/{post_id}"


def _normalize_status_url(url: str | None) -> tuple[str | None, str | None, str | None]:
    if not url or not (match := STATUS_USER_ID_RE.search(url)):
        return None, None, None
    username = normalize_username(match.group("user"))
    post_id = match.group("id")
    return _build_x_status_url(username, post_id), username, post_id


def _extract_quote_reference(content_html: str) -> ReferencedPost | None:
    block_match = BLOCKQUOTE_RE.search(content_html)
    if not block_match:
        return None

    block_html = block_match.group("body")
    author_username = None
    if author_match := BLOCK_AUTHOR_RE.search(block_html):
        author_text = _strip_html(author_match.group("author"))
        if username_match := USERNAME_RE.search(author_text):
            author_username = normalize_username(username_match.group("user"))

    url = None
    post_id = None
    if cite_match := BLOCK_CITE_LINK_RE.search(block_html):
        url, parsed_username, post_id = _normalize_status_url(cite_match.group("url"))
        author_username = author_username or parsed_username

    body_html = BLOCK_FOOTER_RE.sub("", block_html)
    body_html = BLOCK_AUTHOR_RE.sub("", body_html, count=1)
    content_text = _strip_html(body_html) or None
    if author_username and content_text:
        content_text = re.sub(
            rf"^[^)]*\(@{re.escape(author_username)}\)\s*",
            "",
            content_text,
            count=1,
            flags=re.IGNORECASE,
        ).strip() or None

    if not any((author_username, content_text, post_id, url)):
        return None
    return ReferencedPost(
        author_username=author_username,
        content_text=content_text,
        post_id=post_id,
        url=url,
    )


def _extract_reply_reference(title: str) -> ReferencedPost | None:
    match = TITLE_RE_REPLY.match(title)
    if not match:
        return None
    return ReferencedPost(author_username=normalize_username(match.group("target")))


def _classify_post(
    title: str,
    description: str,
) -> tuple[PostKind, AccountPostRelationship, ReferencedPost | None]:
    if TITLE_RE_REPLY.match(title):
        return "reply", "authored", _extract_reply_reference(title)
    if TITLE_RE_RETWEET.match(title):
        return "tweet", "reposted", None

    lowered = f"{title} {description}".lower()
    if "<blockquote>" in description.lower() or "quote tweet" in lowered or "quoted" in lowered:
        return "quote", "authored", _extract_quote_reference(description)
    return "tweet", "authored", None


def _status_id_from_link(link: str, guid: str | None) -> str:
    for candidate in (link, guid or ""):
        if match := STATUS_ID_RE.search(candidate):
            return match.group("id")
    if guid and guid.isdigit():
        return guid
    tail = urlparse(link).path.rstrip("/").split("/")[-1]
    if tail.isdigit():
        return tail
    raise ValueError(f"Unable to determine post id from link={link!r} guid={guid!r}")


def _content_from_title(
    title: str,
    *,
    kind: PostKind,
    relationship: AccountPostRelationship,
) -> str | None:
    if kind == "reply" and (match := TITLE_RE_REPLY.match(title)):
        return match.group("body").strip() or None
    if relationship == "reposted" and (match := TITLE_RE_RETWEET.match(title)):
        return match.group("body").strip() or None
    return None


def parse_rss(xml_text: str, username: str, rss_url: str) -> ParsedFeed:
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("RSS channel not found")

    account_username = normalize_username(username)
    feed_title = (channel.findtext("title") or "").strip()
    source_url = (channel.findtext("link") or rss_url).strip()
    display_name = feed_title.split(" / @", 1)[0].strip() if " / @" in feed_title else feed_title or None

    posts: list[FeedPost] = []
    items = channel.findall("item")
    failed_item_count = 0

    for item in items:
        try:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            guid = (item.findtext("guid") or "").strip() or None
            description = item.findtext("description") or ""
            creator = normalize_username(item.findtext(DC_CREATOR) or account_username)
            published_ts = _parse_published_ts((item.findtext("pubDate") or "").strip())
            post_id = _status_id_from_link(link, guid)
            kind, relationship, referenced_post = _classify_post(title, description)

            main_html, _ = _split_main_and_quote_html(description)
            content_text = _content_from_title(title, kind=kind, relationship=relationship)
            content_text = content_text or _strip_html(main_html) or _strip_html(description)
            author_username = account_username if kind == "reply" else creator

            posts.append(
                FeedPost(
                    account_username=account_username,
                    account_display_name=display_name,
                    relationship=relationship,
                    feed_title=title,
                    source_url=link,
                    guid=guid,
                    raw_xml=ET.tostring(item, encoding="unicode"),
                    post=Post(
                        post_id=post_id,
                        author_username=author_username,
                        kind=kind,
                        content_text=content_text,
                        content_html=main_html,
                        url=_build_x_status_url(author_username, post_id),
                        published_ts=published_ts,
                        referenced_post=referenced_post,
                    ),
                )
            )
        except (TypeError, ValueError, OverflowError):
            failed_item_count += 1

    if items and failed_item_count == len(items):
        raise ValueError("all RSS items failed to parse")

    posts.sort(key=lambda item: (item.post.published_ts, item.post.post_id))
    return ParsedFeed(
        username=account_username,
        display_name=display_name,
        source_url=source_url,
        posts=posts,
        source_item_count=len(items),
        failed_item_count=failed_item_count,
    )
