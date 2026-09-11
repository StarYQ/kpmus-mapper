from collections import defaultdict

from mapper.mapping_store import coerce_timestamp

PENDING = {"kalshi_not_listed_yet", "no_kalshi_counterpart"}


def _pending(row):
    start = coerce_timestamp(row.get("event_start_time"))
    seen = coerce_timestamp(row.get("ts"))
    return (row.get("reason") in PENDING) and (start is not None) and (seen is not None) and (start > seen)


def _answer(row):
    return (bool(row["resolved"]), row["kalshi_ticker"], row["side"], row["reason"])


def symbol_changes(rows):
    history = defaultdict(list)
    for row in rows:
        history[row["pmus_symbol"]].append(row)
    changes = []
    for (symbol, runs) in sorted(history.items()):
        latest = runs[-1]
        previous = runs[-2] if (len(runs) > 1) else None
        # a first refusal before kickoff may only mean the line is not listed yet
        if (previous is None):
            if (not latest["resolved"]) and (latest["reason"] != "unsupported_product") and (not _pending(latest)):
                changes.append({"symbol": symbol, "change": "refused", "was": None,
                                "now": _answer(latest), "run": latest["run_id"]})
            continue
        if (_answer(latest) == _answer(previous)):
            continue
        if latest["resolved"] and previous["resolved"]:
            kind = "re-pointed"
        elif previous["resolved"]:
            kind = "lost"
        elif latest["resolved"]:
            kind = "recovered"
        else:
            kind = "reason changed"
        changes.append({"symbol": symbol, "change": kind, "was": _answer(previous),
                        "now": _answer(latest), "run": latest["run_id"]})
    return changes


def _populated(rows):
    counts = defaultdict(int)
    for row in rows:
        for field in (row.get("fields") or []):
            counts[field] += 1
    return counts


def field_changes(rows):
    order = {}
    by_league = defaultdict(lambda: defaultdict(list))
    for row in rows:
        order.setdefault(row["run_id"], len(order))
        by_league[row["event_series"]][row["run_id"]].append(row)
    changes = []
    for (league, runs) in sorted(by_league.items(), key=lambda item: str(item[0])):
        run_ids = sorted(runs, key=order.get)
        if (len(run_ids) < 2):
            continue
        (previous, latest) = (runs[run_ids[-2]], runs[run_ids[-1]])
        (before, after) = (_populated(previous), _populated(latest))
        for field in sorted(set(before) | set(after)):
            if before.get(field) and (not after.get(field)):
                changes.append({"league": league, "field": field, "change": "stopped",
                                "was": f"{before[field]}/{len(previous)}", "now": f"0/{len(latest)}", "run": run_ids[-1]})
            elif after.get(field) and (not before.get(field)):
                changes.append({"league": league, "field": field, "change": "started",
                                "was": f"0/{len(previous)}", "now": f"{after[field]}/{len(latest)}", "run": run_ids[-1]})
    return changes


def latest_with_reason(rows, reason):
    latest = {}
    for row in rows:
        latest[row["pmus_symbol"]] = row
    return sorted(symbol for (symbol, row) in latest.items() if (row["reason"] == reason))


def report(rows):
    return {
        "answers": symbol_changes(rows),
        "fields": field_changes(rows),
        "kickoff_mismatch": latest_with_reason(rows, "kickoff_mismatch"),
        "unexpected_kalshi_market": latest_with_reason(rows, "unexpected_kalshi_market"),
    }

