from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

try:
    from breaking_news import apply_breaking_overrides
except Exception:
    def apply_breaking_overrides(report: dict[str, Any], vertical: str) -> dict[str, Any]:
        return report


ET_ZONE = ZoneInfo("America/New_York")

MAX_LIVE_STORY_AGE_HOURS = 12
MAX_EDITOR_STORY_AGE_HOURS = 36
MAX_PUBLIC_FALLBACK_AGE_HOURS = 72

MIN_TARGET_SECTIONS = {
    "ai": 6,
    "politics": 6,
    "entertainment": 6,
}

MAX_SECTIONS = {
    "ai": 10,
    "politics": 10,
    "entertainment": 10,
}

SOURCE_CAPS = {
    "ai": 3,
    "politics": 2,
    "entertainment": 2,
}

ENTERTAINMENT_VARIETY_SOFT_CAP = 1
ENTERTAINMENT_VARIETY_RELAXED_CAP = 1
ENTERTAINMENT_FILM_SOFT_CAP = 2

MIN_LEAD_SCORE = {
    "ai": 30,
    "politics": 65,
    "entertainment": 42,
}

PUBLIC_LABEL_PATTERN = re.compile(r"^\s*\[(BREAKING|DEVELOPING|WATCH|UPDATE|LIVE|EXCLUSIVE)\]\s*", re.I)


SITES = {
    "Global AI Report": {
        "slug": "ai",
        "output": Path("latest_ai_report.json"),
        "accent": "AI",
        "video_url": "https://www.youtube.com/embed/21X5lGlDOfg?rel=0&autoplay=1&mute=1",
        "feeds": [
            "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://venturebeat.com/category/ai/feed/",
            "https://www.artificialintelligence-news.com/feed/",
            "https://www.wired.com/feed/tag/ai/latest/rss",
            "https://arstechnica.com/feed/",
        ],
        "fallback_headline": "AI sector sees steady flow of model, infrastructure and policy developments",
    },
    "Global Politics Report": {
        "slug": "politics",
        "output": Path("latest_politics_report.json"),
        "accent": "Politics",
        "video_url": "https://www.youtube.com/embed/21X5lGlDOfg?rel=0&autoplay=1&mute=1",
        "feeds": [
            "https://thehill.com/feed/",
            "https://www.cbsnews.com/latest/rss/politics",
            "https://www.npr.org/rss/rss.php?id=1014",
            "https://www.aljazeera.com/xml/rss/all.xml",
        ],
        "fallback_headline": "Politics desk tracks federal power, courts, campaigns and global policy developments",
    },
    "Global Entertainment Report": {
        "slug": "entertainment",
        "output": Path("latest_entertainment_report.json"),
        "accent": "Entertainment",
        "video_url": "https://www.youtube.com/embed/21X5lGlDOfg?rel=0&autoplay=1&mute=1",
        "feeds": [
            "https://www.hollywoodreporter.com/feed/",
            "https://deadline.com/feed/",
            "https://www.thewrap.com/feed/",
            "https://www.billboard.com/feed/",
            "https://www.rollingstone.com/tv-movies/tv-movie-news/feed/",
            "https://www.rollingstone.com/music/music-news/feed/",
            "https://www.polygon.com/rss/index.xml",
            "https://www.ign.com/articles/feed",
            "https://www.indiewire.com/feed/",
            "https://variety.com/feed/",
        ],
        "fallback_headline": "Streaming wars, studios, creators, box office and entertainment industry shifts drive the newsroom watch",
    },
}


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GSRNetworkContentEngine/3.9; +https://globalsportsreport.com)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


SOURCE_LABELS = {
    "theverge.com": "The Verge",
    "techcrunch.com": "TechCrunch",
    "venturebeat.com": "VentureBeat",
    "artificialintelligence-news.com": "AI News",
    "thehill.com": "The Hill",
    "cbsnews.com": "CBS News",
    "npr.org": "NPR",
    "aljazeera.com": "Al Jazeera",
    "variety.com": "Variety",
    "hollywoodreporter.com": "The Hollywood Reporter",
    "deadline.com": "Deadline",
    "thewrap.com": "TheWrap",
    "billboard.com": "Billboard",
    "indiewire.com": "IndieWire",
    "rollingstone.com": "Rolling Stone",
    "polygon.com": "Polygon",
    "ign.com": "IGN",
}


BREAKING_TERMS = [
    "breaking", "urgent", "just in", "resigns", "resign", "fired", "ousted",
    "dies", "dead", "lawsuit", "sues", "charged", "indicted", "investigation",
    "probe", "ban", "blocked", "halted", "strike", "shutdown", "merger",
    "acquisition", "layoffs", "cuts", "released", "exclusive",
]

AI_PRIORITY_TERMS = [
    "ai", "artificial intelligence", "openai", "anthropic", "google", "microsoft", "meta", "nvidia", "apple",
    "amazon", "chip", "chips", "semiconductor", "data center", "datacenter", "model", "models", "llm",
    "generative", "lawsuit", "regulation", "regulatory", "safety", "startup", "funding", "enterprise",
    "agent", "agents", "robot", "robotics", "aws", "cloud", "claude", "gemini", "chatgpt",
    "copilot", "deepmind", "perplexity", "mistral", "xai", "databricks", "hugging face",
    "pentagon", "defense", "automation", "machine learning", "neural", "inference", "training",
]

AI_HIGH_AUTHORITY_TERMS = [
    "openai", "anthropic", "google", "deepmind", "microsoft", "nvidia", "meta", "apple", "amazon",
    "aws", "claude", "gemini", "chatgpt", "gpt", "copilot", "perplexity", "mistral", "xai",
]

AI_STRONG_NEWS_TERMS = [
    "launch", "released", "release", "unveils", "announces", "funding", "valuation",
    "lawsuit", "court", "regulation", "regulatory", "safety", "ban", "policy",
    "chip", "chips", "semiconductor", "data center", "datacenter", "enterprise",
    "agent", "agents", "model", "models", "llm", "robot", "robotics",
]

POLITICS_HARD_TERMS = [
    "trump", "biden", "congress", "senate", "house", "white house",
    "supreme court", "court", "judge", "lawsuit", "election", "campaign",
    "governor", "mayor", "democrat", "republican", "gop", "tariff",
    "immigration", "border", "ukraine", "gaza", "israel", "iran", "china",
    "russia", "policy", "budget", "tax", "federal", "administration",
    "lawmakers", "vote", "bill", "hearing", "investigation",
    "justice department", "state department", "pentagon", "cabinet",
    "president", "vice president", "secretary", "sanctions",
]

POLITICS_SOFT_TERMS = [
    "correspondents", "dinner", "comedian", "actor", "actress", "movie",
    "film", "celebrity", "red carpet", "hollywood", "music", "tv",
    "television", "sports", "nfl", "nba", "mlb", "nhl", "fashion",
    "met gala", "box office", "concert", "album",
]

POLITICS_SPORTS_PRIMARY_TERMS = [
    "cricket", "test match", "one-day international", "athlete", "coach", "player",
    "team", "league", "tournament", "championship", "match", "innings", "wicket",
    "batting", "bowling", "sports record", "hall of fame",
]

POLITICS_AFFIRMATIVE_TERMS = [
    "government", "election", "campaign", "legislation", "legislature", "congress",
    "senate", "parliament", "white house", "supreme court", "court ruling", "judge",
    "public policy", "foreign policy", "diplomacy", "diplomatic", "political party",
    "democrat", "republican", "gop", "minister", "president", "governor", "mayor",
    "lawmakers", "agency", "administration", "cabinet", "bill", "vote", "sanctions",
    "governance", "accountability", "investigation", "justice department", "state department",
]

POLITICS_SPORTS_CONNECTION_TERMS = [
    "sports law", "sports policy", "government funding", "public funding", "diplomatic boycott",
    "court ruling", "legal challenge", "legislation", "parliamentary hearing",
    "congressional hearing", "government investigation", "election campaign",
]

ENTERTAINMENT_PRIORITY_TERMS = [
    "box office", "streaming", "netflix", "disney", "warner", "warner bros",
    "paramount", "universal", "sony", "hollywood", "studio", "film", "films",
    "movie", "movies", "tv", "television", "music", "album", "tour", "concert",
    "ratings", "festival", "oscar", "oscars", "emmy", "emmys", "grammy", "grammys",
    "hbo", "max", "peacock", "hulu", "prime video", "amazon prime", "apple tv",
    "deadline", "variety", "hollywood reporter", "billboard", "indiewire",
    "rolling stone", "thewrap", "marvel", "dc", "pixar", "lucasfilm", "star wars",
    "taylor swift", "beyonce", "beyoncé", "drake", "kendrick", "lady gaga",
    "spotify", "youtube", "tiktok", "creator", "creators", "influencer",
    "gaming", "video game", "xbox", "playstation", "nintendo", "ign", "polygon",
    "anime", "manga", "comic-con", "broadway", "audience", "viewership",
    "trailer", "release date", "renewed", "canceled", "cancelled", "season",
    "franchise", "sequel", "reboot", "remake", "casting", "cast", "showrunner",
]

ENTERTAINMENT_HIGH_AUTHORITY_TERMS = [
    "netflix", "disney", "warner", "warner bros", "hbo", "max", "paramount",
    "universal", "sony", "amazon", "prime video", "apple tv", "hulu", "peacock",
    "marvel", "dc", "pixar", "lucasfilm", "star wars", "spotify", "youtube",
    "tiktok", "taylor swift", "beyonce", "beyoncé", "drake", "kendrick",
]

ENTERTAINMENT_STRONG_NEWS_TERMS = [
    "box office", "streaming", "released", "release", "launch", "trailer",
    "renewed", "canceled", "cancelled", "lawsuit", "strike", "deal", "merger",
    "acquisition", "layoffs", "cuts", "casting", "cast", "showrunner",
    "festival", "oscar", "emmy", "grammy", "ratings", "viewership",
    "tour", "album", "concert", "franchise", "sequel", "reboot", "remake",
]

