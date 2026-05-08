from __future__ import annotations

import re
from typing import Any


COMPANIES = [
    "OpenAI", "Microsoft", "Google", "Meta", "Anthropic", "xAI", "Nvidia", "Apple", "Amazon",
    "Perplexity", "Mistral", "Cohere", "SpaceX", "Salesforce", "Oracle", "Adobe", "IBM",
]
PRODUCTS = ["ChatGPT", "GPT-5", "GPT-4", "Claude", "Gemini", "Grok", "Llama", "Copilot", "Sora", "DeepSeek", "API", "agent", "model", "tool", "chip"]
MOJIBAKE = {
    "\ufeff": "", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2014": "-", "\u2013": "-", "\xa0": " ",
    "â€™": "'", "â€˜": "'", "â€œ": '"', "â€\x9d": '"', "â€": '"', "â€“": "-", "â€”": "-",
    "Ã¢â‚¬â„¢": "'", "Ã¢â‚¬Ëœ": "'", "Ã¢â‚¬Å“": '"', "Ã¢â‚¬Â": '"', "Ã¢â‚¬": '"',
    "Ã¢â‚¬â€œ": "-", "Ã¢â‚¬â€": "-", "Donât": "Don't", "donât": "don't", "RenÃ©e": "Renee",
    "Ã©": "e", "Ã¡": "a", "Ã³": "o", "Ãº": "u", "Ã±": "n", "Ã¼": "u",
    "ÃƒÂ©": "e", "ÃƒÂ¡": "a", "ÃƒÂ³": "o", "ÃƒÂº": "u", "ÃƒÂ±": "n", "ÃƒÂ¼": "u",
}


def clean_text(value: Any, fallback: str = "") -> str:
    text = "" if value is None else str(value)
    for old, new in MOJIBAKE.items():
        text = text.replace(old, new)
    text = re.sub(r"\s+", " ", text).strip(" -")
    return text or fallback


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        item = clean_text(item).strip("'\".,")
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _not_headline(lines: list[str], headline: str) -> list[str]:
    headline_key = re.sub(r"[^a-z0-9]+", " ", headline.lower()).strip()
    return [line for line in _dedupe(lines) if re.sub(r"[^a-z0-9]+", " ", line.lower()).strip() != headline_key]


def _entities(text: str) -> list[str]:
    found = [name for name in COMPANIES if re.search(rf"\b{re.escape(name)}\b", text, re.I)]
    return [item for item in _dedupe(found) if len(item) > 2][:5]


def build_key_data(item: dict[str, Any], vertical: str = "ai") -> list[str]:
    headline = clean_text(item.get("headline") or item.get("title"))
    snapshot = clean_text(item.get("snapshot") or item.get("summary"))
    text = f"{headline}. {snapshot}"
    lines: list[str] = []

    entities = _entities(text)
    if entities:
        lines.append(f"Company / organization: {', '.join(entities[:4])}")

    category = clean_text(item.get("label") or item.get("category") or item.get("title"))
    if category and category.lower() != headline.lower():
        lines.append(f"Category: {category}")

    products = [p for p in PRODUCTS if re.search(rf"\b{re.escape(p)}\b", text, re.I)]
    if products:
        lines.append(f"Product / model / tool: {', '.join(_dedupe(products)[:4])}")

    figures = re.findall(r"\$[0-9][0-9,.]*(?:\s?(?:million|billion|trillion))?|[0-9]+(?:\.[0-9]+)?%", text, re.I)
    if figures:
        lines.append(f"Funding / valuation / figure: {', '.join(_dedupe(figures)[:3])}")

    date_match = re.search(r"\b(?:20[0-9]{2}-[0-9]{2}-[0-9]{2}|Q[1-4]\s+20[0-9]{2}|[A-Z][a-z]+\s+[0-9]{1,2},\s+20[0-9]{2}|today|this week)\b", text, re.I)
    if date_match:
        lines.append(f"Launch / release timing: {date_match.group(0)}")

    if re.search(r"\b(customer|developer|enterprise|creator|users?|workers?|students?|publishers?|API)\b", text, re.I):
        lines.append("Affected users: customers, developers, creators or enterprise users")
    if re.search(r"\b(lawsuit|court|regulat|safety|security|privacy|copyright|antitrust|compliance)\b", text, re.I):
        lines.append("Regulation / legal / security angle: present")
    if re.search(r"\b(multimodal|reasoning|agent|automation|benchmark|latency|context|limitation|hallucination|chip|inference|training)\b", text, re.I):
        lines.append("Technical capability / limitation: model, infrastructure or deployment detail is part of the story")

    published = clean_text(item.get("published_at") or item.get("published"))
    source = clean_text(item.get("source_name") or item.get("source"))
    if published:
        lines.append(f"Published: {published}")
    if source:
        lines.append(f"Source: {source}")

    return _not_headline(lines, headline)[:6]


