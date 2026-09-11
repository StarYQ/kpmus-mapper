from collections.abc import Mapping
from datetime import datetime, timezone

from sqlalchemy import select

from mapper.db import Session
from mapper.models import EventMapping


MAPPING_KEEP_FIELDS = {
    "pmus_event_id",
    "sportradar_event_id",
    "kalshi_milestone_id",
    "kalshi_primary_event_tickers",
    "kalshi_related_event_tickers",
    "method",
    "resolved_at",
}


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _coerce_timestamp(value):
    if value is None:
        return None
    try:
        if isinstance(value, datetime):
            timestamp = value
        else:
            text = str(value).strip()
            if (not text):
                return None
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            timestamp = datetime.fromisoformat(text)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return timestamp.timestamp()
    except Exception:
        return None


def coerce_timestamp(value):
    return _coerce_timestamp(value)


def _is_stale_update(existing, update):
    if (not isinstance(existing, Mapping)) or (not isinstance(update, Mapping)):
        return False
    existing_timestamp = _coerce_timestamp(existing.get("resolved_at"))
    update_timestamp = _coerce_timestamp(update.get("resolved_at"))
    return (
        (existing_timestamp is not None)
        and (update_timestamp is not None)
        and (update_timestamp < existing_timestamp)
    )


def _event_id_from_record(record):
    if (not isinstance(record, Mapping)):
        return None
    event_id = record.get("pmus_event_id")
    if (not isinstance(event_id, str)):
        return None
    event_id = event_id.strip()
    return event_id or None


def _normalize_sportradar_event_id(value):
    if value is None:
        return None
    value = str(value).strip().lower()
    prefix = "sr:sport_event:"
    if value.startswith(prefix):
        value = value[len(prefix):].strip()
    return value or None


def _nonempty_string(value):
    if (not isinstance(value, str)):
        return None
    value = value.strip()
    return value or None


def _ticker_list(value, require_nonempty=False):
    if (not isinstance(value, (list, tuple))):
        return None
    tickers = []
    seen = set()
    for ticker in value:
        ticker = _nonempty_string(ticker)
        if (ticker is None):
            return None
        if ticker not in seen:
            tickers.append(ticker)
            seen.add(ticker)
    if require_nonempty and (not tickers):
        return None
    return tickers


def _event_identity_fields(mapping):
    if (not isinstance(mapping, Mapping)):
        return None

    event_id = _event_id_from_record(mapping)
    sportradar_event_id = _normalize_sportradar_event_id(
        mapping.get("sportradar_event_id")
    )
    milestone_id = _nonempty_string(mapping.get("kalshi_milestone_id"))
    primary_value = mapping.get("kalshi_primary_event_tickers")
    if primary_value is None:
        primary_value = []
    primary_event_tickers = _ticker_list(primary_value)
    related_value = mapping.get("kalshi_related_event_tickers")
    if related_value is None:
        related_value = []
    related_event_tickers = _ticker_list(related_value)
    method = _nonempty_string(mapping.get("method"))

    if (
        (event_id is None)
        or (sportradar_event_id is None)
        or (milestone_id is None)
        or (primary_event_tickers is None)
        or (related_event_tickers is None)
        or (method is None)
        or ((not primary_event_tickers) and (not related_event_tickers))
    ):
        return None

    return (
        event_id,
        sportradar_event_id,
        milestone_id,
        primary_event_tickers,
        related_event_tickers,
        method,
    )


def prune_mapping(mapping):
    fields = _event_identity_fields(mapping)
    if (fields is None):
        return {}
    (
        event_id,
        sportradar_event_id,
        milestone_id,
        primary_event_tickers,
        related_event_tickers,
        method,
    ) = fields

    now = _utc_now_iso()
    resolved_at = mapping.get("resolved_at")
    if isinstance(resolved_at, datetime):
        resolved_at = resolved_at.isoformat()
    elif isinstance(resolved_at, str):
        resolved_at = resolved_at.strip()
    else:
        resolved_at = None
    if (not resolved_at):
        resolved_at = now

    record = {
        "pmus_event_id": event_id,
        "sportradar_event_id": sportradar_event_id,
        "kalshi_milestone_id": milestone_id,
        "kalshi_primary_event_tickers": primary_event_tickers,
        "kalshi_related_event_tickers": related_event_tickers,
        "method": method,
        "resolved_at": resolved_at,
        "cache_updated_at": now,
    }
    return record


def iter_cached_mappings():
    with Session() as session:
        records = [row.record for row in session.scalars(select(EventMapping))]
    for record in records:
        if isinstance(record, dict) and (_event_identity_fields(record) is not None):
            yield record


def load_cached_mapping_map():
    mappings = {}
    for record in iter_cached_mappings():
        event_id = _event_id_from_record(record)
        if (event_id is not None):
            mappings[event_id] = record
    return mappings


def get_cached_mapping(pmus_event_id):
    if (not pmus_event_id):
        return None
    with Session() as session:
        row = session.get(EventMapping, str(pmus_event_id))
        return row.record if row else None


def merge_mapping_cache(updates_by_event):
    if (not updates_by_event):
        return 0
    pruned_updates = {}
    for event_id, mapping in updates_by_event.items():
        record = prune_mapping(mapping)
        record_event_id = _event_id_from_record(record)
        if (record_event_id is None):
            continue
        if (event_id is not None) and (str(event_id) != record_event_id):
            continue
        pruned_updates[record_event_id] = record
    if (not pruned_updates):
        return 0
    with Session.begin() as session:
        for (event_id, update) in pruned_updates.items():
            existing = session.get(EventMapping, event_id)
            if (existing is None):
                session.add(EventMapping(pmus_event_id=event_id, record=update))
            elif (not _is_stale_update(existing.record, update)):
                existing.record = update
    return len(updates_by_event)
