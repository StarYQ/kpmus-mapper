import json
import re
import sys
from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime, timezone

from mapper.mapping_store import load_cached_mapping_map, merge_mapping_cache
from mapper.outcome_log import (
    append_outcome_rows,
    build_outcome_rows,
    new_run_id,
)
from mapper.pmus_client import PmusClient
from mapper.instrument_store import upsert_instruments
from mapper.manual import load_overrides, load_player_aliases, load_team_aliases, write_team_aliases
from mapper.kalshi_client import KalshiReadClient
from mapper.engine import (
    build_event_mapping_updates,
    event_stage_outcomes,
    required_kalshi_series,
    resolve_instruments,
    validate_manual_overrides,
    validate_player_aliases,
)


PMUS_BATCH_SIZE = 1000
KALSHI_EVENT_PAGE_SIZE = 200
KALSHI_STATUS = "open"
SYMBOL_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")
EVENT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")


def _dedupe(values):
    result = []
    seen = set()
    for value in values:
        normalized = str(value or "").strip().lower()
        if (not normalized) or (normalized in seen):
            continue
        if (SYMBOL_RE.match(normalized) is None):
            raise ValueError(f"invalid PMUS symbol: {value!r}")
        seen.add(normalized)
        result.append(normalized)
    return result


def _pmus_request(client, body):
    response = client.post("/api/v1beta1/list_instruments", json.dumps(body))
    if (not isinstance(response, Mapping)):
        raise ValueError("PMUS list_instruments returned a non-object response")
    instruments = response.get("instruments")
    if (instruments is not None) and (not isinstance(instruments, list)):
        raise ValueError("PMUS list_instruments.instruments is not a list")
    return response


def _paged_pmus_request(client, base_body):
    records = []
    page_token = None
    seen_tokens = set()
    while True:
        body = dict(base_body)
        if page_token:
            body["page_token"] = page_token
        response = _pmus_request(client, body)
        records.extend(response.get("instruments") or [])
        next_page_token = str(response.get("next_page_token") or "")
        if (not next_page_token):
            return records
        if (next_page_token in seen_tokens):
            raise ValueError("PMUS list_instruments repeated a page token")
        seen_tokens.add(next_page_token)
        page_token = next_page_token


def _fetch_requested_pmus(client, symbols):
    records = {}
    for start in range(0, len(symbols), PMUS_BATCH_SIZE):
        batch = symbols[start:start + PMUS_BATCH_SIZE]
        rows = _paged_pmus_request(client, {
            "page_size": len(batch),
            "symbols": batch,
        })
        requested = set(batch)
        for row in rows:
            symbol = str(row.get("symbol") or "").strip().lower()
            if symbol in requested:
                records[symbol] = row
    return records


def _fetch_pmus_event_siblings(client, event_id):
    if (EVENT_ID_RE.match(event_id) is None):
        raise ValueError(f"refusing unsafe PMUS event_id filter: {event_id!r}")
    rows = _paged_pmus_request(client, {
        "page_size": PMUS_BATCH_SIZE,
        "filter": {"where_clause": f"symbol LIKE '%-{event_id}%'"},
    })
    return [
        row for row in rows
        if str((row.get("metadata") or {}).get("event_id") or "") == event_id
    ]


def _event_has_sportradar(records):
    for record in records:
        value = (record.get("metadata") or {}).get("event_external_id_sportradar")
        if str(value or "").strip():
            return True
    return False


def _live_pmus_context(symbols):
    client = PmusClient()
    requested = _fetch_requested_pmus(client, symbols)

    groups = defaultdict(list)
    for record in requested.values():
        event_id = str((record.get("metadata") or {}).get("event_id") or "").strip()
        if event_id:
            groups[event_id].append(record)

    context_by_symbol = dict(requested)
    # id-less events need their sibling rows: the names+kickoff join reads home/away from any of them
    for event_id, records in groups.items():
        if _event_has_sportradar(records):
            continue
        for sibling in _fetch_pmus_event_siblings(client, event_id):
            sibling_symbol = str(sibling.get("symbol") or "").strip().lower()
            if sibling_symbol:
                context_by_symbol[sibling_symbol] = sibling
    context = list(context_by_symbol.values())
    upsert_instruments(context)
    return (requested, context)


def _fetch_kalshi_context(series_tickers):
    if (not series_tickers):
        return ([], [])
    client = KalshiReadClient()
    events = {}
    milestones = {}
    for series_ticker in series_tickers:
        params = {
            "series_ticker": series_ticker,
            "status": KALSHI_STATUS,
            # Both flags default to false. Without the first there are no markets to match; without
            # the second there are no milestones, and the milestone carries the Sportradar id.
            "with_nested_markets": True,
            "with_milestones": True,
            "limit": KALSHI_EVENT_PAGE_SIZE,
        }
        seen_cursors = set()
        while True:
            payload = client.get("/events", params)
            if (not isinstance(payload, Mapping)):
                raise ValueError("Kalshi get_events returned a non-object response")
            for event in (payload.get("events") or []):
                event_ticker = str(event.get("event_ticker") or "").strip()
                if event_ticker:
                    events[event_ticker] = event
            for milestone in (payload.get("milestones") or []):
                milestone_id = str(milestone.get("id") or "").strip()
                if milestone_id:
                    milestones[milestone_id] = milestone
            cursor = str(payload.get("cursor") or "")
            if (not cursor):
                break
            if (cursor in seen_cursors):
                raise ValueError(f"Kalshi get_events repeated a cursor for {series_ticker}")
            seen_cursors.add(cursor)
            params["cursor"] = cursor
    return (list(milestones.values()), list(events.values()))