ENTERTAINMENT_TOPIC_KEYWORDS = {
    "tv": [
        "tv", "television", "series", "show", "episode", "season", "renewed",
        "canceled", "cancelled", "showrunner", "upfront", "ratings", "viewership",
        "nbc", "abc", "cbs", "fox", "hbo",
    ],
    "streaming": [
        "streaming", "netflix", "hulu", "max", "prime video", "amazon prime",
        "apple tv", "peacock", "paramount+", "disney+", "subscriber", "platform",
    ],
    "music": [
        "music", "album", "song", "single", "tour", "concert", "festival",
        "spotify", "billboard", "grammy", "grammys", "artist", "band",
    ],
    "studios_business": [
        "studio", "studios", "disney", "warner", "warner bros", "paramount",
        "universal", "sony", "nbcuniversal", "deal", "merger", "acquisition",
        "layoffs", "cuts", "advertising", "upfront", "earnings", "ceo",
    ],
    "celebrity": [
        "celebrity", "actor", "actress", "singer", "host", "red carpet",
        "relationship", "married", "divorce", "estate", "dies", "dead",
    ],
    "awards": [
        "oscar", "oscars", "emmy", "emmys", "grammy", "grammys", "tony",
        "golden globe", "sag awards", "academy", "nomination", "nominations",
    ],
    "production_labor": [
        "production", "shoot", "filming", "casting", "cast", "crew", "strike",
        "union", "sag-aftra", "wga", "iatse", "labor", "showrunner",
    ],
    "box_office": [
        "box office", "opening weekend", "theatrical", "ticket sales", "gross",
        "domestic", "worldwide", "cinema", "theaters", "theatres",
    ],
    "media_platforms": [
        "youtube", "tiktok", "spotify", "podcast", "advertising", "media company",
        "creator", "creators", "influencer", "social", "platform",
    ],
    "gaming": [
        "gaming", "video game", "playstation", "xbox", "nintendo", "ign",
        "polygon", "game", "games", "interactive",
    ],
    "film": [
        "film", "movie", "movies", "sequel", "reboot", "remake", "franchise",
        "trailer", "director", "screenwriter", "cinema",
    ],
}

ENTERTAINMENT_TOPIC_ORDER = [
    "tv",
    "streaming",
    "music",
    "studios_business",
    "celebrity",
    "awards",
    "production_labor",
    "box_office",
    "media_platforms",
    "gaming",
    "film",
]

BAD_PUBLIC_HEADLINE_TERMS = [
    "daily roundup", "newsletter", "what to watch", "live updates",
    "recap", "photos", "quiz", "horoscope", "podcast",
]

ENTERTAINMENT_GENERIC_HEADLINE_TERMS = [
    "developments under review",
    "major developments under review",
    "track strongest entertainment",
    "entertainment newsroom watch",
    "coverage tracks studios",
    "industry coverage tracks",
    "monitor audience behavior",
    "prioritize verified source links",
    "watch studios, platforms",
]

AI_BLOCK_TERMS = [
    "box office", "movie review", "film review", "celebrity", "red carpet", "nba", "nfl", "mlb", "nhl",
    "soccer", "baseball", "basketball", "football", "hockey", "wwe", "ufc", "fashion montage",
]

TOPIC_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "with", "without", "from", "into", "onto", "over",
    "under", "after", "before", "about", "because", "very", "this", "that", "these", "those",
    "for", "to", "of", "in", "on", "at", "by", "as", "is", "are", "was", "were", "be", "been",
    "will", "would", "could", "should", "may", "might", "can", "new", "says", "say", "said",
    "report", "reports", "watch", "breaking", "exclusive", "update", "live", "latest",
}


def now_et() -> str:
    return datetime.now(ET_ZONE).strftime("%Y-%m-%d %I:%M:%S %p ET")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)

    for _ in range(5):
        previous = text
        text = html.unescape(text)
        if text == previous:
            break

    text = re.sub(r"<script.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)

    for _ in range(5):
        previous = text
        text = html.unescape(text)
        if text == previous:
            break

    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2014": "—",
        "\u2013": "–",
        "\xa0": " ",
        "&amp;": "&",
        "&quot;": '"',
        "&apos;": "'",
        "&nbsp;": " ",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    text = re.sub(r"&#x27;|&#39;", "'", text, flags=re.I)
    text = re.sub(r"&#x2019;|&#8217;", "'", text, flags=re.I)
    text = re.sub(r"&#x2018;|&#8216;", "'", text, flags=re.I)
    text = re.sub(r"&#x201c;|&#8220;", '"', text, flags=re.I)
    text = re.sub(r"&#x201d;|&#8221;", '"', text, flags=re.I)
    text = re.sub(r"&#x2014;|&#8212;", "—", text, flags=re.I)
    text = re.sub(r"&#x2013;|&#8211;", "–", text, flags=re.I)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def strip_public_labels(text: str) -> str:
    text = clean_text(text)
    for _ in range(3):
        text = PUBLIC_LABEL_PATTERN.sub("", text).strip()
    return text


def smart_trim(text: str, limit: int = 220) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.strip() + "..."


def normalize_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean_text(text).lower())[:120]


def normalize_words(text: str) -> list[str]:
    text = strip_public_labels(text).lower()
    text = re.sub(r"https?://\S+", " ", text)
    words = re.findall(r"[a-z0-9]+", text)
    return [word for word in words if len(word) > 2 and word not in TOPIC_STOPWORDS]


def topic_signature(text: str, limit: int = 8) -> str:
    words = normalize_words(text)
    seen: list[str] = []
    for word in words:
        if word not in seen:
            seen.append(word)
        if len(seen) >= limit:
            break
    return " ".join(seen)


def headline_similarity(a: str, b: str) -> float:
    a_clean = " ".join(normalize_words(a))
    b_clean = " ".join(normalize_words(b))
    if not a_clean or not b_clean:
        return 0.0

    ratio = SequenceMatcher(None, a_clean, b_clean).ratio()

    a_words = set(a_clean.split())
    b_words = set(b_clean.split())
    overlap = len(a_words & b_words) / max(1, min(len(a_words), len(b_words)))

    return max(ratio, overlap)


def story_is_duplicate_topic(
    story: dict[str, str],
    selected: list[dict[str, str]],
    site_slug: str,
) -> bool:
    headline = story.get("headline", "")
    signature = topic_signature(headline)

    for existing in selected:
        existing_headline = existing.get("headline", "")
        existing_signature = topic_signature(existing_headline)

        if normalize_key(headline) == normalize_key(existing_headline):
            return True

        similarity = headline_similarity(headline, existing_headline)

        if site_slug == "entertainment":
            if similarity >= 0.54:
                return True
            if signature and existing_signature and len(set(signature.split()) & set(existing_signature.split())) >= 4:
                return True

        elif site_slug == "politics":
            if similarity >= 0.68:
                return True

        else:
            if similarity >= 0.72:
                return True

    return False


def source_name_from_url(url: str) -> str:
    lower = clean_text(url).lower()
    for domain, label in SOURCE_LABELS.items():
        if domain in lower:
            return label
    match = re.search(r"https?://(?:www\.)?([^/]+)", lower)
    return match.group(1) if match else "Unknown Source"


def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_story_datetime(value: str) -> datetime | None:
    value = clean_text(value)
    if not value:
        return None

    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        pass

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def story_age_hours(story: dict[str, str]) -> float | None:
    parsed = parse_story_datetime(story.get("published", ""))
    if parsed is None:
        return None
    return max(0.0, (now_utc() - parsed).total_seconds() / 3600)


def story_is_fresh(story: dict[str, str], max_age_hours: int) -> bool:
    age = story_age_hours(story)
    if age is None:
        return True
    return age <= max_age_hours


def add_freshness_fields(story: dict[str, str]) -> dict[str, str]:
    age = story_age_hours(story)
    if age is None:
        story["freshness_status"] = "unknown"
        story["age_hours"] = ""
    else:
        story["age_hours"] = f"{age:.2f}"
        if age <= MAX_LIVE_STORY_AGE_HOURS:
            story["freshness_status"] = "fresh"
        elif age <= MAX_EDITOR_STORY_AGE_HOURS:
            story["freshness_status"] = "editor_fresh"
        else:
            story["freshness_status"] = "stale"
    return story


def parse_feed(xml_text: str, source_url: str) -> list[dict[str, str]]:
    stories: list[dict[str, str]] = []
    source_name = source_name_from_url(source_url)

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return stories

    channel_items = root.findall(".//item")

    if channel_items:
        for item in channel_items:
            title = clean_text(item.findtext("title"))
            link = clean_text(item.findtext("link"))

            raw_desc = (
                item.findtext("description")
                or item.findtext("summary")
                or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
                or title
            )

            desc = clean_text(raw_desc)
            pub_date = clean_text(
                item.findtext("pubDate")
                or item.findtext("published")
                or item.findtext("updated")
                or ""
            )

            if title and link:
                stories.append(add_freshness_fields({
                    "headline": strip_public_labels(title),
                    "url": clean_text(link),
                    "snapshot": smart_trim(desc or title, 280),
                    "source_feed": source_url,
                    "source_name": source_name,
                    "published": pub_date,
                }))

        return stories

    ns = {"atom": "http://www.w3.org/2005/Atom"}

    for entry in root.findall(".//atom:entry", ns):
        title = clean_text(entry.findtext("atom:title", default="", namespaces=ns))

        link = ""
        for link_node in entry.findall("atom:link", ns):
            href = clean_text(link_node.attrib.get("href", ""))
            rel = clean_text(link_node.attrib.get("rel", "alternate"))
            if href and rel in {"alternate", ""}:
                link = href
                break

        raw_desc = (
            entry.findtext("atom:summary", default="", namespaces=ns)
            or entry.findtext("atom:content", default="", namespaces=ns)
            or title
        )

        pub_date = clean_text(
            entry.findtext("atom:published", default="", namespaces=ns)
            or entry.findtext("atom:updated", default="", namespaces=ns)
            or ""
        )

        if title and link:
            stories.append(add_freshness_fields({
                "headline": strip_public_labels(title),
                "url": clean_text(link),
                "snapshot": smart_trim(raw_desc or title, 280),
                "source_feed": source_url,
                "source_name": source_name,
                "published": pub_date,
            }))

    return stories


