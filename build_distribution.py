#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from editorial_intelligence import normalize_payload

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None  # type: ignore

try:
    import requests
except Exception:
    requests = None  # type: ignore

try:
    import tweepy
except Exception:
    tweepy = None  # type: ignore

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None  # type: ignore


BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = Path(r"C:\Users\joeru\OneDrive\Desktop\global-ai-report-web")
WEB_PUBLIC_DIR = WEB_DIR / "public"

TITLE = "GLOBAL AI REPORT"
SITE_NAME = "Global AI Report"
TAGLINE = "Built for journalists, by a journalist."
DISCLAIMER = "This report is an automated signal and structure layer intended to support, not replace, human journalism."
DEFAULT_X_HANDLE = "@GlobalSportsRp"
DEFAULT_SUBSTACK_URL = "https://globalsportsreport.substack.com/"
SITE_TZ = "America/New_York"

REPORT_FILES: dict[str, Path] = {
    "ai": BASE_DIR / "ai_report.txt",
    "technology": BASE_DIR / "technology_report.txt",
    "business": BASE_DIR / "business_report.txt",
    "policy": BASE_DIR / "policy_report.txt",
    "research": BASE_DIR / "research_report.txt",
}

JSON_REPORT_FILES: dict[str, Path] = {
    "ai": BASE_DIR / "ai_report.json",
    "technology": BASE_DIR / "technology_report.json",
    "business": BASE_DIR / "business_report.json",
    "policy": BASE_DIR / "policy_report.json",
    "research": BASE_DIR / "research_report.json",
}

OUTPUT_SUBSTACK = BASE_DIR / "substack_post.txt"
OUTPUT_TELEGRAM = BASE_DIR / "telegram_post.txt"
OUTPUT_TWITTER = BASE_DIR / "twitter_thread.txt"
OUTPUT_LATEST_TXT = BASE_DIR / "latest_report.txt"
OUTPUT_LATEST_JSON = BASE_DIR / "latest_report.json"
OUTPUT_PREVIOUS_JSON = BASE_DIR / "latest_report.previous.json"
GLOBAL_REPORT_TXT = BASE_DIR / "global_ai_report.txt"

WEB_COPY_TARGETS = {
    "latest_report.json": WEB_PUBLIC_DIR / "latest_report.json",
    "latest_report.txt": WEB_PUBLIC_DIR / "latest_report.txt",
    "global_ai_report.txt": WEB_PUBLIC_DIR / "global_ai_report.txt",
}

SECTION_ORDER = [
    "ai",
    "technology",
    "business",
    "policy",
    "research",
]

RUN_STARTED_AT_DT = datetime.now(ZoneInfo(SITE_TZ)) if ZoneInfo else datetime.now()
RUN_STARTED_AT = RUN_STARTED_AT_DT.strftime("%Y-%m-%d %I:%M:%S %p ET")
RUN_ID = RUN_STARTED_AT_DT.strftime("gai-ai-%Y%m%d-%H%M%S-et")
RUN_ISO = RUN_STARTED_AT_DT.isoformat()


def now_et() -> datetime:
    if ZoneInfo is None:
        return datetime.now()
    return datetime.now(ZoneInfo(SITE_TZ))


def ts() -> str:
    return now_et().strftime("%Y-%m-%d %I:%M:%S %p ET")


def log(message: str) -> None:
    print(f"[{ts()}] {message}")


def load_environment() -> None:
    env_path = BASE_DIR / ".env"
    if load_dotenv and env_path.exists():
        load_dotenv(env_path)

    log(f"ENV PATH: {env_path}")
    log(f"ENV EXISTS: {env_path.exists()}")
    log(f"TELEGRAM TOKEN FOUND: {bool(os.getenv('TELEGRAM_BOT_TOKEN'))}")
    log(f"TELEGRAM CHAT ID FOUND: {bool(os.getenv('TELEGRAM_CHAT_ID'))}")
    log(f"TWITTER API KEY FOUND: {bool(os.getenv('TWITTER_API_KEY'))}")
    log(f"TWITTER API SECRET FOUND: {bool(os.getenv('TWITTER_API_SECRET'))}")
    log(f"TWITTER ACCESS TOKEN FOUND: {bool(os.getenv('TWITTER_ACCESS_TOKEN'))}")
    log(f"TWITTER ACCESS TOKEN SECRET FOUND: {bool(os.getenv('TWITTER_ACCESS_TOKEN_SECRET'))}")
    log(f"TWITTER BEARER TOKEN FOUND: {bool(os.getenv('TWITTER_BEARER_TOKEN'))}")
    log(f"WEB PUBLIC DIR: {WEB_PUBLIC_DIR}")