def build_why_it_matters(item: dict[str, Any], vertical: str = "ai") -> list[str]:
    text = clean_text(f"{item.get('headline', '')} {item.get('snapshot', '')} {item.get('summary', '')}").lower()
    if any(w in text for w in ["lawsuit", "safety", "regulat", "security", "privacy", "copyright", "antitrust"]):
        return ["The legal or safety angle can change product strategy, deployment risk and public trust in AI systems."]
    if any(w in text for w in ["api", "developer", "agent", "model", "launch", "available", "tool"]):
        return ["The product signal matters for platform competition, developer adoption and enterprise workflow decisions."]
    if any(w in text for w in ["chip", "data center", "infrastructure", "billion", "funding", "valuation"]):
        return ["The market signal points to capacity, capital spending and competitive positioning behind the AI buildout."]
    if any(w in text for w in ["enterprise", "workspace", "customer", "deployment"]):
        return ["Enterprise adoption moves the story from experimentation into budgets, procurement and daily workflow impact."]
    return ["This gives editors a concrete AI signal tied to competition, adoption, regulation, technical capability or market impact."]


def build_what_to_watch(item: dict[str, Any], vertical: str = "ai") -> list[str]:
    org = (_entities(clean_text(item.get("headline") or item.get("snapshot") or "")) or ["the company"])[0]
    return [
        f"Watch for follow-up statements from {org}, customers, regulators or competitors.",
        "Track launch timing, developer reaction, enterprise uptake, security details and policy response.",
    ]


def normalize_card(item: dict[str, Any], vertical: str = "ai") -> dict[str, Any]:
    card = dict(item)
    for key in ["headline", "title", "snapshot", "summary", "source", "source_name", "published", "published_at", "url", "label"]:
        if key in card:
            card[key] = clean_text(card.get(key))
    headline = clean_text(card.get("headline") or card.get("title"))
    key_data = build_key_data(card, vertical)
    if not key_data:
        if clean_text(card.get("published_at") or card.get("published")):
            key_data.append(f"Published: {clean_text(card.get('published_at') or card.get('published'))}")
        key_data.append(f"Source: {clean_text(card.get('source_name') or card.get('source'), 'AI source')}")
    card["key_data"] = _not_headline(key_data, headline)[:6]
    card["why_it_matters"] = _dedupe(build_why_it_matters(card, vertical))[:4]
    card["what_to_watch"] = _dedupe(build_what_to_watch(card, vertical))[:4]
    return card


def normalize_payload(payload: dict[str, Any], vertical: str = "ai") -> dict[str, Any]:
    payload = dict(payload)
    for key in ["title", "headline", "snapshot", "site", "site_name", "vertical", "updated_at", "generated_at", "published_at"]:
        if key in payload:
            payload[key] = clean_text(payload.get(key))
    for key in ["live_newsroom", "editor_signals", "homepage_cards"]:
        if isinstance(payload.get(key), list):
            payload[key] = [normalize_card(x, vertical) if isinstance(x, dict) else x for x in payload[key]]
            payload[key] = [x for x in payload[key] if not isinstance(x, dict) or clean_text(x.get("headline") or x.get("title"))]
    if isinstance(payload.get("sections"), dict):
        payload["sections"] = {k: normalize_card(v, vertical) if isinstance(v, dict) else v for k, v in payload["sections"].items()}
        payload["sections"] = {k: v for k, v in payload["sections"].items() if not isinstance(v, dict) or clean_text(v.get("headline") or v.get("title"))}
    elif isinstance(payload.get("sections"), list):
        payload["sections"] = [normalize_card(x, vertical) if isinstance(x, dict) else x for x in payload["sections"]]
        payload["sections"] = [x for x in payload["sections"] if not isinstance(x, dict) or clean_text(x.get("headline") or x.get("title"))]
    return payload