def dedupe_stories(stories: list[dict[str, str]], site_slug: str = "") -> list[dict[str, str]]:
    seen_keys: set[str] = set()
    seen_urls: set[str] = set()
    clean: list[dict[str, str]] = []
    duplicate_count = 0

    for story in stories:
        headline = strip_public_labels(story.get("headline"))
        url = clean_text(story.get("url"))

        if not headline or not url:
            continue

        key = normalize_key(headline)
        url_key = re.sub(r"[?#].*$", "", url).rstrip("/").lower()

        if key in seen_keys or url_key in seen_urls or story_is_duplicate_topic({"headline": headline}, clean, site_slug):
            duplicate_count += 1
            continue

        seen_keys.add(key)
        seen_urls.add(url_key)
        story["headline"] = headline
        story["url"] = url
        story["snapshot"] = clean_text(story.get("snapshot", headline))
        story["source_name"] = clean_text(story.get("source_name", "")) or source_name_from_url(story.get("source_feed", ""))
        add_freshness_fields(story)
        clean.append(story)

    if site_slug:
        print(f"[DEDUPE] {site_slug}: kept {len(clean)} | skipped {duplicate_count} duplicate/topic-repeat stories")

    return clean


def contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def urgency_label(story: dict[str, str]) -> str:
    combined = f"{story.get('headline', '')} {story.get('snapshot', '')}".lower()

    if any(term in combined for term in ["breaking", "urgent", "just in", "fired", "dies", "dead", "indicted", "charged"]):
        return "BREAKING"

    if any(term in combined for term in ["lawsuit", "probe", "investigation", "shutdown", "strike", "ban", "blocked"]):
        return "DEVELOPING"

    if any(term in combined for term in ["deal", "merger", "acquisition", "launch", "released", "expands", "funding"]):
        return "WATCH"

    return ""


def display_headline(story: dict[str, str]) -> str:
    return strip_public_labels(story.get("headline", ""))


def breaking_score(story: dict[str, str]) -> int:
    headline = clean_text(story.get("headline", "")).lower()
    snapshot = clean_text(story.get("snapshot", "")).lower()
    combined = f"{headline} {snapshot}"

    score = 0

    for term in BREAKING_TERMS:
        if term in combined:
            score += 12

    if contains_any(headline, BREAKING_TERMS):
        score += 10

    return score


def is_bad_public_story(story: dict[str, str], site_slug: str) -> bool:
    headline = clean_text(story.get("headline", "")).lower()
    snapshot = clean_text(story.get("snapshot", "")).lower()
    combined = f"{headline} {snapshot}"

    if not headline or len(headline) < 18:
        return True

    if any(term in headline for term in BAD_PUBLIC_HEADLINE_TERMS):
        return True

    if story.get("url", "#") == "#":
        return True

    if not story_is_fresh(story, MAX_PUBLIC_FALLBACK_AGE_HOURS):
        return True

    if site_slug == "politics":
        hard = contains_any(combined, POLITICS_HARD_TERMS)
        soft = contains_any(combined, POLITICS_SOFT_TERMS)
        affirmative = contains_any(combined, POLITICS_AFFIRMATIVE_TERMS)
        sports_primary = contains_any(headline, POLITICS_SPORTS_PRIMARY_TERMS)
        genuine_sports_connection = contains_any(combined, POLITICS_SPORTS_CONNECTION_TERMS)
        if not affirmative:
            return True
        if sports_primary and not genuine_sports_connection:
            return True
        if soft and not hard:
            return True

    if site_slug == "ai":
        if contains_any(combined, AI_BLOCK_TERMS):
            return True
        if not contains_any(combined, AI_PRIORITY_TERMS):
            return True

    if site_slug == "entertainment":
        if any(term in combined for term in ENTERTAINMENT_GENERIC_HEADLINE_TERMS):
            return True
        if not contains_any(combined, ENTERTAINMENT_PRIORITY_TERMS):
            return True

    return False


def score_story(story: dict[str, str], site_slug: str) -> int:
    headline = clean_text(story.get("headline", "")).lower()
    snapshot = clean_text(story.get("snapshot", "")).lower()
    combined = f"{headline} {snapshot}"

    score = 0
    score += breaking_score(story)

    if story_is_fresh(story, MAX_LIVE_STORY_AGE_HOURS):
        score += 40
    elif story_is_fresh(story, MAX_EDITOR_STORY_AGE_HOURS):
        score += 10
    elif story_is_fresh(story, MAX_PUBLIC_FALLBACK_AGE_HOURS):
        score += 2
    else:
        score -= 100

    if site_slug == "politics":
        for term in POLITICS_HARD_TERMS:
            if term in combined:
                score += 8
        for term in POLITICS_SOFT_TERMS:
            if term in combined:
                score -= 30
        if any(term in headline for term in ["trump", "biden", "congress", "senate", "supreme court", "white house"]):
            score += 18

        source = clean_text(story.get("source_name", "")).lower()
        if source in {"cbs news", "npr"}:
            score += 12
        if source == "the hill":
            score -= 5
        if source == "al jazeera":
            score -= 10

    elif site_slug == "ai":
        for term in AI_PRIORITY_TERMS:
            if term in combined:
                score += 8
        for term in AI_STRONG_NEWS_TERMS:
            if term in combined:
                score += 10
        if any(term in headline for term in AI_HIGH_AUTHORITY_TERMS):
            score += 22
        if any(term in headline for term in ["launch", "release", "released", "unveils", "announces", "lawsuit", "funding", "chip", "model"]):
            score += 16

    elif site_slug == "entertainment":
        for term in ENTERTAINMENT_PRIORITY_TERMS:
            if term in combined:
                score += 8

        for term in ENTERTAINMENT_STRONG_NEWS_TERMS:
            if term in combined:
                score += 10

        if any(term in headline for term in ENTERTAINMENT_HIGH_AUTHORITY_TERMS):
            score += 24

        if any(term in headline for term in [
            "netflix", "disney", "warner", "hbo", "max", "box office",
            "streaming", "marvel", "taylor swift", "oscar", "emmy",
            "grammy", "spotify", "youtube", "gaming", "ign", "polygon",
        ]):
            score += 18

        if any(term in combined for term in ENTERTAINMENT_GENERIC_HEADLINE_TERMS):
            score -= 120

        source = clean_text(story.get("source_name", "")).lower()
        if source in {"deadline", "the hollywood reporter"}:
            score += 14
        if source == "variety":
            score -= 8
        if source in {"billboard", "indiewire", "rolling stone", "thewrap"}:
            score += 14
        if source in {"ign", "polygon"}:
            score += 10

    if len(headline) > 30:
        score += 3

    if story.get("url", "#") != "#":
        score += 3

    if is_bad_public_story(story, site_slug):
        score -= 80

    return score


def balance_by_source(
    stories: list[dict[str, str]],
    site_slug: str,
    limit: int | None = None,
    min_target: int | None = None,
) -> list[dict[str, str]]:
    if limit is None:
        limit = len(stories)

    if min_target is None:
        min_target = MIN_TARGET_SECTIONS.get(site_slug, min(6, limit))

    if site_slug == "entertainment":
        return balance_entertainment_stories(stories, limit, min_target)

    if site_slug == "ai":
        # Reserve room for independent publishers before filling by rank.
        def publisher(story):
            return clean_text(story.get("source_name", "")) or source_name_from_url(story.get("source_feed", ""))
        seeds = []
        seen_sources = set()
        for story in stories:
            source = publisher(story)
            if source and source not in seen_sources and not story_is_duplicate_topic(story, seeds, site_slug):
                seeds.append(story)
                seen_sources.add(source)
            if len(seeds) >= min(3, limit):
                break
        stories = seeds + [story for story in stories if story not in seeds]

    source_cap = SOURCE_CAPS.get(site_slug, 3)
    selected: list[dict[str, str]] = []
    source_counts: dict[str, int] = defaultdict(int)
    source_cap_skips = 0
    duplicate_skips = 0

    for story in stories:
        source = clean_text(story.get("source_name", "")) or source_name_from_url(story.get("source_feed", ""))

        if story_is_duplicate_topic(story, selected, site_slug):
            duplicate_skips += 1
            continue

        if source_counts[source] >= source_cap:
            source_cap_skips += 1
            continue

        selected.append(story)
        source_counts[source] += 1

        if len(selected) >= limit:
            break

    if len(selected) < min_target:
        relaxed_cap = max(source_cap + 1, 4)

        for story in stories:
            if story in selected:
                continue

            source = clean_text(story.get("source_name", "")) or source_name_from_url(story.get("source_feed", ""))

            if story_is_duplicate_topic(story, selected, site_slug):
                duplicate_skips += 1
                continue

            if source_counts[source] >= relaxed_cap:
                source_cap_skips += 1
                continue

            selected.append(story)
            source_counts[source] += 1

            if len(selected) >= limit or len(selected) >= min_target:
                break

    if site_slug in {"ai", "politics", "entertainment"}:
        print(
            f"[BALANCE] {site_slug}: selected {len(selected)} | "
            f"source counts {dict(source_counts)} | "
            f"source-cap skips {source_cap_skips} | "
            f"duplicate/topic skips {duplicate_skips}"
        )

    return selected[:limit]


