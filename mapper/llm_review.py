import json
import os
from collections import defaultdict

import httpx

from mapper.engine import (
    EVENT_ANCHOR_SERIES, KICKOFF_TOLERANCE_SECONDS,
    _build_event_index, _build_milestone_index, _group_event_source_ids, _instrument_product,
    _is_draw_label, _market_label, _milestone_title_teams, _name_match_rung, _parse_event_start,
    _select_linked_event, configured_series_for_instrument,
)
from sqlalchemy import select

from mapper.paths import KEYS_PATH
from mapper.db import Session
from mapper.models import ReviewLog

LLM_MODEL = "claude-fable-5-1"
NAME_PRODUCTS = ("aec", "atc", "asc")
API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

PROMPT = """You pair the two participants of ONE sporting event (a match, game or fight) that is listed on two
exchanges under different names. The sport or league is given; use what you know about how clubs, teams
and fighters are named in it.

Our listing (exchange A):
  league: {league}
  home / first participant: {home}
  away / second participant: {away}
  start (UTC): {kickoff}

Candidate events on exchange B at that start time (choose exactly one, or none):
{candidates}

Answer with JSON only, no prose, in exactly this shape:
{{"candidate": <1-based index of the matching candidate or null>,
  "pairs": {{"{home}": "<label of that participant on exchange B>", "{away}": "<label of that participant on exchange B>"}},
  "basis": "<one sentence>"}}
Use null for "candidate" if you are not certain which candidate is the same event, or if the two
participants cannot both be paired with that candidate's two labels."""


def load_api_key(keys_path=KEYS_PATH):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        with open(keys_path) as handle:
            return ((json.load(handle).get("anthropic") or {}).get("api_key")) or None
    except (OSError, ValueError):
        return None


def kalshi_games(client, series):
    games = []
    cursor = None
    for _ in range(20):
        params = {"series_ticker": series, "status": "open", "with_milestones": True, "limit": 200}
        if cursor:
            params["cursor"] = cursor
        payload = client.get("/events", params)
        for milestone in (payload.get("milestones") or []):
            teams = _milestone_title_teams(milestone.get("title"))
            epoch = _parse_event_start(milestone.get("start_date"))
            if teams and (epoch is not None):
                games.append((epoch, teams[0], teams[1], str(milestone.get("title")), str(milestone.get("start_date"))))
        cursor = str(payload.get("cursor") or "")
        if (not cursor):
            break
    return games


def _clubs_matched(k_home, k_away, home, away, aliases):
    return sum(1 for club in (home, away)
               if any(_name_match_rung(label, club, aliases) is not None for label in (k_home, k_away)))


def _event_labels(record, records, milestone_index, events_by_ticker, event_conflicts):
    source_ids = _group_event_source_ids(records)
    links = milestone_index.get(next(iter(source_ids))) if (len(source_ids) == 1) else None
    series = configured_series_for_instrument(record)
    if (not links) or (len(links) != 1) or (series is None):
        return None
    (event, _) = _select_linked_event(links[0], series, events_by_ticker, event_conflicts)
    if (event is None):
        return None
    product = _instrument_product(record)
    labels = sorted({_market_label(m, product) for m in (event.get("markets") or [])
                     if not _is_draw_label(m.get("yes_sub_title"))} - {""})
    if (len(labels) != 2):
        return None
    return {"title": str(event.get("title") or event.get("event_ticker")), "start": str(links[0].get("start_date")), "labels": labels}


