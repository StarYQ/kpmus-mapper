from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory

from mapper import manual
from mapper.drift import report
from mapper.engine import validate_manual_overrides, validate_player_aliases
from mapper.models import PlayerAlias, TeamAlias
from mapper.outcome_log import iter_outcome_rows
from mapper.resolve import SYMBOL_RE, resolve as resolve_symbols

DIST = Path(__file__).resolve().parent.parent / "web" / "dist"
ALIASES = {"players": (PlayerAlias, validate_player_aliases), "teams": (TeamAlias, None)}

# gunicorn api.app:app
app = Flask(__name__, static_folder=None)


def _error(status, message):
    return jsonify({"error": message}), status


@app.errorhandler(400)
def _bad_request(error):
    return _error(400, getattr(error, "description", None) or "bad request")


@app.errorhandler(404)
def _not_found(error):
    return _error(404, getattr(error, "description", None) or "not found")


@app.errorhandler(500)
def _server_error(error):
    return _error(500, "internal server error")


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.post("/resolve")
def resolve():
    body = request.get_json(silent=True)
    if (not isinstance(body, dict)) or (not isinstance(body.get("symbols"), list)):
        return _error(400, 'body format should be {"symbols": [...]}')
    symbols = [str(value or "").strip().lower() for value in body["symbols"]]
    if not (1 <= len(symbols) <= 500):
        return _error(400, "enter between 1-500 entries for now")
    bad = [symbol for symbol in symbols if SYMBOL_RE.match(symbol) is None]
    if bad:
        return _error(400, f"invalid PMUS symbol: {bad[0]!r}")
    try:
        (run_id, results) = resolve_symbols(symbols)
    except Exception as error:
        return _error(502, f"resolve failed: {error}")
    return jsonify({"run": run_id, "results": [
        {"symbol": symbol, "kalshi_ticker": answer.get("kalshi_ticker"), "side": answer.get("side"),
         "rung": answer.get("rung"), "reason": answer.get("reason")}
        for (symbol, answer) in results.items()
    ]})


@app.get("/drift")
def drift():
    return jsonify(report(iter_outcome_rows()))


@app.get("/overrides")
def overrides():
    return jsonify({"overrides": manual.list_overrides()})


@app.put("/overrides/<symbol>")
def put_override(symbol):
    symbol = symbol.strip().lower()
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _error(400, 'body must be {"kalshi_ticker": ..., "side": ...}')
    try:
        validate_manual_overrides({symbol: body})
    except ValueError as error:
        return _error(400, str(error))
    return jsonify(manual.set_override(symbol, str(body["kalshi_ticker"]).strip(), str(body["side"]).strip().lower()))


@app.delete("/overrides/<symbol>")
def delete_override(symbol):
    if not manual.delete_override(symbol.strip().lower()):
        return _error(404, "unknown override")
    return jsonify({"deleted": symbol})


@app.get("/aliases/<kind>")
def list_aliases(kind):
    if kind not in ALIASES:
        return _error(404, "unknown alias table")
    wanted = {value.strip() for value in (request.args.get("source") or "").split(",") if value.strip()}
    return jsonify({"aliases": [{"name": name, "alias": alias, "source": source}
                                for (name, alias, source) in manual.list_aliases(ALIASES[kind][0])
                                if (not wanted) or (source in wanted)]})


@app.put("/aliases/<kind>")
def put_alias(kind):
    if kind not in ALIASES:
        return _error(404, "unknown alias table")
    (model, validator) = ALIASES[kind]
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _error(400, 'body must be {"name": ..., "alias": ...}')
    name = str(body.get("name") or "").strip()
    alias = str(body.get("alias") or "").strip()
    if (not name) or (not alias):
        return _error(400, "name and alias must be non-empty strings")
    if validator is not None:
        try:
            validator({name: [alias]})
        except ValueError as error:
            return _error(400, str(error))
    manual.add_alias(model, name, alias)
    return jsonify({"name": name, "alias": alias})


@app.delete("/aliases/<kind>/<name>/<alias>")
def delete_alias(kind, name, alias):
    if kind not in ALIASES:
        return _error(404, "unknown alias table")
    if not manual.remove_alias(ALIASES[kind][0], name, alias):
        return _error(404, "unknown alias")
    return jsonify({"deleted": [name, alias]})


@app.get("/", defaults={"path": ""})
@app.get("/<path:path>")
def ui(path):
    if path and (DIST / path).is_file():
        return send_from_directory(DIST, path)
    if (DIST / "index.html").is_file():
        return send_file(DIST / "index.html")
    return jsonify({"ok": True}) if (path == "") else _error(404, "not found")
