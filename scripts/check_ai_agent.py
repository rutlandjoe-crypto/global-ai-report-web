import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CANDIDATES = [
    ROOT / "public" / "latest_report.json",
    ROOT / "latest_report.json",
]

REPORT_PATH = next((p for p in CANDIDATES if p.exists()), None)

if REPORT_PATH is None:
    print("AI AGENT FAIL: No latest_report.json found.")
    sys.exit(1)

try:
    data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"AI AGENT FAIL: Could not parse {REPORT_PATH}: {exc}")
    sys.exit(1)

failures = []
warnings = []

def as_list(value):
    return value if isinstance(value, list) else []

live_newsroom = as_list(data.get("live_newsroom"))
editor_signals = as_list(data.get("editor_signals"))
key_storylines = as_list(data.get("key_storylines"))
sections = as_list(data.get("sections"))
homepage_cards = as_list(data.get("homepage_cards"))

public_items = homepage_cards + live_newsroom + key_storylines + sections
all_items = public_items + editor_signals

if len(public_items) < 8:
    failures.append(f"Public AI output has only {len(public_items)} items; expected at least 8.")

if len(live_newsroom) < 5:
    failures.append(f"Live newsroom has only {len(live_newsroom)} items; expected at least 5.")

if len(editor_signals) < 3:
    warnings.append(f"Editor signals has only {len(editor_signals)} items; expected at least 3.")

def pick_url(item):
    if not isinstance(item, dict):
        return ""
    for key in ["url", "link", "href", "source_url"]:
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""

def pick_headline(item):
    if not isinstance(item, dict):
        return ""
    for key in ["headline", "title", "name"]:
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""

def pick_text(item):
    if not isinstance(item, dict):
        return ""

    parts = []
    for key in [
        "headline", "title", "name", "summary", "description", "snapshot",
        "dek", "context", "signal", "label", "analysis"
    ]:
        val = item.get(key)
        if isinstance(val, str):
            parts.append(val)

    for key in ["key_data", "why_it_matters", "what_to_watch", "bullets", "items"]:
        val = item.get(key)
        if isinstance(val, list):
            for entry in val:
                if isinstance(entry, str):
                    parts.append(entry)
                elif isinstance(entry, dict):
                    parts.append(pick_text(entry))

    return " ".join(parts).strip()

def pick_source(item):
    if not isinstance(item, dict):
        return ""

    for key in ["source", "publisher", "outlet", "site"]:
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip().lower()

    url = pick_url(item)
    if url:
        return re.sub(r"^https?://(www\.)?", "", url).split("/")[0].lower()

    return ""

sources = [pick_source(item) for item in all_items if pick_source(item)]
source_counts = Counter(sources)

if len(sources) >= 6 and len(source_counts) < 3:
    failures.append(f"Only {len(source_counts)} sources found across AI output; expected at least 3.")

bad_urls = []
for item in live_newsroom + editor_signals:
    headline = pick_headline(item)
    url = pick_url(item)
    if not url or not url.startswith(("http://", "https://")):
        bad_urls.append(headline or "[missing headline]")

if bad_urls:
    failures.append("Missing or invalid URLs found: " + "; ".join(bad_urls[:8]))

generic_phrases = [
    "ai watch",
    "latest ai headlines",
    "ai roundup",
    "rss",
    "feed",
    "fallback",
    "pipeline",
    "placeholder",
    "no summary available",
    "story continues",
]

for item in all_items:
    text = pick_text(item).lower()
    headline = pick_headline(item)
    found = [phrase for phrase in generic_phrases if phrase in text]
    if found:
        failures.append(f"Generic/internal language found in '{headline}': {', '.join(found)}")

category_patterns = {
    "companies": r"\b(openai|anthropic|google|microsoft|meta|amazon|nvidia|apple|xai|perplexity|mistral|cohere|deepmind)\b",
    "models": r"\b(model|models|llm|chatbot|agent|agents|reasoning|inference|training|benchmark|multimodal)\b",
    "chips": r"\b(chip|chips|gpu|gpus|semiconductor|nvidia|amd|infrastructure|data center|datacenter|compute)\b",
    "policy": r"\b(regulation|regulator|law|lawsuit|copyright|court|senate|white house|eu|safety|policy|governance)\b",
    "business": r"\b(funding|revenue|earnings|valuation|deal|partnership|enterprise|startup|customers|product|launch)\b",
}

category_hits = Counter()

for item in public_items:
    text = pick_text(item).lower()
    for category, pattern in category_patterns.items():
        if re.search(pattern, text, flags=re.I):
            category_hits[category] += 1

if len(public_items) >= 8:
    active_categories = [category for category, count in category_hits.items() if count > 0]
    if len(active_categories) < 3:
        failures.append(f"AI mix too narrow: only {len(active_categories)} categories detected: {active_categories}")

weak_headlines = []
for item in live_newsroom:
    headline = pick_headline(item)
    if not headline:
        weak_headlines.append("[missing headline]")
    elif len(headline.split()) < 4 or headline.endswith("."):
        weak_headlines.append(headline)

if weak_headlines:
    failures.append("Weak AI headlines found: " + "; ".join(weak_headlines[:8]))

print("AI Agent Check")
print(f"Report: {REPORT_PATH}")
print(f"Public items: {len(public_items)}")
print(f"Live newsroom items: {len(live_newsroom)}")
print(f"Editor signals: {len(editor_signals)}")
print(f"Key storylines: {len(key_storylines)}")
print(f"Sections: {len(sections)}")
print(f"Homepage cards: {len(homepage_cards)}")
print("Sources:", dict(source_counts))
print("Categories:", dict(category_hits))

if warnings:
    print("Warnings:")
    for warning in warnings:
        print(f"- {warning}")

if failures:
    print("AI AGENT FAIL")
    for failure in failures:
        print(f"- {failure}")
    sys.exit(1)

print("AI AGENT PASS")