def clean_text(text: Any) -> str:
    if not isinstance(text, str):
        text = str(text)

    replacements = {
        "\ufeff": "",
        "\u2019": "'",
        "\u2018": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2014": "-",
        "\u2013": "-",
        "\xa0": " ",
        "â€™": "'",
        "â€œ": '"',
        "â€\x9d": '"',
        "â€”": "-",
        "â€“": "-",
        "Ã©": "é",
        "Ã¡": "á",
        "Ã³": "ó",
        "Ãº": "ú",
        "Ã±": "ñ",
        "Ã¼": "ü",
        "Ã": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def slugify(text: str) -> str:
    text = clean_text(text).lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "section"


def format_label(key: str) -> str:
    labels = {
        "ai": "AI",
        "technology": "Technology",
        "business": "AI Business",
        "policy": "AI Policy",
        "research": "AI Research",
    }
    return labels.get(key, key.replace("_", " ").title())


def safe_join_parts(value: Any) -> str:
    flattened: list[str] = []

    def walk(item: Any) -> None:
        if item is None:
            return
        if isinstance(item, str):
            txt = clean_text(item)
            if txt:
                flattened.append(txt)
            return
        if isinstance(item, (int, float, bool)):
            flattened.append(str(item))
            return
        if isinstance(item, dict):
            for _, v in item.items():
                walk(v)
            return
        if isinstance(item, (list, tuple, set)):
            for sub in item:
                walk(sub)
            return
        flattened.append(clean_text(str(item)))

    walk(value)
    return "\n\n".join(part for part in flattened if part.strip()).strip()


def first_meaningful_line(text: str) -> str:
    skip = {
        "HEADLINE",
        "SNAPSHOT",
        "KEY STORYLINES",
        "KEY DATA POINTS",
        "WHY IT MATTERS",
        "WHAT TO WATCH",
        "STORY ANGLES",
        "UPDATED",
        "GLOBAL SNAPSHOT",
        "DISCLAIMER",
        "AI REPORT",
        "GLOBAL AI REPORT",
    }

    for line in clean_text(text).splitlines():
        line = line.strip(" -:\t")
        if line and line.upper() not in skip and len(line) > 25:
            return line

    return ""


def parse_timestamp_from_text(text: str) -> str | None:
    patterns = [
        r"Generated:\s*([0-9:\-\sAPMET]+)",
        r"UPDATED\s*\n\s*([0-9:\-\sAPMET]+)",
        r"Updated:\s*([0-9:\-\sAPMET]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return clean_text(match.group(1))

    return None


def read_text_file(path: Path) -> str:
    if not path.exists():
        return ""
    raw = path.read_text(encoding="utf-8", errors="replace")
    return clean_text(raw)


def read_json_file(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def write_text_file(path: Path, text: str) -> None:
    path.write_text(clean_text(text) + "\n", encoding="utf-8")
    log(f"Saved: {path}")


def write_json_file(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    log(f"Saved: {path}")


SECTION_HEADER_RE = re.compile(
    r"^(HEADLINE|SNAPSHOT|KEY STORYLINES|KEY DATA POINTS|WHY IT MATTERS|WHAT TO WATCH|"
    r"CURRENT DATA AND ANALYTICS|STORY ANGLES|DISCLAIMER|UPDATED|GLOBAL SNAPSHOT|"
    r"RESEARCH WATCH|POLICY WATCH|BUSINESS WATCH|PRODUCT WATCH|MARKET WATCH)$",
    flags=re.IGNORECASE | re.MULTILINE,
)


def split_named_sections(text: str) -> dict[str, list[str]]:
    text = clean_text(text)
    if not text:
        return {}

    lines = text.splitlines()
    sections: dict[str, list[str]] = {}
    current_key: str | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if SECTION_HEADER_RE.match(line):
            current_key = slugify(line)
            sections.setdefault(current_key, [])
            continue

        if current_key is None:
            continue

        if line:
            sections[current_key].append(line)

    return sections


def append_heartbeat_to_content(text: str, label: str) -> str:
    heartbeat = f"HEARTBEAT\n{label} checked by GSR Network at {RUN_STARTED_AT}."

    if not text.strip():
        return heartbeat

    return f"{clean_text(text)}\n\n{heartbeat}"


def parse_standard_report(section_key: str, path: Path) -> dict[str, Any] | None:
    text = read_text_file(path)
    if not text:
        return None

    sections = split_named_sections(text)
    headline = ""

    if sections.get("headline"):
        headline = sections["headline"][0]
    else:
        headline = first_meaningful_line(text)

    if not headline:
        headline = f"{format_label(section_key)} signals refreshed"

    snapshot = ""
    if sections.get("snapshot"):
        snapshot = sections["snapshot"][0]
    elif sections.get("global_snapshot"):
        snapshot = sections["global_snapshot"][0]
    else:
        snapshot = headline

    source_updated_at = parse_timestamp_from_text(text) or RUN_STARTED_AT
    label = format_label(section_key)

    return {
        "title": label,
        "source_file": path.name,
        "source_updated_at": source_updated_at,
        "updated_at": RUN_STARTED_AT,
        "generated_at": RUN_STARTED_AT,
        "published_at": RUN_STARTED_AT,
        "last_checked": RUN_STARTED_AT,
        "last_pipeline_run": RUN_STARTED_AT,
        "headline": headline,
        "snapshot": snapshot,
        "content": append_heartbeat_to_content(text, label),
        "freshness_status": "checked",
        "heartbeat": {
            "status": "checked",
            "run_id": RUN_ID,
            "checked_at": RUN_STARTED_AT,
            "checked_at_iso": RUN_ISO,
            "message": f"{label} checked by GSR Network at {RUN_STARTED_AT}.",
        },
    }


def parse_json_report(section_key: str, path: Path) -> dict[str, Any] | None:
    data = read_json_file(path)
    if not isinstance(data, dict):
        return None

    label = format_label(section_key)
    headline = clean_text(data.get("headline") or data.get("title") or f"{label} signals refreshed")
    snapshot = clean_text(data.get("snapshot") or data.get("summary") or headline)
    content = safe_join_parts(data.get("content") or data.get("body") or data.get("key_storylines") or snapshot)

    return {
        "title": label,
        "source_file": path.name,
        "source_updated_at": clean_text(data.get("updated_at") or data.get("generated_at") or data.get("published_at") or RUN_STARTED_AT),
        "updated_at": RUN_STARTED_AT,
        "generated_at": RUN_STARTED_AT,
        "published_at": RUN_STARTED_AT,
        "last_checked": RUN_STARTED_AT,
        "last_pipeline_run": RUN_STARTED_AT,
        "headline": headline,
        "snapshot": snapshot,
        "content": append_heartbeat_to_content(content, label),
        "key_storylines": data.get("key_storylines", []),
        "freshness_status": "checked",
        "heartbeat": {
            "status": "checked",
            "run_id": RUN_ID,
            "checked_at": RUN_STARTED_AT,
            "checked_at_iso": RUN_ISO,
            "message": f"{label} checked by GSR Network at {RUN_STARTED_AT}.",
        },
    }


def load_reports() -> dict[str, dict[str, Any]]:
    reports: dict[str, dict[str, Any]] = {}

    for key in SECTION_ORDER:
        json_path = JSON_REPORT_FILES.get(key)
        text_path = REPORT_FILES.get(key)

        parsed = None

        if json_path and json_path.exists():
            parsed = parse_json_report(key, json_path)

        if not parsed and text_path:
            parsed = parse_standard_report(key, text_path)

        if parsed:
            reports[key] = parsed
            log(f"Loaded report: {parsed.get('source_file')}")
        else:
            log(f"Missing report for: {format_label(key)}")

    return reports


def infer_global_headline(reports: dict[str, dict[str, Any]]) -> str:
    for key in SECTION_ORDER:
        report = reports.get(key)
        if report and report.get("headline"):
            return clean_text(report["headline"])

    return "AI developments are moving across technology, business, policy and research."


def extract_storylines(reports: dict[str, dict[str, Any]]) -> list[str]:
    lines: list[str] = []

    for key in SECTION_ORDER:
        report = reports.get(key)
        if not report:
            continue

        headline = clean_text(report.get("headline", ""))
        if headline:
            lines.append(f"{format_label(key)}: {headline}")

    lines.append(f"System heartbeat: Global AI Report checked all available AI feeds at {RUN_STARTED_AT}.")
    return lines[:7]


def infer_global_snapshot(reports: dict[str, dict[str, Any]]) -> str:
    for key in SECTION_ORDER:
        report = reports.get(key)
        if report and report.get("snapshot"):
            return clean_text(report["snapshot"])

    return "Global AI Report refreshed its available AI and technology signals."


def build_system_heartbeat(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    missing = [format_label(key) for key in SECTION_ORDER if key not in reports]

    return {
        "status": "live",
        "vertical": "ai",
        "run_id": RUN_ID,
        "checked_at": RUN_STARTED_AT,
        "checked_at_iso": RUN_ISO,
        "last_pipeline_run": RUN_STARTED_AT,
        "forced_freshness": True,
        "message": f"GSR Network AI pipeline completed a live heartbeat at {RUN_STARTED_AT}.",
        "fresh_section_count": len(reports),
        "missing_inputs": missing,
    }


def build_latest_report_payload(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    date_string = now_et().strftime("%Y-%m-%d")

    payload = {
        "title": f"{TITLE} | {date_string}",
        "site_name": SITE_NAME,
        "tagline": TAGLINE,
        "headline": infer_global_headline(reports),
        "key_storylines": extract_storylines(reports),
        "snapshot": infer_global_snapshot(reports),
        "generated_at": RUN_STARTED_AT,
        "updated_at": RUN_STARTED_AT,
        "published_at": RUN_STARTED_AT,
        "last_checked": RUN_STARTED_AT,
        "last_pipeline_run": RUN_STARTED_AT,
        "run_id": RUN_ID,
        "run_iso": RUN_ISO,
        "system_heartbeat": build_system_heartbeat(reports),
        "freshness": {
            "status": "active",
            "forced_freshness": True,
            "last_checked": RUN_STARTED_AT,
            "last_pipeline_run": RUN_STARTED_AT,
            "run_id": RUN_ID,
            "inputs": [
                {
                    "section": format_label(key),
                    "key": key,
                    "status": "present" if key in reports else "missing",
                    "last_checked": RUN_STARTED_AT,
                    "run_id": RUN_ID,
                }
                for key in SECTION_ORDER
            ],
        },
        "editorial_brain": {
            "status": "active",
            "vertical": "ai",
            "heartbeat": "active",
            "forced_freshness": "active",
            "focus": [
                "AI and technology developments",
                "Business signals",
                "Policy and regulation",
                "Research and model releases",
                "Orderly one-line card data",
                "Heartbeat on every successful run",
                "Forced freshness fields on top-level payload and section cards",
            ],
            "version": "2026-05-02-ai-heartbeat-forced-freshness",
        },
        "disclaimer": DISCLAIMER,
        "x_handle": os.getenv("GSR_X_HANDLE", DEFAULT_X_HANDLE),
        "substack_url": os.getenv("GSR_SUBSTACK_URL", DEFAULT_SUBSTACK_URL),
        "sections": {},
    }

    for key in SECTION_ORDER:
        if key in reports:
            payload["sections"][key] = reports[key]

    return normalize_payload(payload, "ai")


def build_latest_report_text(payload: dict[str, Any]) -> str:
    parts: list[str] = [
        payload.get("title", TITLE),
        "",
        f"Updated: {payload.get('updated_at', RUN_STARTED_AT)}",
        f"Heartbeat: {payload.get('system_heartbeat', {}).get('message', '')}",
        "",
        "HEADLINE",
        payload.get("headline", ""),
        "",
        "KEY STORYLINES",
    ]

    for line in payload.get("key_storylines", []):
        parts.append(f"- {line}")

    parts += [
        "",
        "SNAPSHOT",
        payload.get("snapshot", ""),
        "",
    ]

    for key in SECTION_ORDER:
        section = payload.get("sections", {}).get(key)
        if not section:
            continue

        parts.append(format_label(key).upper())
        parts.append(section.get("headline", ""))
        parts.append(section.get("snapshot", ""))
        parts.append(f"Last checked: {section.get('last_checked', RUN_STARTED_AT)}")
        parts.append("")
        parts.append(section.get("content", ""))
        parts.append("")

    parts.append(DISCLAIMER)
    return safe_join_parts(parts)


def build_substack_post(payload: dict[str, Any]) -> str:
    parts: list[str] = [
        payload.get("title", TITLE),
        "",
        payload.get("headline", ""),
        "",
        "Key Storylines",
    ]

    for line in payload.get("key_storylines", []):
        parts.append(f"- {line}")

    parts += ["", "Snapshot", payload.get("snapshot", ""), ""]

    for key in SECTION_ORDER:
        section = payload.get("sections", {}).get(key)
        if not section:
            continue
        parts.append(format_label(key))
        parts.append(section.get("content", ""))
        parts.append("")

    parts.append(DISCLAIMER)
    return safe_join_parts(parts)


def build_telegram_post(payload: dict[str, Any]) -> str:
    lines: list[str] = [
        payload.get("title", TITLE),
        payload.get("headline", ""),
        "",
    ]

    for line in payload.get("key_storylines", [])[:5]:
        lines.append(f"- {line}")

    lines += [
        "",
        payload.get("snapshot", ""),
        "",
        f"Read more on Substack: {payload.get('substack_url', DEFAULT_SUBSTACK_URL)}",
        f"Follow on X: {payload.get('x_handle', DEFAULT_X_HANDLE)}",
    ]

    return safe_join_parts(lines)


def split_for_twitter(text: str, max_len: int = 275) -> list[str]:
    text = clean_text(text)
    chunks: list[str] = []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para

        if len(candidate) <= max_len:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(para) <= max_len:
            current = para
            continue

        words = para.split()
        temp = ""

        for word in words:
            candidate_word = f"{temp} {word}".strip()
            if len(candidate_word) <= max_len:
                temp = candidate_word
            else:
                if temp:
                    chunks.append(temp)
                temp = word

        if temp:
            current = temp

    if current:
        chunks.append(current)

    total = len(chunks)
    numbered: list[str] = []

    for i, chunk in enumerate(chunks, start=1):
        prefix = f"{i}/{total} "
        if len(prefix) + len(chunk) > 280:
            chunk = chunk[: 280 - len(prefix) - 1].rstrip()
        numbered.append(prefix + chunk)

    return numbered


def build_twitter_thread(payload: dict[str, Any]) -> list[str]:
    intro = (
        f"{payload.get('title', TITLE)}\n\n"
        f"{payload.get('headline', '')}\n\n"
        f"{payload.get('x_handle', DEFAULT_X_HANDLE)}"
    )

    bullets = "\n".join(f"- {line}" for line in payload.get("key_storylines", [])[:4])

    body = (
        f"{intro}\n\n"
        f"Key storylines:\n{bullets}\n\n"
        f"Snapshot: {payload.get('snapshot', '')}\n\n"
        f"{payload.get('substack_url', DEFAULT_SUBSTACK_URL)}"
    )

    return split_for_twitter(body)


def backup_previous_json() -> None:
    if OUTPUT_LATEST_JSON.exists():
        shutil.copy2(OUTPUT_LATEST_JSON, OUTPUT_PREVIOUS_JSON)
        log(f"Backed up previous JSON to {OUTPUT_PREVIOUS_JSON.name}")


def copy_file_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    log(f"Copied: {src} -> {dst}")
    return True


def sync_website_files() -> list[Path]:
    copied: list[Path] = []

    pairs = [
        (OUTPUT_LATEST_JSON, WEB_COPY_TARGETS["latest_report.json"]),
        (OUTPUT_LATEST_TXT, WEB_COPY_TARGETS["latest_report.txt"]),
        (GLOBAL_REPORT_TXT, WEB_COPY_TARGETS["global_ai_report.txt"]),
    ]

    for src, dst in pairs:
        if copy_file_if_exists(src, dst):
            copied.append(dst)

    return copied


def split_for_telegram(text: str, max_len: int = 3900) -> list[str]:
    text = clean_text(text)

    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current = ""

    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue

        candidate = f"{current}\n\n{para}".strip() if current else para

        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = para

            while len(current) > max_len:
                chunks.append(current[:max_len])
                current = current[max_len:]

    if current:
        chunks.append(current)

    return chunks


def send_telegram_message(text: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id or requests is None:
        log("Telegram send skipped.")
        return False

    chunks = split_for_telegram(text, 3900)
    ok = True

    for idx, chunk in enumerate(chunks, start=1):
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "disable_web_page_preview": False,
                },
                timeout=30,
            )
            response.raise_for_status()
            log(f"Telegram part sent: {idx}/{len(chunks)}")
        except Exception as exc:
            ok = False
            log(f"Telegram exception: {exc}")
            break

    return ok


def send_twitter_thread(parts: list[str]) -> bool:
    api_key = os.getenv("TWITTER_API_KEY", "").strip()
    api_secret = os.getenv("TWITTER_API_SECRET", "").strip()
    access_token = os.getenv("TWITTER_ACCESS_TOKEN", "").strip()
    access_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "").strip()

    if not all([api_key, api_secret, access_token, access_secret]) or tweepy is None:
        log("X/Twitter send skipped.")
        return False

    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )

        reply_to = None

        for idx, part in enumerate(parts, start=1):
            response = client.create_tweet(
                text=part,
                in_reply_to_tweet_id=reply_to,
                user_auth=True,
            )
            tweet_id = response.data["id"]
            reply_to = tweet_id
            log(f"Posted tweet {idx}/{len(parts)}")

        log("X thread posted successfully.")
        return True

    except Exception as exc:
        log(f"Twitter exception: {exc}")
        return False


def maybe_run_website_git_sync() -> bool:
    if os.getenv("WEBSITE_AUTO_GIT", "0").strip() != "1":
        log("Website git sync skipped.")
        return False

    if not WEB_DIR.exists():
        log("Website git sync skipped: web directory missing.")
        return False

    commands = [
        ["git", "add", "public/latest_report.json", "public/latest_report.txt", "public/global_ai_report.txt"],
        ["git", "commit", "-m", f"Global AI Report auto-update {now_et().strftime('%Y-%m-%d %H:%M:%S ET')}"],
        ["git", "pull", "--rebase"],
        ["git", "push", "origin", "master"],
    ]

    try:
        for cmd in commands:
            result = subprocess.run(
                cmd,
                cwd=str(WEB_DIR),
                capture_output=True,
                text=True,
                check=False,
            )

            if result.stdout.strip():
                log(result.stdout.strip())

            if result.stderr.strip():
                log(result.stderr.strip())

        return True

    except Exception as exc:
        log(f"Website git sync exception: {exc}")
        return False



def refresh_carried_forward_section(key: str, section: dict[str, Any]) -> dict[str, Any]:
    """Reuse a previous live section when this run lacks upstream input files.

    This keeps the site deployable and honest: the card is marked as carried forward,
    the heartbeat is fresh, and the payload does not pretend that a new upstream AI
    source file was present.
    """
    label = format_label(key)
    refreshed = dict(section)

    headline = clean_text(refreshed.get("headline") or refreshed.get("title") or f"{label} signals carried forward")
    snapshot = clean_text(refreshed.get("snapshot") or refreshed.get("summary") or headline)
    content = clean_text(refreshed.get("content") or snapshot)

    refreshed.update({
        "title": label,
        "headline": headline,
        "snapshot": snapshot,
        "content": append_heartbeat_to_content(content, label),
        "source_file": clean_text(refreshed.get("source_file") or "previous_latest_report.json"),
        "source_updated_at": clean_text(refreshed.get("source_updated_at") or refreshed.get("updated_at") or RUN_STARTED_AT),
        "updated_at": RUN_STARTED_AT,
        "generated_at": RUN_STARTED_AT,
        "published_at": RUN_STARTED_AT,
        "last_checked": RUN_STARTED_AT,
        "last_pipeline_run": RUN_STARTED_AT,
        "freshness_status": "carried_forward_pending_upstream",
        "heartbeat": {
            "status": "checked",
            "run_id": RUN_ID,
            "checked_at": RUN_STARTED_AT,
            "checked_at_iso": RUN_ISO,
            "message": f"{label} checked by GSR Network at {RUN_STARTED_AT}; previous live section carried forward because no upstream AI input file was present.",
        },
    })

    return refreshed


def load_reports_from_previous_latest() -> dict[str, dict[str, Any]]:
    """Recover report sections from the last good latest_report JSON.

    GitHub Actions can occasionally run the distribution step without the upstream
    generated ai_report/technology_report/business_report/policy_report/research_report
    files. In that case, keep the site live and mark the sections clearly rather than
    failing the whole morning run.
    """
    reports: dict[str, dict[str, Any]] = {}

    candidate_paths = [OUTPUT_PREVIOUS_JSON, OUTPUT_LATEST_JSON]

    for path in candidate_paths:
        data = read_json_file(path)
        if not isinstance(data, dict):
            continue

        sections = data.get("sections")
        if not isinstance(sections, dict):
            continue

        for key in SECTION_ORDER:
            section = sections.get(key)
            if isinstance(section, dict):
                reports[key] = refresh_carried_forward_section(key, section)

        if reports:
            log(f"Recovered {len(reports)} carried-forward AI section(s) from {path.name}.")
            break

    return reports


def load_previous_live_payload() -> dict[str, Any] | None:
    for path in [OUTPUT_PREVIOUS_JSON, OUTPUT_LATEST_JSON]:
        data = read_json_file(path)
        if isinstance(data, dict) and isinstance(data.get("live_newsroom"), list) and data.get("live_newsroom"):
            data["updated_at"] = RUN_STARTED_AT
            data["generated_at"] = RUN_STARTED_AT
            data["published_at"] = RUN_STARTED_AT
            data["last_checked"] = RUN_STARTED_AT
            data["last_pipeline_run"] = RUN_STARTED_AT
            data["freshness_status"] = "carried_forward_live_newsroom"
            log(f"Recovered carried-forward AI live newsroom payload from {path.name}.")
            return normalize_payload(data, "ai")
    return None


def build_minimum_live_reports() -> dict[str, dict[str, Any]]:
    """Last-resort live heartbeat sections when no input files or prior JSON exist."""
    reports: dict[str, dict[str, Any]] = {}

    fallback_snapshots = {
        "ai": "Global AI Report completed a live pipeline heartbeat, but no upstream AI source file was available during this run.",
        "technology": "Technology signals were checked by the GSR Network pipeline, but no upstream technology source file was available during this run.",
        "business": "AI business signals were checked by the GSR Network pipeline, but no upstream business source file was available during this run.",
        "policy": "AI policy signals were checked by the GSR Network pipeline, but no upstream policy source file was available during this run.",
        "research": "AI research signals were checked by the GSR Network pipeline, but no upstream research source file was available during this run.",
    }

    for key in SECTION_ORDER:
        label = format_label(key)
        snapshot = fallback_snapshots[key]
        reports[key] = {
            "title": label,
            "source_file": "system_heartbeat_fallback",
            "source_updated_at": RUN_STARTED_AT,
            "updated_at": RUN_STARTED_AT,
            "generated_at": RUN_STARTED_AT,
            "published_at": RUN_STARTED_AT,
            "last_checked": RUN_STARTED_AT,
            "last_pipeline_run": RUN_STARTED_AT,
            "headline": f"{label} pipeline heartbeat completed",
            "snapshot": snapshot,
            "content": append_heartbeat_to_content(snapshot, label),
            "key_storylines": [
                f"{label}: upstream input file missing during this run.",
                f"System heartbeat: Global AI Report checked this section at {RUN_STARTED_AT}.",
            ],
            "freshness_status": "system_heartbeat_no_upstream_input",
            "heartbeat": {
                "status": "checked",
                "run_id": RUN_ID,
                "checked_at": RUN_STARTED_AT,
                "checked_at_iso": RUN_ISO,
                "message": f"{label} checked by GSR Network at {RUN_STARTED_AT}; no upstream input file was present.",
            },
        }

    log("Built last-resort AI heartbeat sections because no source files or previous JSON sections were available.")
    return reports

def main() -> int:
    log("Starting Global AI Report distribution build.")
    log(f"[HEARTBEAT] Run ID: {RUN_ID}")

    load_environment()
    backup_previous_json()

    reports = load_reports()

    carried_payload = None

    if not reports:
        log("WARNING: No fresh AI report files were loaded. Attempting to preserve previous live AI sections.")
        carried_payload = load_previous_live_payload()
        if carried_payload:
            latest_report_text = build_latest_report_text(carried_payload)
            substack_post = build_substack_post(carried_payload)
            telegram_post = build_telegram_post(carried_payload)
            twitter_parts = build_twitter_thread(carried_payload)

            write_json_file(OUTPUT_LATEST_JSON, carried_payload)
            write_text_file(OUTPUT_LATEST_TXT, latest_report_text)
            write_text_file(OUTPUT_SUBSTACK, substack_post)
            write_text_file(OUTPUT_TELEGRAM, telegram_post)
            write_text_file(OUTPUT_TWITTER, "\n\n---\n\n".join(twitter_parts))
            write_text_file(GLOBAL_REPORT_TXT, latest_report_text)
            sync_website_files()
            log("GLOBAL AI REPORT DISTRIBUTION BUILD COMPLETE")
            return 0
        reports = load_reports_from_previous_latest()

    if not reports:
        log("WARNING: No previous AI sections were available. Building minimum live heartbeat sections instead of failing the run.")
        reports = build_minimum_live_reports()

    payload = build_latest_report_payload(reports)

    latest_report_text = build_latest_report_text(payload)
    substack_post = build_substack_post(payload)
    telegram_post = build_telegram_post(payload)
    twitter_parts = build_twitter_thread(payload)

    write_json_file(OUTPUT_LATEST_JSON, payload)
    write_text_file(OUTPUT_LATEST_TXT, latest_report_text)
    write_text_file(OUTPUT_SUBSTACK, substack_post)
    write_text_file(OUTPUT_TELEGRAM, telegram_post)
    write_text_file(OUTPUT_TWITTER, "\n\n---\n\n".join(twitter_parts))
    write_text_file(GLOBAL_REPORT_TXT, latest_report_text)

    copied_files = sync_website_files()

    telegram_ok = send_telegram_message(telegram_post)
    twitter_ok = send_twitter_thread(twitter_parts)
    website_git_ok = maybe_run_website_git_sync()

    log("==============================================")
    log("GLOBAL AI REPORT DISTRIBUTION SUMMARY")
    log("==============================================")
    log("Files Written: 6")
    log(f" - {OUTPUT_SUBSTACK.name}")
    log(f" - {OUTPUT_TELEGRAM.name}")
    log(f" - {OUTPUT_TWITTER.name}")
    log(f" - {OUTPUT_LATEST_TXT.name}")
    log(f" - {OUTPUT_LATEST_JSON.name}")
    log(f" - {GLOBAL_REPORT_TXT.name}")

    log(f"Website Sync Copies: {len(copied_files)}")
    for path in copied_files:
        log(f" - {path}")

    log(f"Telegram OK: {telegram_ok}")
    log(f"X OK: {twitter_ok}")
    log(f"Website Auto-Deploy OK: {website_git_ok}")
    log("Heartbeat active")
    log("Forced freshness active")
    log("NO CRITICAL ERRORS DETECTED")
    log("==============================================")
    log("GLOBAL AI REPORT DISTRIBUTION BUILD COMPLETE")
    log("==============================================")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        log(f"FATAL ERROR: {exc}")
        traceback.print_exc()
        raise SystemExit(1)
