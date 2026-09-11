from mapper.db import Session
from mapper.models import Instrument

INSTRUMENT_KEEP_FIELDS = {
    "symbol", "state", "product_id", "description", "expiration_date", "expiration_time",
    "price_scale", "fractional_qty_scale", "minimum_trade_qty", "tick_size", "settlement_price_scale",
    "update_time", "updated_at",
}
INSTRUMENT_METADATA_KEEP_FIELDS = {
    "outcome_strike", "instrument_rules", "participant_type",
    "event_category", "event_series", "event_subcategory", "event_product_id", "event_start_time",
    "event_id", "event_external_id_sportradar", "event_external_id_sportsdataio",
    "instrument_product_series", "instrument_product", "outcome_type", "prop_type", "market_sport_type",
    "long_participant_id", "long_participant_name", "long_participant_external_id",
    "short_participant_id", "short_participant_name", "short_participant_external_id",
    "home_team_name", "away_team_name", "market_title", "tournament_name",
}


def _prune(record):
    kept = {key: record[key] for key in INSTRUMENT_KEEP_FIELDS if key in record}
    metadata = record.get("metadata") or {}
    kept["metadata"] = {key: metadata[key] for key in INSTRUMENT_METADATA_KEEP_FIELDS if key in metadata}
    return kept


def upsert_instruments(records):
    rows = [r for r in records if isinstance(r, dict) and str(r.get("symbol") or "").strip()]
    if not rows:
        return 0
    with Session.begin() as session:
        for row in rows:
            record = _prune(row)
            event_id = str(record["metadata"].get("event_id") or "").strip() or None
            session.merge(Instrument(symbol=str(row["symbol"]).strip().lower(), event_id=event_id, record=record))
    return len(rows)