def _not_found_result(symbol):
    return {
        "pmus_symbol": symbol,
        "pmus_event_id": None,
        "resolved": False,
        "kalshi_ticker": None,
        "side": None,
        "rung": None,
        "reason": "pmus_instrument_not_found",
    }


def _apply_review(symbols, results, context, milestones, events,
                  manual_overrides, aliases, cached_event_mappings):
    from mapper import llm_review

    api_key = llm_review.load_api_key()
    if (not api_key):
        print("review skipped: no anthropic key", file=sys.stderr)
        return results

    rows = [results.get(symbol) or _not_found_result(symbol) for symbol in symbols]
    metadata_by_symbol = {}
    for record in context:
        symbol = str(record.get("symbol") or "").strip().lower()
        if symbol:
            metadata_by_symbol[symbol] = record

    leagues = set()
    for row in rows:
        if row.get("resolved") or (str(row.get("reason")) != "no_sportradar_id"):
            continue
        meta = (metadata_by_symbol.get(str(row.get("pmus_symbol") or "")) or {}).get("metadata") or {}
        league = meta.get("event_series")
        if league in llm_review.EVENT_ANCHOR_SERIES:
            leagues.add(league)
    client = KalshiReadClient() if leagues else None
    games_by_league = {
        league: llm_review.kalshi_games(client, llm_review.EVENT_ANCHOR_SERIES[league])
        for league in sorted(leagues) if league in llm_review.EVENT_ANCHOR_SERIES
    }

    queue = llm_review.build_queue(rows, metadata_by_symbol, games_by_league, load_team_aliases(), milestones, events)
    verdicts = llm_review.load_verdicts()
    accepted_pairs = {}
    accepted_events = set()
    asked = 0
    for item in queue:
        if (item["kind"] == "same_nickname"):
            continue
        key = llm_review.question_key(item)
        record = verdicts.get(key)
        if (record is None):
            answer_text = llm_review.call_model(llm_review.render_prompt(item), api_key)
            verdict = llm_review.judge(item, answer_text)
            record = {"question_key": key, "event_id": item["event_id"], "league": item["league"],
                      "our": item["our"], "candidates": item["candidates"], "model": llm_review.LLM_MODEL,
                      "answer": answer_text, "verdict": verdict,
                      "asked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            llm_review.append_verdict(record)
            asked += 1
        if record["verdict"].get("accepted"):
            accepted_pairs.update(record["verdict"]["pairs"])
            accepted_events.add(item["event_id"])
    print(f"review: {len(queue)} queued, {asked} asked, {len(accepted_events)} pairing(s) accepted",
          file=sys.stderr)
    if (not accepted_pairs):
        return results

    # second pass with the accepted pairs as aliases
    write_team_aliases(accepted_pairs)
    second = resolve_instruments(
        context,
        milestones,
        events,
        manual_overrides=manual_overrides,
        player_aliases=aliases,
        team_aliases=load_team_aliases(),
        cached_event_mappings=cached_event_mappings,
    )
    updated = dict(results)
    for symbol in symbols:
        row = results.get(symbol)
        if ((row is None) or (not row.get("resolved"))) and (symbol in second):
            updated[symbol] = second[symbol]
    return updated


def resolve(symbols):
    symbols = _dedupe(str(s or "").strip().lower() for s in symbols)
    if (not symbols):
        raise ValueError("no PMUS symbols supplied")
    manual_overrides = load_overrides()
    validate_manual_overrides(manual_overrides)
    aliases = load_player_aliases()
    validate_player_aliases(aliases)
    (requested, context) = _live_pmus_context(symbols)

    requested_context = list(requested.values())
    for symbol in symbols:
        if (symbol not in requested) and (symbol in manual_overrides):
            synthetic = {"symbol": symbol, "metadata": {}}
            context.append(synthetic)
            requested_context.append(synthetic)

    kalshi_series = required_kalshi_series(requested_context, manual_overrides=manual_overrides)
    (milestones, events) = _fetch_kalshi_context(kalshi_series)
    cached_event_mappings = load_cached_mapping_map()
    results = resolve_instruments(
        context, milestones, events,
        manual_overrides=manual_overrides, player_aliases=aliases,
        team_aliases=load_team_aliases(), cached_event_mappings=cached_event_mappings,
    )
    try:
        results = _apply_review(symbols, results, context, milestones, events,
                                manual_overrides, aliases, cached_event_mappings)
    except Exception as error:
        print(f"review failed: {error}", file=sys.stderr)
    updates = build_event_mapping_updates(context, milestones, team_aliases=load_team_aliases())
    resolved_at = datetime.now(timezone.utc).isoformat()
    for update in updates.values():
        update["resolved_at"] = resolved_at
    merge_mapping_cache(updates)
    run_id = new_run_id()
    event_outcomes = event_stage_outcomes(context, milestones, cached_event_mappings, team_aliases=load_team_aliases())
    append_outcome_rows(build_outcome_rows(symbols, results, requested, event_outcomes, run_id=run_id, source="live"))
    return (run_id, {symbol: (results.get(symbol) or _not_found_result(symbol)) for symbol in symbols})
