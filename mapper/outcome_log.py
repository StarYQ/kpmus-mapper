import uuid
from collections.abc import Mapping
from datetime import datetime, timezone

from sqlalchemy import select

from mapper.db import Session
from mapper.instrument_store import INSTRUMENT_METADATA_KEEP_FIELDS
from mapper.models import Outcome


def new_run_id():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def build_outcome_rows(symbols, results, requested_records, event_outcomes,
                       run_id, source):
    now = _utc_now_iso()
    rows = []
    for symbol in (symbols or []):
        result = (results or {}).get(symbol)
        if (result is None):
            result = {"resolved": False, "reason": "pmus_instrument_not_found"}
        record = (requested_records or {}).get(symbol) or {}
        metadata = record.get("metadata") if isinstance(record, Mapping) else None
        metadata = metadata if isinstance(metadata, Mapping) else {}
        event_id = result.get("pmus_event_id") or metadata.get("event_id")
        event_id = str(event_id).strip() if event_id else None
        event_outcome = (event_outcomes or {}).get(event_id) or {}
        rows.append({
            "ts": now,
            "run_id": str(run_id),
            "fields": sorted(key for key in INSTRUMENT_METADATA_KEEP_FIELDS if metadata.get(key) not in (None, "", [], {})),
            "source": str(source),
            "pmus_symbol": symbol,
            "pmus_event_id": event_id,
            "event_series": (str(metadata.get("event_series")).strip().lower() or None)
            if metadata.get("event_series") else None,
            "instrument_product": (str(metadata.get("instrument_product")).strip().lower() or None)
            if metadata.get("instrument_product") else None,
            "market_sport_type": (str(metadata.get("market_sport_type")).strip().lower() or None)
            if metadata.get("market_sport_type") else None,
            "event_start_time": metadata.get("event_start_time") or None,
            "event_stage_reason": event_outcome.get("event_reason"),
            "event_rung": event_outcome.get("event_rung"),
            "sportradar_event_id": event_outcome.get("sportradar_event_id"),
            "resolved": bool(result.get("resolved")),
            "reason": result.get("reason") if (not result.get("resolved")) else None,
            "rung": result.get("rung"),
            "kalshi_ticker": result.get("kalshi_ticker") or None,
            "side": result.get("side"),
        })
    return rows


_FIELDS = ("fields", "source", "event_series", "instrument_product", "market_sport_type",
           "event_start_time", "event_stage_reason", "event_rung", "sportradar_event_id",
           "resolved", "reason", "rung", "kalshi_ticker", "side")


def append_outcome_rows(rows):
    rows = [row for row in rows if isinstance(row, Mapping)]
    if (not rows):
        return 0
    with Session.begin() as session:
        for row in rows:
            session.add(Outcome(
                run_id=str(row["run_id"]),
                recorded_at=datetime.fromisoformat(row["ts"]),
                symbol=row["pmus_symbol"],
                event_id=row.get("pmus_event_id"),
                **{field: row.get(field) for field in _FIELDS},
            ))
    return len(rows)


def _as_row(outcome):
    row = {"ts": outcome.recorded_at.isoformat(), "run_id": outcome.run_id,
           "pmus_symbol": outcome.symbol, "pmus_event_id": outcome.event_id}
    row.update({field: getattr(outcome, field) for field in _FIELDS})
    return row


def iter_outcome_rows():
    query = select(Outcome).order_by(Outcome.id)
    with Session() as session:
        return [_as_row(outcome) for outcome in session.scalars(query)]