def diversify_by_source(stories: list[dict[str, str]], limit: int | None = None, site_slug: str = "") -> list[dict[str, str]]:
    if site_slug in {"ai", "politics", "entertainment"}:
        return balance_by_source(stories, site_slug, limit)

    preferred: list[dict[str, str]] = []
    source_seen: set[str] = set()

    for story in stories:
        source = clean_text(story.get("source_name", "")) or source_name_from_url(story.get("source_feed", ""))
        if source not in source_seen:
            preferred.append(story)
            source_seen.add(source)
        if limit is not None and len(preferred) >= limit:
            break

    if limit is None:
        limit = len(stories)

    if len(preferred) < limit:
        for story in stories:
            if story not in preferred:
                preferred.append(story)
            if len(preferred) >= limit:
                break

    return preferred[:limit]


def filter_and_rank_stories(stories: list[dict[str, str]], site_slug: str) -> list[dict[str, str]]:
    ranked: list[tuple[int, dict[str, str]]] = []

    for story in stories:
        if is_bad_public_story(story, site_slug):
            continue

        score = score_story(story, site_slug)

        if site_slug == "politics" and score < 25:
            continue

        if site_slug == "entertainment" and score < 18:
            continue

        story["editorial_score"] = str(score)
        story["headline"] = strip_public_labels(story.get("headline", ""))
        story["source_name"] = clean_text(story.get("source_name", "")) or source_name_from_url(story.get("source_feed", ""))
        ranked.append((score, story))

    ranked.sort(key=lambda x: x[0], reverse=True)
    sorted_stories = [story for _, story in ranked]

    if site_slug in {"ai", "politics", "entertainment"}:
        return balance_by_source(sorted_stories, site_slug, limit=len(sorted_stories))

    return sorted_stories


