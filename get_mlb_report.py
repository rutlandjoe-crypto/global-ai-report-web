from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

BASE_DIR = Path(__file__).resolve().parent
REPORT_FILE = BASE_DIR / "mlb_report.txt"

TIMEZONE = ZoneInfo("America/New_York")
SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"
REQUEST_TIMEOUT = 20
OVERNIGHT_CUTOFF_HOUR = 5

DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, human sports journalism."
)


def now_et() -> datetime:
    return datetime.now(TIMEZONE)


def generated_stamp() -> str:
    return now_et().strftime("%Y-%m-%d %I:%M:%S %p ET")


def clean_text(text: Any) -> str:
    if text is None:
        return ""

    text = str(text)

    replacements = {
        "\u2018": "'",
        "\u2019": "'",
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
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return re.sub(r"[ \t]+", " ", text).strip()


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []

    for item in items:
        cleaned = clean_text(item)
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            deduped.append(cleaned)

    return deduped


def save_report(text: str) -> None:
    REPORT_FILE.write_text(text.rstrip() + "\n", encoding="utf-8")


def fetch_schedule(date_str: str) -> dict[str, Any]:
    params = {
        "sportId": 1,
        "date": date_str,
        "hydrate": (
            "team,linescore,probablePitcher,decisions,game(content(summary,media(epg))),"
            "flags,seriesStatus,venue,review,person,stats"
        ),
    }
    response = requests.get(SCHEDULE_URL, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def extract_games(payload: dict[str, Any]) -> list[dict[str, Any]]:
    games: list[dict[str, Any]] = []
    for date_block in payload.get("dates", []):
        for game in date_block.get("games", []):
            if isinstance(game, dict):
                games.append(game)
    return games


def game_sort_key(game: dict[str, Any]) -> tuple[int, str, str]:
    game_date = clean_text(game.get("gameDate", ""))
    game_pk = game.get("gamePk", 0)
    try:
        game_pk_int = int(game_pk)
    except Exception:
        game_pk_int = 0
    return (0 if game_date else 1, game_date, str(game_pk_int))


def format_game_time(game_datetime: str | None) -> str:
    if not game_datetime:
        return "TBD"

    try:
        dt = datetime.fromisoformat(game_datetime.replace("Z", "+00:00")).astimezone(TIMEZONE)
        return dt.strftime("%I:%M %p ET").lstrip("0")
    except Exception:
        return "TBD"


def game_status(game: dict[str, Any]) -> tuple[str, str]:
    status = game.get("status", {})
    abstract_state = clean_text(status.get("abstractGameState", "")).lower()
    detailed_state = clean_text(status.get("detailedState", ""))
    detailed_lower = detailed_state.lower()
    coded_state = clean_text(status.get("codedGameState", "")).upper()

    if (
        abstract_state == "final"
        or coded_state in {"F", "O", "R"}
        or "final" in detailed_lower
        or "completed" in detailed_lower
    ):
        return "final", detailed_state or "Final"

    if (
        abstract_state == "live"
        or coded_state in {"I", "M", "N"}
        or "in progress" in detailed_lower
        or "manager challenge" in detailed_lower
        or "review" in detailed_lower
        or "delayed" in detailed_lower
    ):
        return "live", detailed_state or "Live"

    if (
        "postponed" in detailed_lower
        or "suspended" in detailed_lower
        or "cancelled" in detailed_lower
        or "canceled" in detailed_lower
    ):
        return "upcoming", detailed_state or "Scheduled"

    if (
        abstract_state in {"preview", "pre-game"}
        or "scheduled" in detailed_lower
        or "pre-game" in detailed_lower
        or "warmup" in detailed_lower
    ):
        return "upcoming", detailed_state or "Scheduled"

    return "upcoming", detailed_state or "Scheduled"


def team_name(team_block: dict[str, Any]) -> str:
    return clean_text(team_block.get("team", {}).get("name", "Unknown Team"))


def team_score(team_block: dict[str, Any]) -> int | None:
    score = team_block.get("score")
    return score if isinstance(score, int) else None


def probable_pitcher_name(team_block: dict[str, Any]) -> str:
    probable = team_block.get("probablePitcher") or {}
    return clean_text(probable.get("fullName", ""))


def doubleheader_label(game: dict[str, Any]) -> str:
    double_header = clean_text(game.get("doubleHeader", "")).upper()
    game_number = game.get("gameNumber")

    if double_header in {"Y", "S"} and str(game_number).isdigit():
        return f" (Game {game_number})"
    return ""


def build_pitcher_lookup(games: list[dict[str, Any]]) -> dict[str, set[str]]:
    pitcher_teams: dict[str, set[str]] = {}

    for game in games:
        away_block = game.get("teams", {}).get("away", {})
        home_block = game.get("teams", {}).get("home", {})

        away_team = team_name(away_block)
        home_team = team_name(home_block)

        away_pitcher = probable_pitcher_name(away_block)
        home_pitcher = probable_pitcher_name(home_block)

        if away_pitcher:
            pitcher_teams.setdefault(away_pitcher, set()).add(away_team)
        if home_pitcher:
            pitcher_teams.setdefault(home_pitcher, set()).add(home_team)

    return pitcher_teams


def probable_pitchers_text(
    game: dict[str, Any],
    pitcher_lookup: dict[str, set[str]] | None = None,
) -> str:
    away_block = game.get("teams", {}).get("away", {})
    home_block = game.get("teams", {}).get("home", {})

    away_team = team_name(away_block)
    home_team = team_name(home_block)

    away_pitcher = probable_pitcher_name(away_block)
    home_pitcher = probable_pitcher_name(home_block)

    if not away_pitcher or not home_pitcher:
        return ""

    if len(away_pitcher.split()) < 2 or len(home_pitcher.split()) < 2:
        return ""

    suspicious_names = {"tbd", "unknown", "probable", "to be determined"}
    if away_pitcher.lower() in suspicious_names or home_pitcher.lower() in suspicious_names:
        return ""

    if away_pitcher == home_pitcher:
        return ""

    if pitcher_lookup:
        away_pitcher_teams = pitcher_lookup.get(away_pitcher, set())
        home_pitcher_teams = pitcher_lookup.get(home_pitcher, set())

        if len(away_pitcher_teams) > 1 or len(home_pitcher_teams) > 1:
            return ""

        if away_team and away_pitcher_teams and away_team not in away_pitcher_teams:
            return ""
        if home_team and home_pitcher_teams and home_team not in home_pitcher_teams:
            return ""

    return f"Probables: {away_pitcher} vs. {home_pitcher}."


def inning_state_text(linescore: dict[str, Any]) -> str:
    inning_half = clean_text(linescore.get("inningHalf", ""))
    current_inning = linescore.get("currentInning")

    if inning_half and current_inning:
        return f"{inning_half} {current_inning}"
    if inning_half:
        return inning_half
    return ""


def build_final_line(game: dict[str, Any]) -> str:
    away_block = game.get("teams", {}).get("away", {})
    home_block = game.get("teams", {}).get("home", {})
    away_name = team_name(away_block)
    home_name = team_name(home_block)
    away_score = team_score(away_block)
    home_score = team_score(home_block)
    dh_label = doubleheader_label(game)

    if away_score is None or home_score is None:
        return f"{away_name} at {home_name}{dh_label} - Final."

    if away_score > home_score:
        winner = away_name
        loser = home_name
        win_score = away_score
        lose_score = home_score
    else:
        winner = home_name
        loser = away_name
        win_score = home_score
        lose_score = away_score

    return f"{winner} beat {loser}{dh_label}, {win_score}-{lose_score}."


def build_live_line(game: dict[str, Any]) -> str:
    away_block = game.get("teams", {}).get("away", {})
    home_block = game.get("teams", {}).get("home", {})
    away_name = team_name(away_block)
    home_name = team_name(home_block)
    away_score = team_score(away_block)
    home_score = team_score(home_block)
    linescore = game.get("linescore", {})
    inning_text = inning_state_text(linescore)
    dh_label = doubleheader_label(game)

    if away_score is None or home_score is None:
        if inning_text:
            return f"{away_name} at {home_name}{dh_label} - {inning_text}."
        return f"{away_name} at {home_name}{dh_label} - Live."

    if inning_text:
        return f"{away_name} {away_score}, {home_name} {home_score}{dh_label} - {inning_text}."
    return f"{away_name} {away_score}, {home_name} {home_score}{dh_label} - Live."


def build_upcoming_line(
    game: dict[str, Any],
    pitcher_lookup: dict[str, set[str]] | None = None,
) -> str:
    away_name = team_name(game.get("teams", {}).get("away", {}))
    home_name = team_name(game.get("teams", {}).get("home", {}))
    game_time = format_game_time(game.get("gameDate"))
    probables = probable_pitchers_text(game, pitcher_lookup=pitcher_lookup)
    status_detail = clean_text(game.get("status", {}).get("detailedState", ""))
    dh_label = doubleheader_label(game)

    line = f"{away_name} at {home_name}{dh_label} - {game_time}."

    postponed_markers = ("Postponed", "Suspended", "Cancelled", "Canceled")
    if status_detail and any(marker.lower() in status_detail.lower() for marker in postponed_markers):
        line = f"{away_name} at {home_name}{dh_label} - {status_detail}."

    if probables and not any(marker in line for marker in postponed_markers):
        line += f" {probables}"

    return line.strip()


def build_snapshot_text(finals: list[str], live: list[str], upcoming: list[str]) -> str:
    snapshot_parts: list[str] = []

    if finals:
        snapshot_parts.append(f"{len(finals)} final")
    if live:
        snapshot_parts.append(f"{len(live)} live")
    if upcoming:
        snapshot_parts.append(f"{len(upcoming)} upcoming")

    if snapshot_parts:
        return f"The MLB slate currently shows {', '.join(snapshot_parts)} games."
    return "No MLB games were available during this report window."


def build_headline(
    final_count: int,
    live_count: int,
    upcoming_count: int,
    probable_count: int,
    overnight_mode: bool,
) -> str:
    if live_count > 0:
        return (
            "Major League Baseball's board is active, with live game movement, developing leverage spots, "
            "and remaining schedule context all in play."
        )

    if overnight_mode and final_count > 0 and upcoming_count > 0:
        return (
            "Major League Baseball's overnight window is bridging late final scores and the next day's schedule, "
            "keeping both recap and preview value in play."
        )

    if final_count > 0 and upcoming_count > 0:
        return (
            "Major League Baseball's schedule is carrying both recap and preview value, with completed games on "
            "the board and more matchup context still ahead."
        )

    if upcoming_count > 0 and probable_count > 0:
        return (
            "Major League Baseball's schedule is driving the day, with the board centered on matchup setup, "
            "probable starters, and game-state movement."
        )

    return (
        "Major League Baseball remains central to the sports calendar, with the board defined by schedule flow, "
        "matchup setup, and evolving game context."
    )


def build_key_sections(
    finals: list[str],
    live: list[str],
    upcoming: list[str],
    upcoming_games: list[dict[str, Any]],
    overnight_mode: bool,
    probable_count: int,
) -> tuple[list[str], list[str], list[str]]:
    key_data_points: list[str] = []
    why_it_matters: list[str] = []
    story_angles: list[str] = []

    total_games = len(finals) + len(live) + len(upcoming)

    late_games = 0
    afternoon_games = 0
    evening_games = 0

    for game in upcoming_games:
        game_time = format_game_time(game.get("gameDate"))
        if game_time.endswith("PM ET"):
            if any(token in game_time for token in ("1:", "2:", "3:", "4:", "5:")):
                afternoon_games += 1
            if any(token in game_time for token in ("6:", "7:", "8:", "9:", "10:")):
                evening_games += 1
            if any(token in game_time for token in ("8:", "9:", "10:")):
                late_games += 1

    if overnight_mode:
        key_data_points.append(
            f"The overnight MLB window includes {len(finals)} final, {len(live)} live, and {len(upcoming)} upcoming games."
        )
    else:
        key_data_points.append(
            f"The MLB board shows {total_games} total games in this report window."
        )

    if upcoming:
        key_data_points.append(
            f"{len(upcoming)} games are still ahead on the schedule, keeping the focus on pregame matchup context."
        )

    if probable_count:
        key_data_points.append(
            f"{probable_count} upcoming games currently list probable starters on both sides."
        )
    else:
        key_data_points.append(
            "Probable-starter data is limited or inconsistent on the current board, keeping the emphasis on schedule context."
        )

    if afternoon_games and evening_games:
        key_data_points.append(
            f"The slate is split across {afternoon_games} afternoon starts and {evening_games} evening starts, giving the board coverage value across multiple windows."
        )
    elif evening_games:
        key_data_points.append(
            f"The schedule leans into the evening window with {evening_games} games set for later start times."
        )
    elif afternoon_games:
        key_data_points.append(
            f"The schedule is front-loaded with {afternoon_games} afternoon starts on the board."
        )

    if probable_count >= 5:
        why_it_matters.append(
            "A healthy number of listed probable starters gives reporters stronger footing for preview coverage before first pitch."
        )
    else:
        why_it_matters.append(
            "When probable-starter detail is limited or inconsistent, matchup framing and schedule context carry more editorial value."
        )

    if live:
        why_it_matters.append(
            "Live action on the board shifts the editorial lens toward leverage moments, bullpen usage, and in-game momentum."
        )
    elif finals:
        why_it_matters.append(
            "With finals already posting, the board supports both quick-turn recap writing and forward-looking setup for the remaining slate."
        )
    else:
        why_it_matters.append(
            "With the board still in pregame mode, the strongest early angles come from probable pitchers, scheduling context, and start-time sequencing."
        )

    if overnight_mode:
        why_it_matters.append(
            "An overnight MLB edition helps preserve late West Coast results while still setting up the next day's board."
        )

    if late_games:
        story_angles.append(
            "A meaningful late window keeps the MLB news cycle active deep into the night, which is useful for live blogs, newsletters, and West Coast follow coverage."
        )

    if probable_count:
        story_angles.append(
            "Where probable starters are confirmed, pitching becomes the clearest pregame frame for reporters looking to separate signal from schedule noise."
        )
    else:
        story_angles.append(
            "When probable listings are limited or suspect, the cleaner reporting angles come from lineup watch, travel context, and schedule rhythm."
        )

    if afternoon_games and evening_games:
        story_angles.append(
            "A split-day board creates room for rolling coverage, with early recaps feeding directly into later preview and live-update cycles."
        )
    elif evening_games >= 5:
        story_angles.append(
            "A heavier evening board puts more emphasis on staggered start times, bullpen planning, and late-night newsroom workflow."
        )
    elif afternoon_games >= 5:
        story_angles.append(
            "A heavier afternoon board can speed up the recap cycle and create earlier editorial handoffs into the evening sports window."
        )

    story_angles.append(
        "Across a full MLB slate, the strongest coverage shifts between pregame pitching context, live game leverage, and postgame recap value depending on timing windows."
    )

    key_data_points = dedupe_preserve_order(key_data_points)[:5]
    why_it_matters = dedupe_preserve_order(why_it_matters)[:3]
    story_angles = dedupe_preserve_order(story_angles)[:4]

    return key_data_points, why_it_matters, story_angles


def build_report(
    edition_date: str,
    final_games: list[dict[str, Any]],
    live_games: list[dict[str, Any]],
    upcoming_games: list[dict[str, Any]],
    overnight_mode: bool,
) -> str:
    final_games = sorted(final_games, key=game_sort_key)
    live_games = sorted(live_games, key=game_sort_key)
    upcoming_games = sorted(upcoming_games, key=game_sort_key)

    pitcher_lookup = build_pitcher_lookup(upcoming_games)

    finals = [build_final_line(game) for game in final_games]
    live = [build_live_line(game) for game in live_games]
    upcoming = [build_upcoming_line(game, pitcher_lookup=pitcher_lookup) for game in upcoming_games]

    probable_count = sum(
        1 for game in upcoming_games if probable_pitchers_text(game, pitcher_lookup=pitcher_lookup)
    )

    key_data_points, why_it_matters, story_angles = build_key_sections(
        finals=finals,
        live=live,
        upcoming=upcoming,
        upcoming_games=upcoming_games,
        overnight_mode=overnight_mode,
        probable_count=probable_count,
    )

    headline = build_headline(
        final_count=len(finals),
        live_count=len(live),
        upcoming_count=len(upcoming),
        probable_count=probable_count,
        overnight_mode=overnight_mode,
    )
    snapshot_text = build_snapshot_text(finals, live, upcoming)

    final_heading = "FINAL SCORES"
    live_heading = "LIVE"
    upcoming_heading = "UPCOMING"

    if overnight_mode:
        final_heading = "FINAL SCORES (PREVIOUS DAY)"
        live_heading = "LIVE (LATE WINDOW)"
        upcoming_heading = "UPCOMING (TODAY)"

    lines: list[str] = [
        f"MLB PRO REPORT | {edition_date}",
        "",
        "HEADLINE",
        headline,
        "",
        "SNAPSHOT",
        snapshot_text,
        "",
        "KEY DATA POINTS",
    ]

    if key_data_points:
        lines.extend(f"- {clean_text(item)}" for item in key_data_points)
    else:
        lines.append("- No MLB data points were available during this report window.")

    lines.extend(["", "WHY IT MATTERS"])

    if why_it_matters:
        lines.extend(f"- {clean_text(item)}" for item in why_it_matters)
    else:
        lines.append("- The clearest value on the board comes from schedule positioning and probable pitching context.")

    lines.extend(["", "STORY ANGLES"])

    if story_angles:
        lines.extend(f"- {clean_text(item)}" for item in story_angles)
    else:
        lines.append("- Pregame pitching context remains the clearest entry point for MLB coverage in this report window.")

    lines.extend(["", final_heading])
    if finals:
        lines.extend(finals)
    else:
        lines.append("No final scores were available during this report window.")

    lines.extend(["", live_heading])
    if live:
        lines.extend(live)
    else:
        lines.append("No live games were available during this report window.")

    lines.extend(["", upcoming_heading])
    if upcoming:
        lines.extend(upcoming)
    else:
        lines.append("No upcoming games were available during this report window.")

    lines.extend(["", DISCLAIMER, "", f"Generated: {generated_stamp()}"])

    return "\n".join(lines)


def build_fallback_report(reason: str, edition_date: str) -> str:
    reason = clean_text(reason)

    return "\n".join(
        [
            f"MLB PRO REPORT | {edition_date}",
            "",
            "HEADLINE",
            "Major League Baseball remains in focus, but full report generation was limited during this window.",
            "",
            "SNAPSHOT",
            "The MLB board could not be fully processed during this report window.",
            "",
            "KEY DATA POINTS",
            "- Live MLB schedule data was temporarily unavailable.",
            "",
            "WHY IT MATTERS",
            "- Even when data is interrupted, the MLB board remains central to daily newsroom planning and preview coverage.",
            "",
            "STORY ANGLES",
            "- The next clean data pull should restore full matchup context, probable starters, and board-level framing.",
            "",
            "FINAL SCORES",
            "No final scores were available during this report window.",
            "",
            "LIVE",
            "No live games were available during this report window.",
            "",
            "UPCOMING",
            "No upcoming games were available during this report window.",
            "",
            DISCLAIMER,
            "",
            f"Generated: {generated_stamp()}",
            f"Fallback reason: {reason}",
        ]
    )


def classify_games(
    yesterday_games: list[dict[str, Any]],
    today_games: list[dict[str, Any]],
    overnight_mode: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if overnight_mode:
        final_games = [g for g in yesterday_games if game_status(g)[0] == "final"]
        live_games = [g for g in yesterday_games if game_status(g)[0] == "live"]
        upcoming_games = [g for g in today_games if game_status(g)[0] == "upcoming"]
        return final_games, live_games, upcoming_games

    today_finals = [g for g in today_games if game_status(g)[0] == "final"]
    today_live = [g for g in today_games if game_status(g)[0] == "live"]
    today_upcoming = [g for g in today_games if game_status(g)[0] == "upcoming"]
    return today_finals, today_live, today_upcoming


def main() -> None:
    now = now_et()
    overnight_mode = now.hour < OVERNIGHT_CUTOFF_HOUR

    today_date = now.strftime("%Y-%m-%d")
    yesterday_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    edition_date = today_date

    try:
        today_payload = fetch_schedule(today_date)
        today_games = extract_games(today_payload)

        yesterday_games: list[dict[str, Any]] = []
        if overnight_mode:
            yesterday_payload = fetch_schedule(yesterday_date)
            yesterday_games = extract_games(yesterday_payload)

        final_games, live_games, upcoming_games = classify_games(
            yesterday_games=yesterday_games,
            today_games=today_games,
            overnight_mode=overnight_mode,
        )

        report = build_report(
            edition_date=edition_date,
            final_games=final_games,
            live_games=live_games,
            upcoming_games=upcoming_games,
            overnight_mode=overnight_mode,
        )
        save_report(report)

        print(report)
        print()
        print(f"Saved to {REPORT_FILE}")

    except Exception as exc:
        fallback = build_fallback_report(str(exc), edition_date=edition_date)
        save_report(fallback)

        print(fallback)
        print()
        print(f"Saved fallback to {REPORT_FILE}")


if __name__ == "__main__":
    main()