def build_queue(rows, metadata_by_symbol, games_by_league, aliases, milestones=(), events=()):
    queue = []
    seen_events = set()
    milestone_index = _build_milestone_index(milestones)
    (events_by_ticker, event_conflicts) = _build_event_index(events)
    records_by_event = defaultdict(list)
    for record in metadata_by_symbol.values():
        records_by_event[str((record.get("metadata") or {}).get("event_id") or "")].append(record)
    for row in rows:
        if row.get("resolved"):
            continue
        symbol = str(row.get("pmus_symbol") or "")
        event_id = str(row.get("pmus_event_id") or "")
        reason = str(row.get("reason") or "")
        meta = (metadata_by_symbol.get(symbol) or {}).get("metadata") or {}
        league = str(meta.get("event_series") or symbol.split("-")[1] if "-" in symbol else "")
        if (event_id in seen_events):
            continue
        if (reason == "ambiguous_participant_names"):
            seen_events.add(event_id)
            queue.append({"kind": "same_nickname", "event_id": event_id, "league": league, "symbol": symbol,
                          "our": [meta.get("home_team_name"), meta.get("away_team_name")],
                          "note": "identical participant names; a name-keyed alias cannot express the answer -- needs a participant-id-keyed alias (design change)"})
            continue
        # id-joined game whose two labels the alias table does not carry
        if (reason == "no_kalshi_counterpart"):
            record = metadata_by_symbol.get(symbol) or {}
            our = [meta.get("home_team_name") or meta.get("long_participant_name"),
                   meta.get("away_team_name") or meta.get("short_participant_name")]
            candidate = (_event_labels(record, records_by_event.get(event_id) or [record], milestone_index, events_by_ticker, event_conflicts)
                         if (_instrument_product(record) in NAME_PRODUCTS) and (not symbol.endswith("-draw")) and all(our) else None)
            if (candidate is None) or (_clubs_matched(candidate["labels"][0], candidate["labels"][1], our[0], our[1], aliases) == 2):
                continue
            seen_events.add(event_id)
            queue.append({"kind": "market_labels", "event_id": event_id, "league": league, "symbol": symbol,
                          "our": our, "kickoff": str(meta.get("event_start_time")), "candidates": [candidate]})
            continue
        # id-less game: which of the Kalshi games at this kickoff is ours
        if (reason != "no_sportradar_id") or (league not in EVENT_ANCHOR_SERIES):
            continue
        home, away, start = meta.get("home_team_name"), meta.get("away_team_name"), meta.get("event_start_time")
        epoch = _parse_event_start(start)
        if (not home) or (not away) or (epoch is None):
            continue
        near = [g for g in (games_by_league.get(league) or []) if (abs(g[0] - epoch) <= KICKOFF_TOLERANCE_SECONDS)]
        if (not near) or any(_clubs_matched(g[1], g[2], home, away, aliases) == 2 for g in near):
            continue
        seen_events.add(event_id)
        queue.append({"kind": "kickoff_candidates", "event_id": event_id, "league": league, "symbol": symbol,
                      "our": [home, away], "kickoff": str(start),
                      "candidates": [{"title": g[3], "start": g[4], "labels": [g[1], g[2]]} for g in near]})
    return queue


def question_key(item):
    return json.dumps({"event_id": item["event_id"], "our": item["our"],
                       "candidates": sorted(c["title"] for c in item.get("candidates") or [])}, sort_keys=True)


def render_prompt(item):
    lines = [f"  {i + 1}. {c['title']}  (start {c['start']}; labels: {c['labels'][0]!r}, {c['labels'][1]!r})"
             for (i, c) in enumerate(item["candidates"])] or ["  (none listed at this kickoff)"]
    return PROMPT.format(league=item["league"], home=item["our"][0], away=item["our"][1],
                         kickoff=item["kickoff"], candidates="\n".join(lines))


def call_model(prompt, api_key, model=LLM_MODEL, timeout=60.0):
    response = httpx.post(API_URL, timeout=timeout,
                          headers={"x-api-key": api_key, "anthropic-version": API_VERSION, "content-type": "application/json"},
                          json={"model": model, "max_tokens": 400,
                                "messages": [{"role": "user", "content": prompt}]})
    if (response.status_code != 200):
        raise RuntimeError(f"anthropic API {response.status_code}: {response.text[:300]}")
    parts = response.json().get("content") or []
    return "".join(part.get("text", "") for part in parts if part.get("type") == "text")


# accept only a complete pairing onto one offered candidate; anything else stays undecided
def judge(item, answer_text):
    try:
        start = answer_text.index("{")
        answer = json.loads(answer_text[start:answer_text.rindex("}") + 1])
    except (ValueError, AttributeError):
        return {"accepted": False, "why": "not JSON"}
    index = answer.get("candidate")
    candidates = item.get("candidates") or []
    if (not isinstance(index, int)) or not (1 <= index <= len(candidates)):
        return {"accepted": False, "why": "no candidate chosen", "basis": answer.get("basis")}
    chosen = candidates[index - 1]
    pairs = answer.get("pairs") or {}
    (home, away) = item["our"]
    labels = [str(pairs.get(home) or ""), str(pairs.get(away) or "")]
    if (sorted(labels) != sorted(chosen["labels"])) or (labels[0] == labels[1]):
        return {"accepted": False, "why": "pairing is not a permutation of the candidate's labels", "basis": answer.get("basis")}
    return {"accepted": True, "candidate": chosen["title"], "pairs": {home: labels[0], away: labels[1]}, "basis": answer.get("basis")}


def load_verdicts():
    with Session() as session:
        return {row.question_key: row.record for row in session.scalars(select(ReviewLog))}


def append_verdict(record):
    with Session.begin() as session:
        session.add(ReviewLog(question_key=record["question_key"], record=record))