def newest_stories(stories: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(
        stories,
        key=lambda story: parse_story_datetime(story.get("published", "")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )


def urgent_stories(stories: list[dict[str, str]], site_slug: str) -> list[dict[str, str]]:
    return sorted(
        stories,
        key=lambda story: (
            breaking_score(story),
            score_story(story, site_slug),
            parse_story_datetime(story.get("published", "")) or datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )


def unique_take(
    stories: list[dict[str, str]],
    limit: int,
    used_keys: set[str] | None = None,
    site_slug: str = "",
) -> list[dict[str, str]]:
    if used_keys is None:
        used_keys = set()

    picked: list[dict[str, str]] = []

    for story in stories:
        key = normalize_key(story.get("headline", ""))
        if not key or key in used_keys:
            continue

        if site_slug and story_is_duplicate_topic(story, picked, site_slug):
            continue

        picked.append(story)
        used_keys.add(key)

        if len(picked) >= limit:
            break

    return picked


def extract_names(text: str) -> list[str]:
    candidates = re.findall(r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3}\b", text)
    banned = {
        "a", "all", "an", "arguably", "at", "after", "before", "breaking",
        "developing", "from", "global", "here", "how", "key", "new", "news",
        "official", "officials", "report", "that", "the", "these", "this", "those",
        "watch", "what", "when", "where", "why", "with", "monday", "tuesday",
        "wednesday", "thursday", "friday", "saturday", "sunday", "ai",
    }

    names = []
    for c in candidates:
        words = clean_text(c).split()
        while words and words[0].lower() in banned:
            words.pop(0)
        c = " ".join(words)
        if c and any(word.lower() not in banned for word in words) and c not in names:
            names.append(c)

    return names[:4]


def extract_political_entities(text: str) -> list[str]:
    """Return conservative political entities, not capitalized sentence openers."""
    entities = extract_names(text)
    validated_singletons = {
        "congress", "senate", "parliament", "nato", "eu", "un", "pentagon",
        "democrats", "republicans", "gop", "ukraine", "gaza", "israel", "iran",
        "china", "russia", "america", "trump", "biden",
    }
    result: list[str] = []
    for entity in entities:
        words = entity.split()
        if len(words) > 1:
            result.append(entity)
            continue
        token = words[0]
        occurrences = len(re.findall(rf"\b{re.escape(token)}\b", text, flags=re.IGNORECASE))
        if token.lower() in validated_singletons or occurrences >= 2:
            result.append(entity)
    return result[:4]


def extract_numbers(text: str) -> list[str]:
    nums = re.findall(
        r"\b\d+(?:\.\d+)?%?|\$\d+(?:\.\d+)?(?:\s?million|\s?billion|\s?M|\s?B)?\b",
        text,
        flags=re.I,
    )
    return list(dict.fromkeys(nums))[:4]


def story_focus(headline: str) -> str:
    h = strip_public_labels(headline)

    if ":" in h:
        return h.split(":", 1)[0].strip()
    if " - " in h:
        return h.split(" - ", 1)[0].strip()

    return smart_trim(h, 120)


def term_hits(text: str, terms: list[str]) -> list[str]:
    lower = clean_text(text).lower()
    hits: list[str] = []
    for term in terms:
        if term in lower and term not in hits:
            hits.append(term)
    return hits


def entertainment_topic(story: dict[str, str]) -> str:
    combined = clean_text(f"{story.get('headline', '')} {story.get('snapshot', '')}").lower()
    for topic in ENTERTAINMENT_TOPIC_ORDER:
        if any(term in combined for term in ENTERTAINMENT_TOPIC_KEYWORDS.get(topic, [])):
            return topic
    return "culture"


def entertainment_topic_counts(stories: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for story in stories:
        counts[entertainment_topic(story)] += 1
    return dict(counts)


def entertainment_source_limit(source: str, relaxed: bool = False) -> int:
    if clean_text(source).lower() == "variety":
        return ENTERTAINMENT_VARIETY_RELAXED_CAP if relaxed else ENTERTAINMENT_VARIETY_SOFT_CAP
    return SOURCE_CAPS["entertainment"] + (1 if relaxed else 0)


def entertainment_topic_limit(topic: str, relaxed: bool = False) -> int:
    if topic == "film":
        return ENTERTAINMENT_FILM_SOFT_CAP
    if topic in {"box_office", "production_labor"}:
        return 2
    return 2 + (1 if relaxed else 0)


def entertainment_story_allowed(
    story: dict[str, str],
    selected: list[dict[str, str]],
    source_counts: dict[str, int],
    topic_counts: dict[str, int],
    relaxed: bool = False,
) -> bool:
    source = clean_text(story.get("source_name", "")) or source_name_from_url(story.get("source_feed", ""))
    topic = entertainment_topic(story)

    if story_is_duplicate_topic(story, selected, "entertainment"):
        return False
    if source_counts[source] >= entertainment_source_limit(source, relaxed):
        return False
    if topic_counts[topic] >= entertainment_topic_limit(topic, relaxed):
        return False
    return True


def balance_entertainment_stories(
    stories: list[dict[str, str]],
    limit: int,
    min_target: int,
) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    source_counts: dict[str, int] = defaultdict(int)
    topic_counts: dict[str, int] = defaultdict(int)
    source_cap_skips = 0
    duplicate_or_topic_skips = 0

    def add_story(story: dict[str, str]) -> None:
        selected.append(story)
        source = clean_text(story.get("source_name", "")) or source_name_from_url(story.get("source_feed", ""))
        source_counts[source] += 1
        topic_counts[entertainment_topic(story)] += 1

    for topic in ENTERTAINMENT_TOPIC_ORDER:
        if len(selected) >= limit:
            break
        for story in stories:
            if story in selected or entertainment_topic(story) != topic:
                continue
            if entertainment_story_allowed(story, selected, source_counts, topic_counts):
                add_story(story)
                break

    for relaxed in (False, True):
        for story in stories:
            if len(selected) >= limit:
                break
            if story in selected:
                continue

            source = clean_text(story.get("source_name", "")) or source_name_from_url(story.get("source_feed", ""))
            topic = entertainment_topic(story)

            if story_is_duplicate_topic(story, selected, "entertainment"):
                duplicate_or_topic_skips += 1
                continue
            if source_counts[source] >= entertainment_source_limit(source, relaxed):
                source_cap_skips += 1
                continue
            if topic_counts[topic] >= entertainment_topic_limit(topic, relaxed):
                duplicate_or_topic_skips += 1
                continue

            add_story(story)

        if len(selected) >= min_target:
            break

    if len(selected) < min_target:
        for story in stories:
            if len(selected) >= min(limit, min_target):
                break
            if story in selected:
                continue
            if story_is_duplicate_topic(story, selected, "entertainment"):
                duplicate_or_topic_skips += 1
                continue
            source = clean_text(story.get("source_name", "")) or source_name_from_url(story.get("source_feed", ""))
            if clean_text(source).lower() == "variety" and source_counts[source] >= ENTERTAINMENT_VARIETY_RELAXED_CAP:
                source_cap_skips += 1
                continue
            add_story(story)

    print(
        f"[BALANCE] entertainment: selected {len(selected)} | "
        f"source counts {dict(source_counts)} | "
        f"topic counts {dict(topic_counts)} | "
        f"source-cap skips {source_cap_skips} | "
        f"duplicate/topic skips {duplicate_or_topic_skips}"
    )

    return selected[:limit]


def sentence_from_parts(parts: list[str], limit: int = 220) -> str:
    cleaned = [clean_text(part) for part in parts if clean_text(part)]
    if not cleaned:
        return ""
    return smart_trim(" ".join(cleaned), limit)


def make_key_data(site_slug: str, headline: str, snapshot: str) -> list[str]:
    combined = f"{headline}. {snapshot}"
    names = extract_political_entities(combined) if site_slug == "politics" else extract_names(combined)
    nums = extract_numbers(combined)
    lower = combined.lower()

    items: list[str] = []

    if names:
        items.append("Key people or organizations: " + ", ".join(names))

    if nums:
        items.append("Specific figures mentioned: " + ", ".join(nums))

    if site_slug == "ai":
        if hits := term_hits(lower, ["model", "llm", "agent", "chip", "nvidia", "data center", "enterprise", "regulation", "lawsuit", "funding"]):
            items.append("AI desk signal: " + ", ".join(hits[:4]))
        if any(x in lower for x in ["openai", "anthropic", "google", "microsoft", "meta", "nvidia", "amazon", "apple"]):
            items.append("Market context: major AI platform or infrastructure player involved")

    elif site_slug == "politics":
        if hits := term_hits(lower, ["congress", "senate", "house", "white house", "supreme court", "court", "election", "campaign", "budget", "immigration", "tariff", "ukraine", "gaza", "china"]):
            items.append("Politics desk signal: " + ", ".join(hits[:4]))
        if any(x in lower for x in ["bill", "vote", "hearing", "lawsuit", "judge", "sanctions", "policy"]):
            items.append("Institutional context: story may affect policy, legal pressure or governing leverage")

    elif site_slug == "entertainment":
        if hits := term_hits(lower, ["streaming", "box office", "netflix", "disney", "warner", "hbo", "max", "paramount", "music", "tour", "album", "gaming", "creator", "franchise"]):
            items.append("Entertainment business signal: " + ", ".join(hits[:4]))
        topic = entertainment_topic({"headline": headline, "snapshot": snapshot})
        if topic != "culture":
            items.append("Entertainment area: " + topic.replace("_", " "))
        if any(x in lower for x in ["ratings", "viewership", "audience", "box office", "streaming", "spotify", "youtube", "tiktok"]):
            items.append("Audience context: story connects to measurable attention, distribution or platform behavior")

    items.append("Story focus: " + story_focus(headline))

    if snapshot:
        items.append("Source context: " + smart_trim(snapshot, 150))

    return items[:5]


def make_contextual_snapshot(site_slug: str, headline: str, snapshot: str) -> str:
    base = clean_text(snapshot or headline)
    combined = f"{headline} {base}".lower()

    if not base:
        return smart_trim(headline, 260)

    generic_fragments = [
        "no stronger verified story cleared",
        "tracking configured feeds",
        "newsroom is tracking",
        "developments under review",
        "monitoring continues",
    ]

    if any(fragment in base.lower() for fragment in generic_fragments):
        base = headline

    if site_slug == "ai":
        if any(x in combined for x in ["chip", "nvidia", "semiconductor", "data center", "datacenter", "inference", "training"]):
            return smart_trim(
                f"{base} The larger angle is AI infrastructure: compute capacity, chip access and data-center economics are increasingly determining which companies can scale products for enterprise and government customers.",
                380,
            )
        if any(x in combined for x in ["lawsuit", "court", "regulation", "regulatory", "safety", "policy", "ban"]):
            return smart_trim(
                f"{base} The story matters because AI is moving deeper into legal and regulatory territory, where product speed, data rights, safety obligations and public accountability can affect adoption.",
                380,
            )
        if any(x in combined for x in ["model", "llm", "agent", "agents", "openai", "anthropic", "google", "microsoft", "meta", "gemini", "claude", "chatgpt"]):
            return smart_trim(
                f"{base} The competitive question is whether this changes the model race, enterprise integrations or customer lock-in as major AI providers battle for durable platform advantage.",
                380,
            )
        if any(x in combined for x in ["funding", "valuation", "startup", "acquisition", "merger"]):
            return smart_trim(
                f"{base} The business angle is capital allocation: investors and strategic buyers are still sorting which AI companies have real defensibility beyond headline momentum.",
                380,
            )

    if site_slug == "politics":
        if any(x in combined for x in ["supreme court", "court", "judge", "lawsuit", "justice department"]):
            return smart_trim(
                f"{base} The broader significance is institutional: court action can alter policy timelines, executive authority, legal precedent and the political incentives around the issue.",
                380,
            )
        if any(x in combined for x in ["congress", "senate", "house", "bill", "vote", "budget", "hearing"]):
            return smart_trim(
                f"{base} The key question is leverage: the next votes, negotiations and public pressure points will determine whether this becomes policy movement or political positioning.",
                380,
            )
        if any(x in combined for x in ["election", "campaign", "poll", "candidate", "trump", "biden"]):
            return smart_trim(
                f"{base} The election angle is whether this changes voter attention, campaign strategy or party messaging beyond the immediate news cycle.",
                380,
            )
        if any(x in combined for x in ["ukraine", "gaza", "israel", "iran", "china", "russia", "sanctions", "tariff"]):
            return smart_trim(
                f"{base} The geopolitical angle is how the decision affects alliances, economic pressure, security commitments and U.S. positioning abroad.",
                380,
            )

    if site_slug == "entertainment":
        if any(x in combined for x in ["streaming", "netflix", "disney", "warner", "hbo", "max", "paramount", "hulu", "peacock"]):
            return smart_trim(
                f"{base} The business read is whether the project can drive viewing, platform promotion, subscriber attention or franchise value.",
                380,
            )
        if any(x in combined for x in ["box office", "film", "movie", "franchise", "sequel", "reboot", "release"]):
            return smart_trim(
                f"{base} The studio read is whether audience attention can turn into box office, streaming value or a stronger franchise position.",
                380,
            )
        if any(x in combined for x in ["music", "album", "tour", "concert", "spotify", "billboard", "grammy"]):
            return smart_trim(
                f"{base} The music-business read is whether attention turns into chart movement, touring demand, streaming lift or stronger artist leverage.",
                380,
            )
        if any(x in combined for x in ["gaming", "video game", "playstation", "xbox", "nintendo", "ign", "polygon"]):
            return smart_trim(
                f"{base} The gaming read is whether fan interest turns into sales, subscriptions, platform engagement or long-term IP value.",
                380,
            )
        if any(x in combined for x in ["creator", "youtube", "tiktok", "influencer"]):
            return smart_trim(
                f"{base} The creator-economy angle is distribution power: talent, platforms and advertisers are still testing where audience loyalty turns into sustainable revenue.",
                380,
            )

    return smart_trim(base, 330)


def make_why_it_matters(site_slug: str, headline: str, snapshot: str) -> list[str]:
    combined = f"{headline} {snapshot}".lower()

    if site_slug == "ai":
        if any(x in combined for x in ["chip", "nvidia", "data center", "datacenter", "pentagon", "defense", "semiconductor", "inference", "training"]):
            return [
                "AI competition is increasingly being decided by infrastructure, not just product announcements.",
                "Compute supply, data-center capacity and institutional buyers can shape which companies actually scale.",
                "Editors should frame the story around power, procurement, capacity and durable competitive advantage.",
            ]
        if any(x in combined for x in ["regulation", "law", "lawsuit", "court", "policy", "safety", "ban", "copyright"]):
            return [
                "This shows AI moving from product hype into the legal and regulatory systems that can define its limits.",
                "The consequences may affect data rights, safety obligations, user trust and enterprise adoption.",
                "Editors should identify who gains leverage: companies, regulators, courts, creators, workers or customers.",
            ]
        if any(x in combined for x in ["model", "openai", "anthropic", "google", "microsoft", "meta", "launch", "release", "agent", "agents"]):
            return [
                "This affects the competitive race among major AI platforms, model providers and enterprise vendors.",
                "The key test is whether the move changes customer behavior, integration depth or platform lock-in.",
                "Editors should separate meaningful product movement from promotional AI noise.",
            ]
        if any(x in combined for x in ["funding", "valuation", "startup", "merger", "acquisition"]):
            return [
                "This is a capital-allocation story as the AI market separates durable businesses from momentum plays.",
                "Funding, valuation and acquisition signals can reveal where investors believe defensibility exists.",
                "Editors should connect the deal logic to revenue, infrastructure costs and enterprise demand.",
            ]
        return [
            "This belongs in the broader AI adoption story across business, labor, policy and technology infrastructure.",
            "The newsroom value is identifying whether the development changes behavior, budgets or institutional trust.",
            "Editors should separate real market movement from promotional noise.",
        ]

    if site_slug == "politics":
        if any(x in combined for x in ["supreme court", "court", "judge", "lawsuit", "justice department"]):
            return [
                "This has legal and institutional consequences beyond one news cycle.",
                "Court action can change policy timelines, executive authority, precedent and accountability pressure.",
                "Editors should frame the story around who gains power and who faces new limits.",
            ]
        if any(x in combined for x in ["congress", "senate", "house", "bill", "vote", "budget", "hearing"]):
            return [
                "This could affect legislative leverage, policy timing or party strategy.",
                "The practical question is whether the development changes votes, negotiations or public pressure.",
                "Editors should watch for the gap between messaging and actual governing outcomes.",
            ]
        if any(x in combined for x in ["election", "campaign", "poll", "candidate", "trump", "biden"]):
            return [
                "This may alter campaign incentives, voter attention or party messaging.",
                "The significance depends on whether it changes turnout, fundraising, coalition pressure or media focus.",
                "Editors should connect the story to the next measurable political test.",
            ]
        if any(x in combined for x in ["ukraine", "gaza", "israel", "iran", "china", "russia", "sanctions", "tariff"]):
            return [
                "This carries foreign-policy or economic consequences beyond the immediate political reaction.",
                "The story can affect alliances, security commitments, trade pressure or U.S. credibility abroad.",
                "Editors should watch official actions, not just statements.",
            ]
        return [
            "This affects the balance of power, policy debate or public trust.",
            "The newsroom should identify who gains leverage and who faces accountability.",
            "Editors should connect the story to the next governing, legal or electoral consequence.",
        ]

    if site_slug == "entertainment":
        if any(x in combined for x in ["netflix", "streaming", "disney", "warner", "hbo", "max", "paramount", "hulu", "peacock"]):
            return [
                "Streaming platforms are using franchises, live events and talent-driven projects to keep audiences inside their ecosystems.",
                "The next question is whether the story changes viewership, subscriber attention, pricing leverage or franchise value.",
                "The useful read is how the move affects audience demand, platform promotion and the business value of the property.",
            ]
        if any(x in combined for x in ["box office", "release", "film", "movie", "franchise", "sequel", "reboot", "remake"]):
            return [
                "This affects film release strategy, audience demand and studio positioning.",
                "The broader business question is whether attention can become theatrical revenue, streaming value or franchise momentum.",
                "Editors can connect the story to box office, distribution windows and cultural demand.",
            ]
        if any(x in combined for x in ["music", "album", "tour", "concert", "spotify", "billboard", "grammy"]):
            return [
                "This affects music industry momentum, artist leverage and audience attention.",
                "Streaming performance, touring demand and chart movement can determine whether the story has durable commercial impact.",
                "Editors should watch whether the story moves across touring, platforms, awards or fan communities.",
            ]
        if any(x in combined for x in ["gaming", "video game", "playstation", "xbox", "nintendo", "ign", "polygon"]):
            return [
                "This connects entertainment coverage to gaming culture, platform strategy and franchise economics.",
                "The key issue is whether fan attention translates into software sales, subscriptions or long-term IP value.",
                "Editors should track audience reaction and publisher/platform follow-through.",
            ]
        if any(x in combined for x in ["creator", "youtube", "tiktok", "influencer"]):
            return [
                "This story reflects the growing business power of creators and direct audience relationships.",
                "The important question is whether platform attention turns into durable revenue, brand leverage or distribution control.",
                "Editors should watch how advertisers, platforms and talent respond.",
            ]
        return [
            "This story sits at the intersection of culture, business and audience attention.",
            "The newsroom value is connecting the headline to distribution, monetization and fan behavior.",
            "Editors should watch whether it becomes a larger entertainment industry trend.",
        ]

    return ["This story may affect newsroom coverage priorities."]


def make_what_to_watch(site_slug: str, headline: str, snapshot: str) -> list[str]:
    combined = f"{headline} {snapshot}".lower()
    names = extract_political_entities(f"{headline}. {snapshot}") if site_slug == "politics" else extract_names(f"{headline}. {snapshot}")
    primary = names[0] if names else "the main source or organization"

    if site_slug == "ai":
        watch = [f"Watch for follow-up statements, product details or customer evidence from {primary}."]
        if any(x in combined for x in ["chip", "data center", "nvidia", "semiconductor"]):
            watch.append("Track whether the story changes compute capacity, cloud spending or supplier leverage.")
        elif any(x in combined for x in ["lawsuit", "regulation", "court", "policy", "safety"]):
            watch.append("Track court, regulator, creator, customer or enterprise responses.")
        elif any(x in combined for x in ["model", "agent", "launch", "release", "openai", "anthropic", "google", "microsoft"]):
            watch.append("Track whether competitors answer with pricing, product or integration changes.")
        else:
            watch.append("Track whether competitors, regulators or enterprise customers respond.")
        watch.append("Look for measurable adoption signals rather than promotional claims.")
        return watch[:3]

    if site_slug == "politics":
        watch = (
            [f"Watch for the next official action involving {primary}."]
            if names
            else ["Watch for the next verified action by the relevant government, court, agency or political organization."]
        )
        if any(x in combined for x in ["court", "judge", "lawsuit", "supreme court"]):
            watch.append("Track filings, rulings, appeals and agency responses.")
        elif any(x in combined for x in ["congress", "senate", "house", "bill", "vote"]):
            watch.append("Track vote counts, committee movement, leadership pressure and amendment fights.")
        elif any(x in combined for x in ["election", "campaign", "poll"]):
            watch.append("Track polling movement, fundraising, endorsements and turnout signals.")
        else:
            watch.append("Track responses from lawmakers, courts, agencies or campaigns.")
        watch.append("Separate official action from political messaging.")
        return watch[:3]

    if site_slug == "entertainment":
        watch = [f"Watch how audiences, platforms and talent respond to {primary}."]
        if any(x in combined for x in ["streaming", "netflix", "disney", "hbo", "max", "paramount"]):
            watch.append("Track viewership, renewals, cancellations, pricing moves and platform promotion.")
        elif any(x in combined for x in ["box office", "movie", "film", "release", "franchise"]):
            watch.append("Track box-office trajectory, release-window strategy and franchise momentum.")
        elif any(x in combined for x in ["music", "album", "tour", "concert", "spotify"]):
            watch.append("Track chart movement, streaming demand, ticket sales and award-cycle momentum.")
        elif any(x in combined for x in ["gaming", "playstation", "xbox", "nintendo", "video game"]):
            watch.append("Track fan reaction, platform strategy and publisher follow-through.")
        else:
            watch.append("Track whether the story develops into a larger box office, streaming, music, gaming or industry trend.")
        watch.append("Look for whether fan attention turns into measurable business impact.")
        return watch[:3]

    return ["Watch for verified follow-up developments."]


def make_editor_note(site_slug: str, headline: str, snapshot: str) -> str:
    combined = f"{headline} {snapshot}".lower()

    if breaking_score({"headline": headline, "snapshot": snapshot}) >= 12:
        if site_slug == "politics":
            return "Developing power-and-policy story; prioritize official actions, legal documents and institutional response."
        if site_slug == "ai":
            return "Developing AI industry story; prioritize primary company statements, filings, technical details and customer impact."
        if site_slug == "entertainment":
            return "Developing entertainment-industry story; prioritize trade-reporting confirmation, audience impact and business consequences."
        return "Developing story with elevated newsroom urgency."

    if site_slug == "ai":
        if any(x in combined for x in ["chip", "nvidia", "data center", "datacenter", "semiconductor"]):
            return "Infrastructure angle: compute capacity, supplier leverage and enterprise/government demand."
        if any(x in combined for x in ["model", "agent", "openai", "anthropic", "google", "microsoft", "meta"]):
            return "Platform competition angle: model capability, integration depth and customer lock-in."
        if any(x in combined for x in ["regulation", "lawsuit", "court", "policy", "copyright", "safety"]):
            return "Governance angle: legal exposure, safety obligations and adoption risk."
        return "AI adoption angle: separate verified business impact from product-cycle noise."

    if site_slug == "politics":
        if any(x in combined for x in ["court", "judge", "supreme court", "lawsuit"]):
            return "Institutional accountability angle: legal process, precedent and limits on power."
        if any(x in combined for x in ["congress", "senate", "house", "bill", "vote", "budget"]):
            return "Governing leverage angle: votes, negotiations, timing and policy consequences."
        if any(x in combined for x in ["election", "campaign", "poll", "candidate"]):
            return "Campaign leverage angle: voter attention, coalition pressure and message discipline."
        if any(x in combined for x in ["ukraine", "gaza", "israel", "iran", "china", "russia", "tariff", "sanctions"]):
            return "Geopolitical/economic angle: alliances, pressure points and policy follow-through."
        return "Power, policy or public-trust angle."

    if site_slug == "entertainment":
        if any(x in combined for x in ["box office", "film", "movie", "franchise", "sequel", "release"]):
            return "Studio economics angle: theatrical performance, IP value and distribution strategy."
        if any(x in combined for x in ["streaming", "studio", "netflix", "disney", "warner", "hbo", "max", "paramount"]):
            return "Streaming/business strategy angle: audience retention, platform leverage and franchise value."
        if any(x in combined for x in ["music", "album", "tour", "spotify", "billboard", "concert"]):
            return "Music business angle: audience momentum, platform performance and touring leverage."
        if any(x in combined for x in ["gaming", "video game", "playstation", "xbox", "nintendo"]):
            return "Gaming/IP angle: fan demand, platform strategy and long-term franchise economics."
        if any(x in combined for x in ["creator", "youtube", "tiktok", "influencer"]):
            return "Creator economy angle: distribution control, audience loyalty and monetization leverage."
        return "Culture-business angle: audience attention, distribution power and monetization."

    return "Monitor for follow-up reporting and broader trend connection."


def make_signal_headline(story: dict[str, str], site_slug: str) -> str:
    headline = strip_public_labels(story.get("headline", ""))
    return smart_trim(headline, 150)


def clean_snapshot_for_public(site_slug: str, headline: str, snapshot: str) -> str:
    cleaned = smart_trim(snapshot or headline, 280)
    lower = cleaned.lower()

    blocked_terms = [
        "newsroom monitoring continues",
        "the newsroom is monitoring",
        "monitoring major",
        "no higher-priority live lead",
        "no stronger verified story cleared",
        "overtaken the board",
        "developments under review",
        "tracking configured feeds",
    ]

    if any(term in lower for term in blocked_terms):
        cleaned = smart_trim(headline, 240)

    return make_contextual_snapshot(site_slug, headline, cleaned)


def enrich_story(story: dict[str, str], site_slug: str, signal_mode: bool = False) -> dict[str, Any]:
    raw_headline = strip_public_labels(story.get("headline", ""))
    headline = make_signal_headline(story, site_slug) if signal_mode else raw_headline
    headline = smart_trim(strip_public_labels(headline), 150)
    snapshot = clean_snapshot_for_public(site_slug, headline, story.get("snapshot", "") or raw_headline or headline)
    key_data = [clean_text(item) for item in make_key_data(site_slug, headline, snapshot)]

    if site_slug == "entertainment":
        raw_topic = entertainment_topic(story)
        key_data = [item for item in key_data if not item.lower().startswith("entertainment area:")]
        if raw_topic != "culture":
            insert_at = 1 if key_data else 0
            key_data.insert(insert_at, "Entertainment area: " + raw_topic.replace("_", " "))
        key_data = key_data[:5]

    return {
        "headline": clean_text(headline),
        "url": clean_text(story.get("url", "#")),
        "snapshot": clean_text(snapshot),
        "key_data": key_data,
        "why_it_matters": [clean_text(item) for item in make_why_it_matters(site_slug, headline, snapshot)],
        "what_to_watch": [clean_text(item) for item in make_what_to_watch(site_slug, headline, snapshot)],
        "editor_note": clean_text(make_editor_note(site_slug, headline, snapshot)),
        "source_feed": clean_text(story.get("source_feed", "")),
        "source_name": clean_text(story.get("source_name", "")) or source_name_from_url(story.get("source_feed", "")),
        "published": clean_text(story.get("published", "")),
        "age_hours": clean_text(story.get("age_hours", "")),
        "freshness_status": clean_text(story.get("freshness_status", "")),
        "editorial_score": clean_text(story.get("editorial_score", "0")),
        "urgency": clean_text(urgency_label(story)),
    }


def build_public_monitoring_story(site_slug: str, fallback_headline: str) -> dict[str, str]:
    if site_slug == "ai":
        snapshot = (
            "Global AI Report is tracking model releases, infrastructure moves, regulation, "
            "enterprise adoption and major company signals. No stronger verified story cleared "
            "the public lead threshold on this run."
        )
    elif site_slug == "politics":
        snapshot = (
            "Global Politics Report is tracking federal power, courts, campaigns, policy, "
            "Congress and international developments. No stronger verified story cleared "
            "the public lead threshold on this run."
        )
    elif site_slug == "entertainment":
        snapshot = (
            "Global Entertainment Report is tracking studios, streaming platforms, film, "
            "television, music, gaming, creators and audience behavior. No stronger verified "
            "story cleared the public lead threshold on this run."
        )
    else:
        snapshot = (
            "The newsroom is tracking configured feeds. No stronger verified story cleared "
            "the public lead threshold on this run."
        )

    return {
        "headline": fallback_headline,
        "url": "#",
        "snapshot": snapshot,
        "source_feed": "editorial-monitoring",
        "source_name": "Editorial Monitoring",
        "published": now_et(),
        "age_hours": "0.00",
        "freshness_status": "monitoring",
        "editorial_score": "0",
    }


def build_fallback_sections(
    site_slug: str,
    fallback_headline: str,
    ranked_fallback_stories: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    if ranked_fallback_stories:
        safe = [
            story for story in ranked_fallback_stories
            if int(story.get("editorial_score", "0") or "0") >= MIN_LEAD_SCORE.get(site_slug, 55)
        ]

        if site_slug in {"ai", "entertainment"} and not safe:
            safe = ranked_fallback_stories[:10]

        if safe:
            balanced_safe = balance_by_source(
                safe,
                site_slug,
                limit=MAX_SECTIONS.get(site_slug, 10),
                min_target=MIN_TARGET_SECTIONS.get(site_slug, 6),
            )
            return [enrich_story(story, site_slug) for story in balanced_safe]

    fallback = build_public_monitoring_story(site_slug, fallback_headline)
    return [enrich_story(fallback, site_slug)]


def build_spotlights(
    ranked_live_stories: list[dict[str, str]],
    ranked_editor_stories: list[dict[str, str]],
    site_slug: str,
) -> dict[str, list[dict[str, Any]]]:
    live_used: set[str] = set()
    editor_used: set[str] = set()

    live_candidates = urgent_stories(ranked_live_stories, site_slug)
    if not live_candidates:
        live_candidates = newest_stories(ranked_live_stories)

    live_candidates = balance_by_source(live_candidates, site_slug, limit=8, min_target=5)
    editor_candidates = balance_by_source(ranked_editor_stories, site_slug, limit=8, min_target=5)

    live_newsroom_raw = unique_take(live_candidates, 5, live_used, site_slug)
    editor_signals_raw = unique_take(editor_candidates, 5, editor_used, site_slug)

    return {
        "live_newsroom": [enrich_story(story, site_slug) for story in live_newsroom_raw],
        "editor_signals": [enrich_story(story, site_slug, signal_mode=True) for story in editor_signals_raw],
    }


def clean_report_text(report: dict[str, Any]) -> dict[str, Any]:
    report["headline"] = strip_public_labels(report.get("headline", ""))
    report["snapshot"] = clean_text(report.get("snapshot", ""))

    for field in ["live_newsroom", "editor_signals", "sections"]:
        cleaned_items = []
        for item in report.get(field, []):
            if isinstance(item, dict):
                cleaned_item = {}
                for key, value in item.items():
                    if isinstance(value, str):
                        cleaned_item[key] = strip_public_labels(value) if key == "headline" else clean_text(value)
                    elif isinstance(value, list):
                        cleaned_item[key] = [clean_text(v) if isinstance(v, str) else v for v in value]
                    else:
                        cleaned_item[key] = value
                cleaned_items.append(cleaned_item)
            else:
                cleaned_items.append(item)
        report[field] = cleaned_items

    report["key_storylines"] = [
        strip_public_labels(item) for item in report.get("key_storylines", [])
    ]

    return report


def valid_public_url(url: Any) -> bool:
    value = clean_text(url)
    return value.startswith(("http://", "https://"))


def generated_public_headline(headline: Any) -> bool:
    lower = clean_text(headline).lower()
    if not lower:
        return True
    generated_terms = [
        "ai signal:",
        "political signal:",
        "newsroom is tracking",
        "tracking configured feeds",
        "no stronger verified story cleared",
        "developments under review",
        "steady flow of",
        "desk tracks",
        "drive the newsroom watch",
    ]
    return any(term in lower for term in generated_terms)


def iter_public_cards(report: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    cards: list[tuple[str, dict[str, Any]]] = []
    for collection in ["sections", "live_newsroom", "editor_signals"]:
        value = report.get(collection)
        if not isinstance(value, list):
            continue
        for idx, item in enumerate(value):
            if isinstance(item, dict):
                cards.append((f"{collection}[{idx}]", item))
    return cards


def validate_public_headline_integrity(report: dict[str, Any], site_slug: str) -> dict[str, Any]:
    generated: list[dict[str, str]] = []
    fallback_or_stale: list[dict[str, str]] = []
    missing_links: list[dict[str, str]] = []
    empty_cards: list[dict[str, str]] = []

    for location, card in iter_public_cards(report):
        headline = strip_public_labels(card.get("headline", ""))
        url = clean_text(card.get("url", ""))
        freshness = clean_text(card.get("freshness_status", ""))
        row = {"location": location, "headline": headline, "url": url, "freshness_status": freshness}
        if not headline or not clean_text(card.get("snapshot", "")):
            empty_cards.append(row)
        if not valid_public_url(url):
            missing_links.append(row)
        if valid_public_url(url) and generated_public_headline(headline):
            generated.append(row)
        if freshness in {"stale", "monitoring"} or not valid_public_url(url) or generated_public_headline(headline):
            fallback_or_stale.append(row)

    headline = strip_public_labels(report.get("headline", ""))
    top_level_generated = bool(generated_public_headline(headline) and report.get("sections"))

    validation = {
        "site": site_slug,
        "cards_checked": len(iter_public_cards(report)),
        "generated_public_headlines": generated,
        "fallback_or_stale_cards": fallback_or_stale,
        "missing_or_invalid_links": missing_links,
        "empty_cards": empty_cards,
        "top_level_generated_headline": top_level_generated,
        "passed": (
            not generated
            and not fallback_or_stale
            and not missing_links
            and not empty_cards
            and not top_level_generated
        ),
    }
    print(
        f"[HEADLINE_INTEGRITY] {site_slug}: "
        f"passed={validation['passed']} checked={validation['cards_checked']} "
        f"generated={len(generated)} fallback_or_stale={len(fallback_or_stale)} "
        f"missing_links={len(missing_links)} empty={len(empty_cards)}"
    )
    return validation


def source_count_summary(stories: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for story in stories:
        source = clean_text(story.get("source_name", "")) or source_name_from_url(story.get("source_feed", ""))
        counts[source] += 1
    return dict(counts)


def build_report(site_name: str, config: dict[str, Any]) -> dict[str, Any]:
    fetched_stories: list[dict[str, str]] = []
    feed_counts: dict[str, int] = {}

    for feed in config["feeds"]:
        try:
            xml_text = fetch_url(feed)
            parsed = parse_feed(xml_text, feed)
            fetched_stories.extend(parsed)
            source_label = source_name_from_url(feed)
            feed_counts[source_label] = feed_counts.get(source_label, 0) + len(parsed)
            print(f"[FEED] {site_name}: {len(parsed)} stories from {feed}")
            time.sleep(0.4)
        except Exception as exc:
            print(f"[WARN] {site_name} feed failed: {feed} | {exc}")

    print(f"[FEED_COUNTS] {site_name}: {feed_counts}")

    deduped_stories = dedupe_stories(fetched_stories, config["slug"])

    fresh_live_stories = [
        story for story in deduped_stories
        if story_is_fresh(story, MAX_LIVE_STORY_AGE_HOURS)
    ]

    fresh_editor_stories = [
        story for story in deduped_stories
        if story_is_fresh(story, MAX_EDITOR_STORY_AGE_HOURS)
    ]

    public_fallback_stories = [
        story for story in deduped_stories
        if story_is_fresh(story, MAX_PUBLIC_FALLBACK_AGE_HOURS)
    ]

    stale_count = max(0, len(deduped_stories) - len(fresh_live_stories))
    unknown_count = sum(1 for story in deduped_stories if story_age_hours(story) is None)

    print(
        f"[FRESHNESS] {site_name}: "
        f"{len(deduped_stories)} total | "
        f"{len(fresh_live_stories)} live-fresh <= {MAX_LIVE_STORY_AGE_HOURS}h | "
        f"{len(fresh_editor_stories)} editor-fresh <= {MAX_EDITOR_STORY_AGE_HOURS}h | "
        f"{len(public_fallback_stories)} public-fallback <= {MAX_PUBLIC_FALLBACK_AGE_HOURS}h | "
        f"{stale_count} stale/blocked | "
        f"{unknown_count} unknown-date"
    )

    ranked_live_stories = filter_and_rank_stories(fresh_live_stories, config["slug"])
    ranked_editor_stories = filter_and_rank_stories(fresh_editor_stories, config["slug"])
    ranked_public_fallback_stories = filter_and_rank_stories(public_fallback_stories, config["slug"])

    safe_live_leads = [
        story for story in ranked_live_stories
        if int(story.get("editorial_score", "0") or "0") >= MIN_LEAD_SCORE.get(config["slug"], 55)
    ]

    if config["slug"] == "ai" and not safe_live_leads and ranked_live_stories:
        safe_live_leads = ranked_live_stories[:6]

    if config["slug"] == "entertainment" and not safe_live_leads and ranked_live_stories:
        safe_live_leads = ranked_live_stories[:6]

    if not safe_live_leads:
        fallback_pool = ranked_editor_stories or ranked_public_fallback_stories

        if config["slug"] in {"ai", "entertainment"} and not fallback_pool:
            fallback_pool = filter_and_rank_stories(deduped_stories, config["slug"])

        sections = build_fallback_sections(
            config["slug"],
            config["fallback_headline"],
            fallback_pool,
        )

        if fallback_pool and sections and sections[0].get("url") != "#":
            spotlights = build_spotlights(fallback_pool, fallback_pool, config["slug"])
            print(f"[FALLBACK] {site_name}: Public lead selected from vetted recent story pool")
        else:
            spotlights = {
                "live_newsroom": sections[:1],
                "editor_signals": [],
            }
            print(f"[FALLBACK] {site_name}: Public monitoring fallback used")

    else:
        diversified_leads = balance_by_source(
            safe_live_leads,
            config["slug"],
            limit=MAX_SECTIONS.get(config["slug"], 10),
            min_target=MIN_TARGET_SECTIONS.get(config["slug"], 6),
        )

        if len(diversified_leads) < MIN_TARGET_SECTIONS.get(config["slug"], 6):
            refill_pool = ranked_editor_stories or ranked_public_fallback_stories
            for story in refill_pool:
                if story in diversified_leads:
                    continue
                if story_is_duplicate_topic(story, diversified_leads, config["slug"]):
                    continue
                diversified_leads.append(story)
                if len(diversified_leads) >= MIN_TARGET_SECTIONS.get(config["slug"], 6):
                    break

        diversified_leads = balance_by_source(
            diversified_leads,
            config["slug"],
            limit=MAX_SECTIONS.get(config["slug"], 10),
            min_target=MIN_TARGET_SECTIONS.get(config["slug"], 6),
        )

        sections = [enrich_story(story, config["slug"]) for story in diversified_leads]
        spotlights = build_spotlights(diversified_leads, ranked_editor_stories, config["slug"])

    if config["slug"] == "ai":
        def publisher(story):
            return clean_text(story.get("source_name", "")) or source_name_from_url(story.get("source_feed", ""))
        present = {publisher(story) for story in sections if publisher(story)}
        for story in ranked_editor_stories:
            if len(present) >= 3:
                break
            source = publisher(story)
            if source and source not in present and not story_is_duplicate_topic(story, sections, "ai"):
                # Retain original source text, publication date and lead.
                if len(sections) >= MAX_SECTIONS["ai"]:
                    counts = defaultdict(int)
                    for card in sections:
                        counts[publisher(card)] += 1
                    index = next(
                        (i for i in range(len(sections)-1, 0, -1)
                         if counts[publisher(sections[i])] > 1),
                        None,
                    )
                    if index is None:
                        continue
                    sections.pop(index)
                sections.append(enrich_story(story, "ai"))
                present = {publisher(card) for card in sections if publisher(card)}
        if len(present) < 3:
            raise RuntimeError(
                "AI generation has fewer than three qualifying sources: "
                + repr(sorted(present))
            )

    lead = sections[0]

    print(
        f"[SELECTED] {site_name}: sections={len(sections)} | "
        f"live={len(spotlights['live_newsroom'])} | "
        f"editor={len(spotlights['editor_signals'])} | "
        f"sources={source_count_summary([s for s in ranked_live_stories if s.get('headline') in [x.get('headline') for x in sections]])}"
    )

    report = {
        "site": clean_text(site_name),
        "vertical": clean_text(config["accent"]),
        "headline": strip_public_labels(lead["headline"]),
        "snapshot": clean_text(lead["snapshot"]),
        "updated_at": now_et(),
        "generated_at": now_et(),
        "video_url": clean_text(config["video_url"]),
        "freshness": {
            "max_live_story_age_hours": MAX_LIVE_STORY_AGE_HOURS,
            "max_editor_story_age_hours": MAX_EDITOR_STORY_AGE_HOURS,
            "max_public_fallback_age_hours": MAX_PUBLIC_FALLBACK_AGE_HOURS,
            "total_items_checked": len(deduped_stories),
            "live_fresh_items": len(fresh_live_stories),
            "editor_fresh_items": len(fresh_editor_stories),
            "public_fallback_items": len(public_fallback_stories),
            "stale_or_blocked_items": stale_count,
            "unknown_date_items": unknown_count,
            "last_checked": now_et(),
        },
        "live_newsroom": spotlights["live_newsroom"],
        "editor_signals": spotlights["editor_signals"],
        "key_storylines": [strip_public_labels(s["headline"]) for s in sections[:3]],
        "sections": sections,
        "editorial_brain": {
            "status": "active",
            "version": "v4.0-cross-vertical-editorial-intelligence",
            "language_upgrade": "active",
            "placeholder_guard": "active",
            "contextual_snapshot_engine": "active",
            "vertical_analysis_modes": {
                "ai": "enterprise, infrastructure, model competition, regulation and capital allocation",
                "politics": "policy, institutional power, courts, elections, geopolitics and governing consequences",
                "entertainment": "streaming strategy, studio economics, music business, gaming IP and creator economy",
            },
        },
        "schema": {
            "version": "gsr-network-v4.0-cross-vertical-editorial-intelligence",
            "required_story_fields": [
                "headline",
                "url",
                "snapshot",
                "key_data",
                "why_it_matters",
                "what_to_watch",
                "editor_note",
                "urgency",
                "published",
                "age_hours",
                "freshness_status",
                "source_name",
            ],
            "spotlight_fields": [
                "live_newsroom",
                "editor_signals",
            ],
            "editorial_guards": [
                "AI public lead should use a real vetted story whenever available",
                "Monitoring language is blocked from normal public snapshots",
                "Source diversity guard prevents one feed from dominating the page",
                "Authority scoring favors major AI companies, models, infrastructure, policy and enterprise movement",
                "Entertainment scoring favors recognizable studios, platforms, talent, box office, streaming, music, gaming and creator-economy signals",
                "Entertainment fallback language is blocked from normal public leads when verified stories exist",
                "Topic deduplication prevents repeated stories from filling the same public page",
                "Minimum-card logic attempts to fill each vertical with a healthy newsroom mix when enough vetted stories exist",
                "Cross-vertical editorial intelligence adds business, policy, market, audience and institutional context",
                "AI cards emphasize infrastructure, model competition, regulation, capital allocation and enterprise impact",
                "Politics cards emphasize power, policy, courts, elections, geopolitics and governing consequences",
                "Entertainment cards emphasize streaming strategy, studio economics, music business, gaming IP and creator-economy signals",
                "Public snapshots are expanded into contextual newsroom analysis when source text is too thin or mechanical",
            ],
        },
    }

    report = apply_breaking_overrides(report, config["slug"])
    report = clean_report_text(report)

    return report


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str] | tuple[str, ...] = ()) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--vertical",
        action="append",
        choices=tuple(config["slug"] for config in SITES.values()),
        help="Generate only the selected vertical; may be repeated.",
    )
    args = parser.parse_args(list(argv))
    selected_verticals = set(args.vertical or ())

    print(f"[START] GSR Network Content Engine | {now_et()}")

    ROOT = Path(r"C:\Users\joeru\OneDrive\Desktop")

    DESTINATIONS = {
        "ai": ROOT / "global-ai-report-web" / "public" / "latest_report.json",
        "politics": ROOT / "global-politics-report-web" / "public" / "latest_report.json",
        "entertainment": ROOT / "global-entertainment-report-web" / "public" / "latest_report.json",
    }

    for site_name, config in SITES.items():
        if selected_verticals and config["slug"] not in selected_verticals:
            continue
        print(f"[RUN] {site_name}")
        report = build_report(site_name, config)
        validation = validate_public_headline_integrity(report, config["slug"])
        if not validation["passed"]:
            raise RuntimeError(
                f"{site_name} failed public content validation; refusing to overwrite published output"
            )

        write_json(config["output"], report)
        print(f"[OK] Wrote {config['output']}")

        slug = config["slug"]
        if slug in DESTINATIONS:
            dest_path = DESTINATIONS[slug]
            write_json(dest_path, report)
            print(f"[SYNC] Updated {dest_path}")

        print(f"[HEADLINE] {report['headline']}")
        print(f"[SPOTLIGHT] Live: {len(report['live_newsroom'])} | Editor: {len(report['editor_signals'])}")

    print("[DONE] Cross-vertical editorial intelligence active")
    print("[DONE] AI enterprise/infrastructure analysis active")
    print("[DONE] Politics policy/institutional analysis active")
    print("[DONE] Entertainment business/audience analysis active")
    print("[DONE] Contextual snapshot expansion active")
    print(f"[DONE] GSR Network Content Engine | {now_et()}")


if __name__ == "__main__":
    main()


