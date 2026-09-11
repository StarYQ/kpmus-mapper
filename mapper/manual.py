from sqlalchemy import select

from mapper.db import Session
from mapper.models import Override, PlayerAlias, ReviewLog, TeamAlias


def load_overrides():
    with Session() as session:
        return {row.symbol: {"kalshi_ticker": row.kalshi_ticker, "side": row.side}
                for row in session.scalars(select(Override))}


def load_player_aliases():
    with Session() as session:
        return {row.name: list(row.labels) for row in session.scalars(select(PlayerAlias))}


def load_team_aliases():
    with Session() as session:
        return {row.name: list(row.labels) for row in session.scalars(select(TeamAlias))}


def write_team_aliases(pairs, source="review"):
    changed = 0
    with Session.begin() as session:
        for (our_name, label) in pairs.items():
            if (label.strip().lower() == our_name.strip().lower()):
                continue
            row = session.get(TeamAlias, our_name)
            values = list(row.labels) if row else []
            if (label in values):
                continue
            values.append(label)
            if row:
                row.labels = values
            else:
                session.add(TeamAlias(name=our_name, labels=values, source=source))
            changed += 1
    return changed


def seed_team_aliases():
    from mapper.seed import TEAM_ALIASES
    added = 0
    with Session.begin() as session:
        for (name, labels) in TEAM_ALIASES.items():
            if session.get(TeamAlias, name) is None:
                session.add(TeamAlias(name=name, labels=[labels] if isinstance(labels, str) else list(labels), source="seed"))
                added += 1
    return added


def list_overrides():
    with Session() as session:
        return [{"pmus_symbol": row.symbol, "kalshi_ticker": row.kalshi_ticker, "side": row.side,
                 "updated_at": row.updated_at.isoformat()} for row in session.scalars(select(Override).order_by(Override.symbol))]


def set_override(symbol, kalshi_ticker, side):
    with Session.begin() as session:
        row = session.get(Override, symbol)
        if row is None:
            row = Override(symbol=symbol, kalshi_ticker=kalshi_ticker, side=side)
            session.add(row)
        else:
            (row.kalshi_ticker, row.side) = (kalshi_ticker, side)
        session.flush()
        return {"pmus_symbol": symbol, "kalshi_ticker": kalshi_ticker, "side": side, "updated_at": row.updated_at.isoformat()}


def delete_override(symbol):
    with Session.begin() as session:
        row = session.get(Override, symbol)
        if row is None:
            return False
        session.delete(row)
        return True


def list_aliases(model):
    with Session() as session:
        return [(row.name, label, getattr(row, "source", None))
                for row in session.scalars(select(model).order_by(model.name)) for label in row.labels]


def add_alias(model, name, label, source="manual"):
    with Session.begin() as session:
        row = session.get(model, name)
        if row is None:
            session.add(model(name=name, labels=[label], **({"source": source} if (model is TeamAlias) else {})))
            return True
        if label in row.labels:
            return False
        row.labels = [*row.labels, label]
        return True


def remove_alias(model, name, label):
    with Session.begin() as session:
        row = session.get(model, name)
        if (row is None) or (label not in row.labels):
            return False
        labels = [value for value in row.labels if (value != label)]
        if labels:
            row.labels = labels
        else:
            session.delete(row)
        # a hand deletion rejects the model's verdict so the next resolve does not re-apply it
        if (model is TeamAlias):
            for log in session.scalars(select(ReviewLog)):
                verdict = (log.record or {}).get("verdict") or {}
                if verdict.get("accepted") and ((verdict.get("pairs") or {}).get(name) == label):
                    log.record = {**log.record, "verdict": {**verdict, "accepted": False, "why": "alias removed by hand"}}
        return True
