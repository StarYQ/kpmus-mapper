import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete

from mapper.db import Session
from mapper.models import Outcome

FIXTURE = Path(__file__).resolve().parent.parent / "demo-data" / "id-presence-2026.json"
RUN_PREFIX = "demo-mls-id-loss"
SERIES = "mls"            # the league that lost the id
CONTROL = "mlb"           # the league that did not, so a real change is distinguishable from a bug
BEFORE = "2026-05"        # the last month MLS carried it
AFTER = "2026-07"         # the first month it did not

# The metadata keys an MLS game instrument carries. The Sportradar id is the one that
# disappeared; the rest are what `fields` looks like on a healthy row.
BASE_FIELDS = [
    "away_team_name", "event_id", "event_series", "event_start_time", "home_team_name",
    "instrument_product", "instrument_rules", "long_participant_name", "market_sport_type",
    "market_title", "outcome_strike", "outcome_type", "participant_type",
]
ID_FIELD = "event_external_id_sportradar"


def _events(month):
    events = json.loads(FIXTURE.read_text())["events"]
    return [row for row in events if (row["month"] == month) and (row["series"] in (SERIES, CONTROL))]


def _rows(run_id, recorded_at, events, refusals=0):
    """One outcome row per event, as the resolver would have written it."""
    rows = []
    remaining = refusals
    for (index, event) in enumerate(events):
        has_id = event["has_id"]
        fields = sorted(BASE_FIELDS + ([ID_FIELD] if has_id else []))
        # A refusal only makes sense where the id is gone. Count them off those rows,
        # whatever order the fixture happens to be in.
        refused = (not has_id) and (remaining > 0)
        remaining -= int(refused)
        rows.append({
            "run_id": run_id,
            "recorded_at": recorded_at,
            "fields": fields,
            "source": "demo",
            "symbol": f"aec-{event['event_id']}-home",
            "event_id": event["event_id"],
            "event_series": event["series"],
            "instrument_product": "aec",
            "market_sport_type": ("baseball_team_full_game_winner" if (event["series"] == CONTROL)
                                  else "soccer_team_full_time_winner"),
            "event_start_time": None,
            "event_stage_reason": None,
            # Before the loss the event joined on the id; after it, on names + kickoff.
            "event_rung": "sportradar" if has_id else "name_date",
            "sportradar_event_id": f"sr:demo:{index}" if has_id else None,
            "resolved": (not refused),
            "reason": "no_sportradar_id" if refused else None,
            "rung": None if refused else ("sportradar_exact_name" if has_id else "name_date_exact_name"),
            "kalshi_ticker": None if refused else f"KXDEMO-{event['event_id'].upper()}-HOME",
            "side": None if refused else "yes",
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--with-refusals", type=int, default=0, metavar="N",
                        help="mark N of the after-run rows refused no_sportradar_id, as clubs whose "
                             "spelling needs an alias row would be")
    parser.add_argument("--clear", action="store_true", help="delete the demo rows and exit")
    args = parser.parse_args()

    if args.clear:
        with Session.begin() as session:
            removed = session.execute(delete(Outcome).where(Outcome.run_id.like(f"{RUN_PREFIX}%"))).rowcount
        print(f"removed {removed} demo rows")
        return 0

    before_events = _events(BEFORE)
    after_events = _events(AFTER)
    if (not before_events) or (not after_events):
        raise SystemExit(f"{FIXTURE.name} has no events for {BEFORE} or {AFTER}")

    now = datetime.now(timezone.utc)
    before_run = f"{RUN_PREFIX}-before"
    after_run = f"{RUN_PREFIX}-after"
    rows = (_rows(before_run, now - timedelta(minutes=2), before_events)
            + _rows(after_run, now - timedelta(minutes=1), after_events, refusals=args.with_refusals))

    with Session.begin() as session:
        session.execute(delete(Outcome).where(Outcome.run_id.like(f"{RUN_PREFIX}%")))
        session.bulk_insert_mappings(Outcome, rows)

    mls_before = [row for row in before_events if row["series"] == SERIES]
    mls_after = [row for row in after_events if row["series"] == SERIES]
    print(f"{before_run}: {len(before_events)} rows, "
          f"{SERIES} {sum(1 for r in mls_before if r['has_id'])}/{len(mls_before)} with the id")
    print(f"{after_run}:  {len(after_events)} rows, "
          f"{SERIES} {sum(1 for r in mls_after if r['has_id'])}/{len(mls_after)} with the id"
          + (f", {args.with_refusals} refused" if args.with_refusals else ""))
    print("now read it: curl -s $API/drift")
    return 0


if (__name__ == "__main__"):
    raise SystemExit(main())
