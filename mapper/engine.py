import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


PRODUCT_SERIES_MAP = {
    ("mlb", "aec", "baseball_team_full_game_winner", "fg"): "KXMLBGAME",
    ("mlb", "asc", "baseball_team_full_game_spread", "fg"): "KXMLBSPREAD",
    ("mlb", "asc", "baseball_team_first_five_spread", "f5"): "KXMLBF5SPREAD",
    ("mlb", "tsc", "baseball_team_full_game_total", "fg"): "KXMLBTOTAL",
    ("mlb", "tsc", "baseball_team_first_five_total", "f5"): "KXMLBF5TOTAL",
    ("cfb", "aec", "football_team_full_game_winner", "fg"): "KXNCAAFGAME",
    ("cfb", "asc", "football_team_full_game_spread", "fg"): "KXNCAAFSPREAD",
    ("cfb", "tsc", "football_team_full_game_total", "fg"): "KXNCAAFTOTAL",
    ("nfl", "aec", "football_team_full_game_winner", "fg"): "KXNFLGAME",
    ("nfl", "asc", "football_team_full_game_spread", "fg"): "KXNFLSPREAD",
    ("nfl", "tsc", "football_team_full_game_total", "fg"): "KXNFLTOTAL",
    ("epl", "atc", "soccer_team_full_time_winner", "fg"): "KXEPLGAME",
    ("epl", "asc", "soccer_team_full_game_spread", "fg"): "KXEPLSPREAD",
    ("epl", "tsc", "soccer_team_full_game_total", "fg"): "KXEPLTOTAL",
    ("ucl", "atc", "soccer_team_full_time_winner", "fg"): "KXUCLGAME",
    ("ucl", "asc", "soccer_team_full_game_spread", "fg"): "KXUCLSPREAD",
    ("ucl", "tsc", "soccer_team_full_game_total", "fg"): "KXUCLTOTAL",
    ("bun", "atc", "soccer_team_full_time_winner", "fg"): "KXBUNDESLIGAGAME",
    ("bun", "asc", "soccer_team_full_game_spread", "fg"): "KXBUNDESLIGASPREAD",
    ("bun", "tsc", "soccer_team_full_game_total", "fg"): "KXBUNDESLIGATOTAL",
    ("lal", "atc", "soccer_team_full_time_winner", "fg"): "KXLALIGAGAME",
    ("lal", "asc", "soccer_team_full_game_spread", "fg"): "KXLALIGASPREAD",
    ("lal", "tsc", "soccer_team_full_game_total", "fg"): "KXLALIGATOTAL",
    ("sea", "atc", "soccer_team_full_time_winner", "fg"): "KXSERIEAGAME",
    ("sea", "asc", "soccer_team_full_game_spread", "fg"): "KXSERIEASPREAD",
    ("sea", "tsc", "soccer_team_full_game_total", "fg"): "KXSERIEATOTAL",
    ("lg1", "atc", "soccer_team_full_time_winner", "fg"): "KXLIGUE1GAME",
    ("lg1", "asc", "soccer_team_full_game_spread", "fg"): "KXLIGUE1SPREAD",
    ("lg1", "tsc", "soccer_team_full_game_total", "fg"): "KXLIGUE1TOTAL",
    ("mls", "atc", "soccer_team_full_time_winner", "fg"): "KXMLSGAME",
    ("mls", "asc", "soccer_team_full_game_spread", "fg"): "KXMLSSPREAD",
    ("mls", "tsc", "soccer_team_full_game_total", "fg"): "KXMLSTOTAL",
    ("lmx", "atc", "soccer_team_full_time_winner", "fg"): "KXLIGAMXGAME",
    ("lmx", "asc", "soccer_team_full_game_spread", "fg"): "KXLIGAMXSPREAD",
    ("lmx", "tsc", "soccer_team_full_game_total", "fg"): "KXLIGAMXTOTAL",
    ("nfl", "tsc", "football_game_first_half_total", "1h"): "KXNFL1HTOTAL",
    ("nfl", "tsc", "football_game_first_quarter_total", "1q"): "KXNFL1QTOTAL",
    ("nfl", "asc", "football_team_first_half_spread", "1h"): "KXNFL1HSPREAD",
    ("nfl", "asc", "football_team_first_quarter_spread", "1q"): "KXNFL1QSPREAD",
    ("cfb", "asc", "football_team_first_half_spread", "1h"): "KXNCAAF1HSPREAD",
    ("nfl", "atc", "football_team_first_half_winner", "1h"): "KXNFL1H",
    ("nfl", "atc", "football_team_second_half_winner", "2h"): "KXNFL2H",
    ("nfl", "atc", "football_team_first_quarter_winner", "1q"): "KXNFL1Q",
    ("nfl", "atc", "football_team_second_quarter_winner", "2q"): "KXNFL2Q",
    ("nfl", "atc", "football_team_third_quarter_winner", "3q"): "KXNFL3Q",
    ("nfl", "atc", "football_team_fourth_quarter_winner", "4q"): "KXNFL4Q",
    ("cfb", "atc", "football_team_first_half_winner", "1h"): "KXNCAAF1H",
    ("epl", "tsc", "soccer_team_first_half_total", "1h"): "KXEPL1HTOTAL",
    ("ucl", "tsc", "soccer_team_first_half_total", "1h"): "KXUCL1HTOTAL",
    ("bun", "tsc", "soccer_team_first_half_total", "1h"): "KXBUNDESLIGA1HTOTAL",
    ("lal", "tsc", "soccer_team_first_half_total", "1h"): "KXLALIGA1HTOTAL",
    ("sea", "tsc", "soccer_team_first_half_total", "1h"): "KXSERIEA1HTOTAL",
    ("lg1", "tsc", "soccer_team_first_half_total", "1h"): "KXLIGUE11HTOTAL",
    ("epl", "asc", "soccer_team_first_half_spread", "1h"): "KXEPL1HSPREAD",
    ("epl", "asc", "soccer_team_second_half_spread", "2h"): "KXEPL2HSPREAD",
    ("ucl", "asc", "soccer_team_first_half_spread", "1h"): "KXUCL1HSPREAD",
    ("bun", "asc", "soccer_team_first_half_spread", "1h"): "KXBUNDESLIGA1HSPREAD",
    ("lal", "asc", "soccer_team_first_half_spread", "1h"): "KXLALIGA1HSPREAD",
    ("sea", "asc", "soccer_team_first_half_spread", "1h"): "KXSERIEA1HSPREAD",
    ("lg1", "asc", "soccer_team_first_half_spread", "1h"): "KXLIGUE11HSPREAD",
    ("epl", "atc", "soccer_team_first_half_winner", "1h"): "KXEPL1H",
    ("ucl", "atc", "soccer_team_first_half_winner", "1h"): "KXUCL1H",
    ("mlb", "atc", "baseball_team_first_five_winner", "f5"): "KXMLBF5",
    ("uslc", "atc", "soccer_team_full_time_winner", "fg"): "KXUSLGAME",
    ("eflc", "atc", "soccer_team_full_time_winner", "fg"): "KXEFLCUPGAME",
    ("eflc", "asc", "soccer_team_full_game_spread", "fg"): "KXEFLCUPSPREAD",
    ("eflc", "tsc", "soccer_team_full_game_total", "fg"): "KXEFLCUPTOTAL",
    ("eflch", "atc", "soccer_team_full_time_winner", "fg"): "KXEFLCHAMPIONSHIPGAME",
    ("sld", "atc", "soccer_team_full_time_winner", "fg"): "KXDENSUPERLIGAGAME",
    ("ecu1", "atc", "soccer_team_full_time_winner", "fg"): "KXECULPGAME",
    ("uel", "atc", "soccer_team_full_time_winner", "fg"): "KXUELGAME",
    ("uaepl", "atc", "soccer_team_full_time_winner", "fg"): "KXUAEPLGAME",
    ("spl", "atc", "soccer_team_full_time_winner", "fg"): "KXSAUDIPLGAME",
    ("pl1", "atc", "soccer_team_full_time_winner", "fg"): "KXPERLIGA1GAME",
    ("pdc", "atc", "soccer_team_full_time_winner", "fg"): "KXCHLLDPGAME",
    ("lpa", "atc", "soccer_team_full_time_winner", "fg"): "KXARGPREMDIVGAME",
    ("alsv", "atc", "soccer_team_full_time_winner", "fg"): "KXALLSVENSKANGAME",
    ("brb", "atc", "soccer_team_full_time_winner", "fg"): "KXBRASILEIROBGAME",
    ("cplcr", "aec", "cricket_match_winner", "fg"): "KXCPLMATCH",
}

EVENT_ANCHOR_SERIES = {
    "mlb": "KXMLBGAME",
    "cfb": "KXNCAAFGAME",
    "nfl": "KXNFLGAME",
    "epl": "KXEPLGAME",
    "ucl": "KXUCLGAME",
    "bun": "KXBUNDESLIGAGAME",
    "lal": "KXLALIGAGAME",
    "sea": "KXSERIEAGAME",
    "lg1": "KXLIGUE1GAME",
    "mls": "KXMLSGAME",
    "lmx": "KXLIGAMXGAME",
    "uslc": "KXUSLGAME",
    "eflc": "KXEFLCUPGAME",
    "eflch": "KXEFLCHAMPIONSHIPGAME",
    "sld": "KXDENSUPERLIGAGAME",
    "ecu1": "KXECULPGAME",
    "uel": "KXUELGAME",
    "uaepl": "KXUAEPLGAME",
    "spl": "KXSAUDIPLGAME",
    "pl1": "KXPERLIGA1GAME",
    "pdc": "KXCHLLDPGAME",
    "lpa": "KXARGPREMDIVGAME",
    "alsv": "KXALLSVENSKANGAME",
    "brb": "KXBRASILEIROBGAME",
    "cplcr": "KXCPLMATCH",
    "ufc": "KXUFCFIGHT",
}

PROP_SERIES_MAP = {
    "baseball_player_home_runs": "KXMLBHR",
    "baseball_player_hits": "KXMLBHIT",
    "baseball_player_hits_runs_rbis": "KXMLBHRR",
    "baseball_player_total_bases": "KXMLBTB",
    "baseball_player_strikeouts": "KXMLBKS",
    "baseball_player_outs": "KXMLBOUTS",
    "baseball_team_first_inning_run": "KXMLBRFI",
    "baseball_game_extra_innings": "KXMLBEXTRAS",
    "ufc_go_the_distance": "KXUFCDISTANCE",
    "football_player_passing_yards": "KXNFLPASSYDS",
    "football_player_passing_touchdowns": "KXNFLPASSTDS",
    "football_player_receiving_yards": "KXNFLRECYDS",
    "football_player_rushing_yards": "KXNFLRSHYDS",
    "football_player_receptions": "KXNFLREC",
    "football_player_interceptions_thrown": "KXNFLPASSINT",
    "football_game_overtime": "KXNFLOT",
    "football_game_total_defensive_special_teams_touchdowns": "KXNFLDSTTD",
}

LINE_TOKEN_RE = re.compile(r"^(\d+)pt5$")
GTE_TOKEN_RE = re.compile(r"^gte(\d+)$")
EVENT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")
NON_FULL_GAME_TOKENS = {
    "f5", "fh", "sh", "1h", "2h", "1q", "2q", "3q", "4q",
    "q1", "q2", "q3", "q4", "i1", "i2", "i3", "i4", "i5",
    "i6", "i7", "i8", "i9",
}
PERIOD_TYPE_SEGMENTS = (
    ("first_half", "1h"),
    ("second_half", "2h"),
    ("first_quarter", "1q"),
    ("second_quarter", "2q"),
    ("third_quarter", "3q"),
    ("fourth_quarter", "4q"),
)
SYMBOL_SEGMENT_TOKENS = {
    "f5": "f5", "fh": "1h", "1h": "1h", "sh": "2h", "2h": "2h",
    "1q": "1q", "q1": "1q", "2q": "2q", "q2": "2q",
    "3q": "3q", "q3": "3q", "4q": "4q", "q4": "4q",
}

SINGLE_MARKET_PROP_SERIES = {
    "KXMLBRFI", "KXMLBEXTRAS",
    "KXUFCDISTANCE",
    "KXEPLBTTS", "KXUCLBTTS", "KXBUNDESLIGABTTS", "KXLALIGABTTS",
    "KXSERIEABTTS", "KXLIGUE1BTTS", "KXMLSBTTS", "KXLIGAMXBTTS",
    "KXEPL1HBTTS", "KXUCL1HBTTS", "KXBUNDESLIGA1HBTTS", "KXLALIGA1HBTTS", "KXLIGUE11HBTTS",
    "KXNFLOT", "KXNFLDSTTD",
}

LEAGUE_PROP_SERIES_MAP = {
    ("epl", "soccer_game_btts"): "KXEPLBTTS",
    ("ucl", "soccer_game_btts"): "KXUCLBTTS",
    ("bun", "soccer_game_btts"): "KXBUNDESLIGABTTS",
    ("lal", "soccer_game_btts"): "KXLALIGABTTS",
    ("sea", "soccer_game_btts"): "KXSERIEABTTS",
    ("lg1", "soccer_game_btts"): "KXLIGUE1BTTS",
    ("mls", "soccer_game_btts"): "KXMLSBTTS",
    ("lmx", "soccer_game_btts"): "KXLIGAMXBTTS",
    ("epl", "soccer_game_first_half_btts"): "KXEPL1HBTTS",
    ("ucl", "soccer_game_first_half_btts"): "KXUCL1HBTTS",
    ("bun", "soccer_game_first_half_btts"): "KXBUNDESLIGA1HBTTS",
    ("lal", "soccer_game_first_half_btts"): "KXLALIGA1HBTTS",
    ("lg1", "soccer_game_first_half_btts"): "KXLIGUE11HBTTS",
}

CACHED_LINK_MAX_AGE_DAYS = 30


def normalize_sportradar_id(value):
    if (value is None):
        return None
    normalized = str(value).strip().lower()
    prefix = "sr:sport_event:"
    if normalized.startswith(prefix):
        normalized = normalized[len(prefix):]
    return normalized or None


def _metadata(instrument):
    metadata = instrument.get("metadata") if isinstance(instrument, Mapping) else None
    return metadata if isinstance(metadata, Mapping) else {}


def _instrument_symbol(instrument):
    if (not isinstance(instrument, Mapping)):
        return None
    symbol = str(instrument.get("symbol") or "").strip()
    return symbol or None


def _instrument_product(instrument):
    metadata = _metadata(instrument)
    product = str(metadata.get("instrument_product") or "").strip().lower()
    if product:
        return product
    symbol = _instrument_symbol(instrument)
    return symbol.split("-", 1)[0].lower() if symbol else None


def _canonical_segment(instrument):
    metadata = _metadata(instrument)
    market_sport_type = str(metadata.get("market_sport_type") or "").lower()
    if ("first_five" in market_sport_type):
        return "f5"
    if ("full_game" in market_sport_type):
        return "fg"

    symbol = _instrument_symbol(instrument) or ""
    tokens = symbol.lower().split("-")
    for (needle, segment) in PERIOD_TYPE_SEGMENTS:
        if (needle in market_sport_type):
            if any((token in SYMBOL_SEGMENT_TOKENS) and (SYMBOL_SEGMENT_TOKENS[token] != segment)
                   for token in tokens):
                return None
            return segment
    if ("f5" in tokens):
        return "f5"
    if any(token in NON_FULL_GAME_TOKENS for token in tokens):
        return None
    return "fg"


def configured_series_for_instrument(instrument):
    metadata = _metadata(instrument)
    event_series = str(metadata.get("event_series") or "").strip().lower()
    product = _instrument_product(instrument)
    market_sport_type = str(metadata.get("market_sport_type") or "").strip().lower()
    if (product == "astatc"):
        return (LEAGUE_PROP_SERIES_MAP.get((event_series, market_sport_type))
                or PROP_SERIES_MAP.get(market_sport_type))
    segment = _canonical_segment(instrument)
    if (not event_series) or (not product) or (not market_sport_type) or (not segment):
        return None
    key = (event_series, product, market_sport_type, segment)
    return PRODUCT_SERIES_MAP.get(key)


def configured_leagues():
    leagues = {key[0] for key in PRODUCT_SERIES_MAP}
    leagues |= {key[0] for key in LEAGUE_PROP_SERIES_MAP}
    leagues |= set(EVENT_ANCHOR_SERIES)
    return frozenset(leagues)


def required_kalshi_series(instruments, manual_overrides=None):
    overrides = manual_overrides if isinstance(manual_overrides, Mapping) else {}
    required = set()
    for instrument in (instruments or []):
        symbol = _instrument_symbol(instrument)
        if symbol and (symbol in overrides):
            continue
        series = configured_series_for_instrument(instrument)
        if series:
            required.add(series)
            event_series = str(_metadata(instrument).get("event_series") or "").strip().lower()
            anchor_series = EVENT_ANCHOR_SERIES.get(event_series)
            if anchor_series:
                required.add(anchor_series)
    return sorted(required)


def _parse_decimal(value):
    if (value is None) or (value == ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _parse_line_token(token):
    match = LINE_TOKEN_RE.match(str(token or "").lower())
    if (match is None):
        return None
    return Decimal(match.group(1)) + Decimal("0.5")


def _symbol_line(instrument):
    symbol = _instrument_symbol(instrument) or ""
    tokens = symbol.lower().split("-")
    if (not tokens):
        return None
    line = _parse_line_token(tokens[-1])
    if (line is None):
        return None
    if (_instrument_product(instrument) == "asc") and (len(tokens) >= 2):
        if (tokens[-2] == "neg"):
            return -line
        if (tokens[-2] == "pos"):
            return line
        return None
    return line


def _instrument_line(instrument):
    metadata_line = _parse_decimal(_metadata(instrument).get("outcome_strike"))
    return metadata_line if (metadata_line is not None) else _symbol_line(instrument)


def _prop_floor_strike(instrument):
    metadata = _metadata(instrument)
    threshold = _parse_decimal(metadata.get("outcome_strike"))
    symbol = _instrument_symbol(instrument) or ""
    match = GTE_TOKEN_RE.match(symbol.lower().split("-")[-1])
    symbol_threshold = Decimal(match.group(1)) if match else None
    if (threshold is not None) and (symbol_threshold is not None) and (threshold != symbol_threshold):
        return "poisoned_metadata_mismatch"
    if (threshold is None):
        threshold = symbol_threshold
    if (threshold is None):
        return None
    if (threshold <= 0) or (threshold != threshold.to_integral_value()):
        return None
    return threshold - Decimal("0.5")


def _market_floor_strike(market):
    # floor_strike is the only place Kalshi states the line; ticker suffixes are indices, not numbers.
    if (not isinstance(market, Mapping)):
        return None
    return _parse_decimal(market.get("floor_strike"))


def _normalize_name(value):
    if (value is None):
        return ""
    folded = unicodedata.normalize("NFKD", str(value))
    ascii_value = folded.encode("ascii", "ignore").decode("ascii").lower()
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value))


def _alias_values(name, aliases):
    if (not isinstance(aliases, Mapping)):
        return []
    normalized_name = _normalize_name(name)
    values = []
    for canonical, configured in aliases.items():
        if (_normalize_name(canonical) != normalized_name):
            continue
        if isinstance(configured, str):
            values.append(configured)
        elif isinstance(configured, (list, tuple, set)):
            values.extend(configured)
    return values


def _name_match_rung(label, target, aliases):
    normalized_label = _normalize_name(label)
    normalized_target = _normalize_name(target)
    if (not normalized_label) or (not normalized_target):
        return None
    if (normalized_label == normalized_target):
        return "exact_name"
    for alias in _alias_values(target, aliases):
        if (normalized_label == _normalize_name(alias)):
            return "alias_name"
    return None


PERIOD_WINNER_SUFFIX_RE = re.compile(
    r"\s+wins\s+(?:(?:1st|2nd|3rd|4th)\s+(?:half|quarter)|first\s+5\s+innings)\s*$",
    re.IGNORECASE,
)
REG_TIME_PREFIX_RE = re.compile(r"^\s*reg\s+time:\s*", re.IGNORECASE)


def _market_label(market, product):
    # yes_sub_title is Kalshi's label for the yes side; every name rung is decided against it.
    label = REG_TIME_PREFIX_RE.sub("", str(market.get("yes_sub_title") or "").strip())
    if (product == "astatc"):
        return label.split(":", 1)[0].strip()
    if (product == "asc"):
        label = re.split(
            r"\s+wins?\s+(?:(?:the\s+)?(?:1h|2h|1q|2q|3q|4q)\s+)?by\s+(?:over|more\s+than)\b",
            label, maxsplit=1, flags=re.IGNORECASE,
        )[0].strip()
        return re.split(
            r"\s+-\d+(?:\.\d+)?\s+first\s+5\s+innings\s*$",
            label,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()
    if (product == "atc"):
        return PERIOD_WINNER_SUFFIX_RE.split(label, maxsplit=1)[0].strip()
    return label


def _build_milestone_index(milestones):
    index = defaultdict(list)
    seen = defaultdict(set)
    for milestone in (milestones or []):
        if (not isinstance(milestone, Mapping)):
            continue
        # Kalshi numbers its external ids; source_3_id is the Sportradar one (docs/schemas.md).
        source_ids = milestone.get("source_ids") or {}
        source_id = normalize_sportradar_id(source_ids.get("source_3_id"))
        if (not source_id):
            continue
        milestone_id = str(milestone.get("id") or "")
        dedupe_key = milestone_id or repr(sorted(milestone.items()))
        if (dedupe_key in seen[source_id]):
            continue
        seen[source_id].add(dedupe_key)
        index[source_id].append(milestone)
    return index


DRAW_LABELS = frozenset({"tie", "draw"})
PERIOD_DRAW_LABEL_RE = re.compile(r"^(?:tie|draw) (?:1st|2nd|3rd|4th) (?:half|quarter)$")


def _is_draw_label(label):
    normalized = _normalize_name(REG_TIME_PREFIX_RE.sub("", str(label or "")))
    return (normalized in DRAW_LABELS) or (PERIOD_DRAW_LABEL_RE.match(normalized) is not None)

KICKOFF_TOLERANCE_SECONDS = 6 * 3600


def _milestone_title_teams(title):
    text = str(title or "")
    for separator in (" vs. ", " vs ", " v. ", " v "):
        if (separator in text):
            (home, away) = text.split(separator, 1)
            if home.strip() and away.strip():
                return (home.strip(), away.strip())
    return None


def _parse_event_start(value):
    text = str(value or "").strip()
    if (not text):
        return None
    text = text.replace("Z", "+00:00").replace(" ", "T", 1)
    if re.search(r"[+-]\d{2}$", text):
        text = text + ":00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if (parsed.tzinfo is None):
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _build_name_date_index(milestones):
    index = defaultdict(list)
    for milestone in (milestones or []):
        if (not isinstance(milestone, Mapping)):
            continue
        teams = _milestone_title_teams(milestone.get("title"))
        epoch = _parse_event_start(milestone.get("start_date"))
        if (teams is None) or (epoch is None):
            continue
        index[int(epoch // 86400)].append((epoch, teams[0], teams[1], milestone))
    return index


def _group_event_name_date(instruments):
    homes = set()
    aways = set()
    starts = set()
    for instrument in instruments:
        metadata = _metadata(instrument)
        home = str(metadata.get("home_team_name") or "").strip()
        away = str(metadata.get("away_team_name") or "").strip()
        epoch = _parse_event_start(metadata.get("event_start_time"))
        if home:
            homes.add(home)
        if away:
            aways.add(away)
        if (epoch is not None):
            starts.add(epoch)
    if (len(homes) != 1) or (len(aways) != 1) or (len(starts) != 1):
        return None
    return (next(iter(homes)), next(iter(aways)), next(iter(starts)))


# each Kalshi label must identify its club strictly better than the other club; a tie is refused
def _teams_correspond(home, away, kalshi_home, kalshi_away, aliases):
    if (_name_match_rung(kalshi_home, home, aliases) is None):
        return False
    if (_name_match_rung(kalshi_home, away, aliases) is not None):
        return False
    if (_name_match_rung(kalshi_away, away, aliases) is None):
        return False
    if (_name_match_rung(kalshi_away, home, aliases) is not None):
        return False
    return True


def _name_date_link(instruments, name_date_index, aliases):
    if (not name_date_index):
        return (None, "no_sportradar_id")
    group = _group_event_name_date(instruments)
    if (group is None):
        return (None, "no_sportradar_id")
    (home, away, epoch) = group
    day = int(epoch // 86400)
    candidates = {}
    mismatched = 0
    for bucket in (day - 1, day, day + 1):
        for (candidate_epoch, kalshi_home, kalshi_away, milestone) in name_date_index.get(bucket, ()):
            if (not _teams_correspond(home, away, kalshi_home, kalshi_away, aliases)):
                continue
            if (abs(candidate_epoch - epoch) > KICKOFF_TOLERANCE_SECONDS):
                mismatched += 1
                continue
            milestone_id = str(milestone.get("id") or "") or repr(sorted(milestone.items()))
            candidates[milestone_id] = milestone
    if (not candidates):
        return (None, "kickoff_mismatch" if mismatched else "no_sportradar_id")
    if (len(candidates) > 1):
        return (None, "ambiguous_name_date_event")
    return (next(iter(candidates.values())), None)


def _build_event_index(events):
    index = {}
    conflicts = defaultdict(set)
    for event in (events or []):
        if (not isinstance(event, Mapping)):
            continue
        event_ticker = str(event.get("event_ticker") or "").strip()
        if (not event_ticker):
            continue
        event_series = str(event.get("series_ticker") or "").strip()
        if event_ticker in conflicts:
            if event_series:
                conflicts[event_ticker].add(event_series)
            continue
        existing = index.get(event_ticker)
        if existing is None:
            index[event_ticker] = event
            continue
        existing_series = str(existing.get("series_ticker") or "").strip()
        if existing_series and event_series and (existing_series != event_series):
            index.pop(event_ticker, None)
            conflicts[event_ticker].update((existing_series, event_series))
            continue
        existing_markets = existing.get("markets") or []
        event_markets = event.get("markets") or []
        if (len(event_markets) >= len(existing_markets)):
            index[event_ticker] = event
    return (index, conflicts)


def _linked_event_tickers(link):
    tickers = []
    seen = set()
    for field in ("primary_event_tickers", "related_event_tickers", "kalshi_primary_event_tickers", "kalshi_related_event_tickers"):
        for value in (link.get(field) or []):
            ticker = str(value or "").strip()
            if ticker and (ticker not in seen):
                seen.add(ticker)
                tickers.append(ticker)
    return tickers


def _select_linked_event(link, expected_series, events_by_ticker, event_conflicts):
    matches = {}
    for event_ticker in _linked_event_tickers(link):
        if expected_series in (event_conflicts.get(event_ticker) or set()):
            return (None, "ambiguous_kalshi_counterpart")
        event = events_by_ticker.get(event_ticker)
        if (not isinstance(event, Mapping)):
            continue
        if (str(event.get("series_ticker") or "") != expected_series):
            continue
        matches[event_ticker] = event
    if (not matches):
        return (None, "no_kalshi_counterpart")
    if (len(matches) > 1):
        return (None, "ambiguous_kalshi_counterpart")
    return (next(iter(matches.values())), None)


def _group_event_source_ids(instruments):
    # Our half of the strong join. Some leagues carry event_external_id_sportsdataio instead, which
    # Kalshi does not publish, so those games fall through to the names + kickoff join.
    source_ids = set()
    for instrument in instruments:
        source_id = normalize_sportradar_id(_metadata(instrument).get("event_external_id_sportradar"))
        if source_id:
            source_ids.add(source_id)
    return source_ids


def _cache_timestamp_age_days(value):
    if (value is None):
        return None
    try:
        text = str(value).strip()
        if (not text):
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        timestamp = datetime.fromisoformat(text)
    except ValueError:
        return None
    if (timestamp.tzinfo is None):
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - timestamp).total_seconds() / 86400.0


def _build_group_context(instruments):
    namesake_ids = defaultdict(set)
    single_market_type_symbols = defaultdict(set)
    for instrument in instruments:
        if (_instrument_product(instrument) != "astatc"):
            continue
        metadata = _metadata(instrument)
        market_sport_type = str(metadata.get("market_sport_type") or "").strip().lower()
        event_series = str(metadata.get("event_series") or "").strip().lower()
        symbol = _instrument_symbol(instrument)
        prop_series = (LEAGUE_PROP_SERIES_MAP.get((event_series, market_sport_type))
                       or PROP_SERIES_MAP.get(market_sport_type))
        if (prop_series in SINGLE_MARKET_PROP_SERIES):
            single_market_type_symbols[market_sport_type].add(symbol)
            continue
        name = _normalize_name(metadata.get("long_participant_name"))
        if name:
            participant_id = str(metadata.get("long_participant_id") or "").strip().lower()
            namesake_ids[name].add(participant_id or f"?{symbol}")
    return {
        "namesake_collisions": {
            name for (name, ids) in namesake_ids.items() if (len(ids) > 1)
        },
        "duplicated_single_market_types": {
            market_sport_type
            for (market_sport_type, symbols) in single_market_type_symbols.items()
            if (len(symbols) > 1)
        },
    }


def _cache_link(event_id, cached_event_mappings):
    if (not isinstance(cached_event_mappings, Mapping)):
        return None
    record = cached_event_mappings.get(event_id)
    if (not isinstance(record, Mapping)):
        return None
    if (str(record.get("pmus_event_id") or "") != event_id):
        return None
    if (not normalize_sportradar_id(record.get("sportradar_event_id"))):
        return None
    if (not str(record.get("kalshi_milestone_id") or "")):
        return None
    if (not _linked_event_tickers(record)):
        return None
    age_days = _cache_timestamp_age_days(record.get("resolved_at"))
    if (age_days is None) or (age_days > CACHED_LINK_MAX_AGE_DAYS):
        return None
    return record


def _event_link(event_id, instruments, milestone_index, cached_event_mappings,
                name_date_index=None, aliases=None):
    source_ids = _group_event_source_ids(instruments)
    if (len(source_ids) > 1):
        return (None, None, None, "poisoned_event_identity")

    source_id = next(iter(source_ids)) if source_ids else None
    cached = _cache_link(event_id, cached_event_mappings)
    cached_source_id = normalize_sportradar_id(cached.get("sportradar_event_id")) if cached else None
    if source_id and cached_source_id and (source_id != cached_source_id):
        return (None, source_id, None, "poisoned_event_identity")

    if source_id:
        live_links = milestone_index.get(source_id) or []
        if (len(live_links) > 1):
            return (None, source_id, None, "ambiguous_kalshi_event")
        if (len(live_links) == 1):
            return (live_links[0], source_id, "sportradar", None)
        if cached and (cached_source_id == source_id):
            return (cached, source_id, "cached_sportradar", None)
        return (None, source_id, None, "kalshi_not_listed_yet")

    if cached:
        return (cached, cached_source_id, "cached_sportradar", None)
    (link, reason) = _name_date_link(instruments, name_date_index, aliases)
    if (link is not None):
        return (link, None, "name_date", None)
    return (None, None, None, reason)


def _result_base(instrument):
    metadata = _metadata(instrument)
    return {
        "pmus_symbol": _instrument_symbol(instrument),
        "pmus_event_id": metadata.get("event_id"),
    }


def _unresolved(instrument, reason):
    result = _result_base(instrument)
    result.update({
        "resolved": False,
        "kalshi_ticker": None,
        "side": None,
        "rung": None,
        "reason": reason,
    })
    return result


def _resolved(instrument, market, side, event_rung, market_rung, source_id, milestone_id):
    ticker = str(market.get("ticker") or "").strip()
    if (not ticker):
        return _unresolved(instrument, "no_kalshi_counterpart")
    result = _result_base(instrument)
    result.update({
        "resolved": True,
        "kalshi_ticker": ticker,
        "side": side,
        "rung": f"{event_rung}_{market_rung}",
        "reason": None,
        "sportradar_event_id": source_id,
        "kalshi_milestone_id": milestone_id,
    })
    return result


def _manual_override(instrument, override):
    if isinstance(override, Mapping):
        ticker = str(override.get("kalshi_ticker") or "").strip()
        side = str(override.get("side") or "").strip().lower()
    elif isinstance(override, (list, tuple)) and (len(override) == 2):
        ticker = str(override[0] or "").strip()
        side = str(override[1] or "").strip().lower()
    else:
        return _unresolved(instrument, "invalid_manual_override")
    if (not ticker) or (side not in {"yes", "no"}):
        return _unresolved(instrument, "invalid_manual_override")
    result = _result_base(instrument)
    result.update({
        "resolved": True,
        "kalshi_ticker": ticker,
        "side": side,
        "rung": "manual_override",
        "reason": None,
    })
    return result


def _single_name_market(instrument, markets, target_name, opponent_name, aliases):
    product = _instrument_product(instrument)
    candidates = []
    for market in markets:
        label = _market_label(market, product)
        if (product == "atc") and _is_draw_label(market.get("yes_sub_title")):
            continue
        rung = _name_match_rung(label, target_name, aliases)
        if (rung is None):
            continue
        if (_name_match_rung(label, opponent_name, aliases) is not None):
            return (None, None, "ambiguous_participant_names")
        candidates.append((market, rung))
    if (not candidates):
        return (None, None, "no_kalshi_counterpart")
    if (len(candidates) > 1):
        return (None, None, "ambiguous_kalshi_counterpart")
    (market, rung) = candidates[0]
    return (market, rung, None)


def _single_strike_market(markets, strike):
    candidates = []
    unexpected = 0
    for market in markets:
        if (str(market.get("strike_type") or "") != "greater"):
            unexpected += 1
            continue
        if (_market_floor_strike(market) != strike):
            continue
        if (re.match(r"\s*over\b", REG_TIME_PREFIX_RE.sub("", str(market.get("yes_sub_title") or "")), re.IGNORECASE) is None):
            continue
        candidates.append(market)
    if (not candidates):
        return (None, ("unexpected_kalshi_market" if (markets and (unexpected == len(markets))) else "no_kalshi_counterpart"))
    if (len(candidates) > 1):
        return (None, "ambiguous_kalshi_counterpart")
    return (candidates[0], None)


def _resolve_moneyline(instrument, markets, event_rung, source_id, milestone_id, aliases):
    metadata = _metadata(instrument)
    target_name = str(metadata.get("long_participant_name") or "").strip()
    opponent_name = str(metadata.get("short_participant_name") or "").strip()
    if (not target_name) or (not opponent_name):
        return _unresolved(instrument, "missing_orientation_metadata")
    (market, name_rung, reason) = _single_name_market(instrument, markets, target_name, opponent_name, aliases)
    if reason:
        return _unresolved(instrument, reason)
    return _resolved(instrument, market, "yes", event_rung, name_rung, source_id, milestone_id)


def _resolve_total(instrument, markets, event_rung, source_id, milestone_id):
    line = _instrument_line(instrument)
    symbol_line = _symbol_line(instrument)
    metadata_line = _parse_decimal(_metadata(instrument).get("outcome_strike"))
    if (metadata_line is not None) and (symbol_line is not None) and (metadata_line != symbol_line):
        return _unresolved(instrument, "poisoned_metadata_mismatch")
    if (symbol_line is None):
        return _unresolved(instrument, "invalid_line")
    if (line is None) or (line <= 0):
        return _unresolved(instrument, "invalid_line")
    (market, reason) = _single_strike_market(markets, line)
    if reason:
        return _unresolved(instrument, reason)
    return _resolved(instrument, market, "yes", event_rung, "exact_strike", source_id, milestone_id)


def _first_event_participant_id(metadata):
    event_id = str(metadata.get("event_id") or "").strip().lower()
    event_series = str(metadata.get("event_series") or "").strip().lower()
    if (not EVENT_ID_RE.match(event_id)) or (not event_series):
        return None
    parts = event_id.split("-")
    if (len(parts) < 3) or (parts[0] != event_series):
        return None
    return f"{event_series}-{parts[1]}"


def _resolve_spread(instrument, markets, event_rung, source_id, milestone_id, aliases):
    metadata = _metadata(instrument)
    first_participant_id = _first_event_participant_id(metadata)
    long_participant_id = str(metadata.get("long_participant_id") or "").strip().lower()
    if (not first_participant_id) or (not long_participant_id):
        return _unresolved(instrument, "missing_orientation_metadata")
    if (long_participant_id != first_participant_id):
        return _unresolved(instrument, "poisoned_metadata_mismatch")

    line = _instrument_line(instrument)
    symbol_line = _symbol_line(instrument)
    metadata_line = _parse_decimal(metadata.get("outcome_strike"))
    if (metadata_line is not None) and (symbol_line is not None) and (metadata_line != symbol_line):
        return _unresolved(instrument, "poisoned_metadata_mismatch")
    if (symbol_line is None):
        return _unresolved(instrument, "invalid_line")
    if (line is None) or (line == 0):
        return _unresolved(instrument, "invalid_line")
    long_name = str(metadata.get("long_participant_name") or "").strip()
    short_name = str(metadata.get("short_participant_name") or "").strip()
    if (not long_name) or (not short_name):
        return _unresolved(instrument, "missing_orientation_metadata")
    if (line < 0):
        (target_name, opponent_name, side) = (long_name, short_name, "yes")
    else:
        (target_name, opponent_name, side) = (short_name, long_name, "no")

    candidates = []
    unexpected = 0
    for market in markets:
        if (str(market.get("strike_type") or "") != "greater"):
            unexpected += 1
            continue
        if (_market_floor_strike(market) != abs(line)):
            continue
        label = _market_label(market, "asc")
        name_rung = _name_match_rung(label, target_name, aliases)
        if (name_rung is None):
            continue
        if (_name_match_rung(label, opponent_name, aliases) is not None):
            return _unresolved(instrument, "ambiguous_participant_names")
        candidates.append((market, name_rung))
    if (not candidates):
        return _unresolved(instrument, ("unexpected_kalshi_market" if (markets and (unexpected == len(markets))) else "no_kalshi_counterpart"))
    if (len(candidates) > 1):
        return _unresolved(instrument, "ambiguous_kalshi_counterpart")
    (market, name_rung) = candidates[0]
    return _resolved(instrument, market, side, event_rung, name_rung, source_id, milestone_id)


def _resolve_prop(instrument, markets, event_rung, source_id, milestone_id, aliases, expected_series, group_context):
    unexpected = 0
    metadata = _metadata(instrument)
    market_sport_type = str(metadata.get("market_sport_type") or "").strip().lower()
    if market_sport_type in (group_context.get("duplicated_single_market_types") or set()):
        return _unresolved(instrument, "ambiguous_pmus_instruments")
    if expected_series in SINGLE_MARKET_PROP_SERIES:
        if (len(markets) != 1):
            return _unresolved(instrument, ("unexpected_kalshi_market" if (markets and (unexpected == len(markets))) else "no_kalshi_counterpart"))
        return _resolved(instrument, markets[0], "yes", event_rung, "single_market", source_id, milestone_id)

    target_name = str(metadata.get("long_participant_name") or "").strip()
    floor_strike = _prop_floor_strike(instrument)
    if (not target_name):
        return _unresolved(instrument, "missing_orientation_metadata")
    if (_normalize_name(target_name) in (group_context.get("namesake_collisions") or set())):
        return _unresolved(instrument, "ambiguous_participant_names")
    if (floor_strike == "poisoned_metadata_mismatch"):
        return _unresolved(instrument, "poisoned_metadata_mismatch")
    if (floor_strike is None):
        return _unresolved(instrument, "invalid_line")

    candidates = []
    for market in markets:
        # strike_type says how Kalshi reads its own floor_strike: "greater" is strictly above it,
        # "greater_or_equal" is at or above, so the same question is written half a point higher.
        strike_type = str(market.get("strike_type") or "")
        market_floor = _market_floor_strike(market)
        if (strike_type == "greater"):
            if (market_floor != floor_strike):
                continue
        elif (strike_type == "greater_or_equal"):
            if (market_floor != floor_strike + Decimal("0.5")):
                continue
        else:
            unexpected += 1
            continue
        name_rung = _name_match_rung(_market_label(market, "astatc"), target_name, aliases)
        if name_rung:
            candidates.append((market, name_rung))
    if (not candidates):
        return _unresolved(instrument, ("unexpected_kalshi_market" if (markets and (unexpected == len(markets))) else "no_kalshi_counterpart"))
    if (len(candidates) > 1):
        return _unresolved(instrument, "ambiguous_kalshi_counterpart")
    (market, name_rung) = candidates[0]
    return _resolved(instrument, market, "yes", event_rung, f"{name_rung}_exact_strike", source_id, milestone_id)


def _resolve_drawable_winner(instrument, markets, event_rung, source_id, milestone_id, aliases):
    metadata = _metadata(instrument)
    symbol = (_instrument_symbol(instrument) or "").lower()
    strike = str(metadata.get("outcome_strike") or "").strip().lower()
    draw_symbol = symbol.endswith("-draw")
    draw_strike = (strike == "draw")
    if (draw_symbol != draw_strike):
        return _unresolved(instrument, "poisoned_metadata_mismatch")
    if draw_symbol:
        candidates = [market for market in markets if _is_draw_label(market.get("yes_sub_title"))]
        if (not candidates):
            return _unresolved(instrument, "no_kalshi_counterpart")
        if (len(candidates) > 1):
            return _unresolved(instrument, "ambiguous_kalshi_counterpart")
        return _resolved(instrument, candidates[0], "yes", event_rung, "draw_label", source_id, milestone_id)

    target_name = str(metadata.get("long_participant_name") or "").strip()
    home = str(metadata.get("home_team_name") or "").strip()
    away = str(metadata.get("away_team_name") or "").strip()
    if (not target_name) or (not home) or (not away):
        return _unresolved(instrument, "missing_orientation_metadata")
    if (_normalize_name(target_name) == _normalize_name(home)):
        opponent_name = away
    elif (_normalize_name(target_name) == _normalize_name(away)):
        opponent_name = home
    else:
        return _unresolved(instrument, "poisoned_metadata_mismatch")
    (market, name_rung, reason) = _single_name_market(instrument, markets, target_name, opponent_name, aliases)
    if reason:
        return _unresolved(instrument, reason)
    return _resolved(instrument, market, "yes", event_rung, name_rung, source_id, milestone_id)


def _resolve_market(instrument, linked_event, event_rung, source_id, milestone_id,
                    team_aliases, prop_aliases, expected_series, group_context):
    markets = [market for market in (linked_event.get("markets") or []) if isinstance(market, Mapping)]
    product = _instrument_product(instrument)
    if (product == "aec"):
        return _resolve_moneyline(instrument, markets, event_rung, source_id, milestone_id, team_aliases)
    if (product == "atc"):
        return _resolve_drawable_winner(instrument, markets, event_rung, source_id, milestone_id, team_aliases)
    if (product == "tsc"):
        return _resolve_total(instrument, markets, event_rung, source_id, milestone_id)
    if (product == "asc"):
        return _resolve_spread(instrument, markets, event_rung, source_id, milestone_id, team_aliases)
    if (product == "astatc"):
        return _resolve_prop(instrument, markets, event_rung, source_id, milestone_id, prop_aliases, expected_series, group_context)
    return _unresolved(instrument, "unsupported_product")


# pure: no I/O, every answer is resolved with a rung or refused with a reason
def resolve_instruments(pmus_instruments, kalshi_milestones, kalshi_events,
                        manual_overrides=None, player_aliases=None, cached_event_mappings=None,
                        team_aliases=None):
    overrides = manual_overrides if isinstance(manual_overrides, Mapping) else {}
    prop_aliases = dict(player_aliases) if isinstance(player_aliases, Mapping) else {}
    aliases = dict(team_aliases) if isinstance(team_aliases, Mapping) else {}

    rows_by_symbol = {}
    poisoned_duplicates = set()
    ordered_symbols = []
    for instrument in (pmus_instruments or []):
        symbol = _instrument_symbol(instrument)
        if (not symbol):
            continue
        previous = rows_by_symbol.get(symbol)
        if (previous is None):
            rows_by_symbol[symbol] = instrument
            ordered_symbols.append(symbol)
        elif (previous != instrument):
            poisoned_duplicates.add(symbol)

    results = {}
    groups = defaultdict(list)
    for symbol in ordered_symbols:
        instrument = rows_by_symbol[symbol]
        if (symbol in overrides):
            results[symbol] = _manual_override(instrument, overrides[symbol])
            continue
        if (symbol in poisoned_duplicates):
            results[symbol] = _unresolved(instrument, "poisoned_metadata_mismatch")
            continue
        metadata = _metadata(instrument)
        event_id = str(metadata.get("event_id") or "").strip()
        expected_series = configured_series_for_instrument(instrument)
        if event_id:
            product = _instrument_product(instrument) or ""
            if (not symbol.startswith(f"{product}-{event_id}")):
                results[symbol] = _unresolved(instrument, "poisoned_symbol_event_mismatch")
                continue
            groups[event_id].append(instrument)
        if (expected_series is None):
            results[symbol] = _unresolved(instrument, "unsupported_product")
            continue
        if (not event_id):
            results[symbol] = _unresolved(instrument, "missing_event_id")

    milestone_index = _build_milestone_index(kalshi_milestones)
    name_date_index = _build_name_date_index(kalshi_milestones)
    (events_by_ticker, event_conflicts) = _build_event_index(kalshi_events)
    for event_id, instruments in groups.items():
        (link, source_id, event_rung, event_reason) = _event_link(
            event_id, instruments, milestone_index, cached_event_mappings,
            name_date_index=name_date_index, aliases=aliases)
        if event_reason:
            for instrument in instruments:
                if configured_series_for_instrument(instrument) is None:
                    continue
                results[_instrument_symbol(instrument)] = _unresolved(instrument, event_reason)
            continue
        if (link is None):
            for instrument in instruments:
                if configured_series_for_instrument(instrument) is None:
                    continue
                results[_instrument_symbol(instrument)] = _unresolved(instrument, "no_kalshi_counterpart")
            continue

        milestone_id = str(link.get("id") or link.get("kalshi_milestone_id") or "")
        group_context = _build_group_context(instruments)
        for instrument in instruments:
            expected_series = configured_series_for_instrument(instrument)
            if (expected_series is None):
                results[_instrument_symbol(instrument)] = _unresolved(instrument, "unsupported_product")
                continue
            (linked_event, link_reason) = _select_linked_event(
                link, expected_series, events_by_ticker, event_conflicts,
            )
            if link_reason:
                results[_instrument_symbol(instrument)] = _unresolved(instrument, link_reason)
                continue
            if (linked_event is None):
                results[_instrument_symbol(instrument)] = _unresolved(instrument, "no_kalshi_counterpart")
                continue
            results[_instrument_symbol(instrument)] = _resolve_market(
                instrument, linked_event, event_rung, source_id, milestone_id,
                aliases, prop_aliases, expected_series, group_context)
    return results


def build_event_mapping_updates(pmus_instruments, kalshi_milestones, team_aliases=None):
    groups = defaultdict(list)
    for instrument in (pmus_instruments or []):
        event_id = str(_metadata(instrument).get("event_id") or "").strip()
        if event_id:
            groups[event_id].append(instrument)

    milestone_index = _build_milestone_index(kalshi_milestones)
    updates = {}
    for event_id, instruments in groups.items():
        source_ids = _group_event_source_ids(instruments)
        if (len(source_ids) != 1):
            continue
        source_id = next(iter(source_ids))
        links = milestone_index.get(source_id) or []
        if (len(links) != 1):
            continue
        link = links[0]
        milestone_id = str(link.get("id") or "").strip()
        primary = [str(value) for value in (link.get("primary_event_tickers") or []) if value]
        related = [str(value) for value in (link.get("related_event_tickers") or []) if value]
        if (not milestone_id) or (not primary and not related):
            continue
        updates[event_id] = {
            "pmus_event_id": event_id,
            "sportradar_event_id": source_id,
            "kalshi_milestone_id": milestone_id,
            "kalshi_primary_event_tickers": primary,
            "kalshi_related_event_tickers": related,
            "method": "sportradar_id",
        }
    return updates


def event_stage_outcomes(pmus_instruments, kalshi_milestones, cached_event_mappings=None, team_aliases=None):
    groups = defaultdict(list)
    for instrument in (pmus_instruments or []):
        event_id = str(_metadata(instrument).get("event_id") or "").strip()
        if event_id:
            groups[event_id].append(instrument)

    milestone_index = _build_milestone_index(kalshi_milestones)
    name_date_index = _build_name_date_index(kalshi_milestones)
    outcomes = {}
    for event_id, instruments in groups.items():
        (link, source_id, event_rung, event_reason) = _event_link(
            event_id, instruments, milestone_index, cached_event_mappings,
            name_date_index=name_date_index, aliases=(team_aliases if isinstance(team_aliases, Mapping) else {}))
        milestone_id = str(link.get("id") or link.get("kalshi_milestone_id") or "") if link else None
        outcomes[event_id] = {
            "pmus_event_id": event_id,
            "sportradar_event_id": source_id,
            "event_rung": event_rung,
            "event_reason": event_reason,
            "kalshi_milestone_id": milestone_id or None,
        }
    return outcomes


def validate_player_aliases(aliases):
    if (not isinstance(aliases, Mapping)):
        raise ValueError("player aliases must be a JSON object")
    for (key, value) in aliases.items():
        if (not isinstance(key, str)) or (not key.strip()):
            raise ValueError(f"player alias key must be a non-empty string: {key!r}")
        values = [value] if isinstance(value, str) else value
        if (not isinstance(values, (list, tuple))) or (not values):
            raise ValueError(f"player alias value must be a string or non-empty list: {key!r}")
        for item in values:
            if (not isinstance(item, str)) or (not item.strip()):
                raise ValueError(f"player alias value must be a non-empty string: {key!r}")


def validate_manual_overrides(overrides):
    if (not isinstance(overrides, Mapping)):
        raise ValueError("manual overrides must be a JSON object")
    for (key, value) in overrides.items():
        if (not isinstance(key, str)) or (EVENT_ID_RE.match(key) is None):
            raise ValueError(f"manual override key is not a lowercase PMUS symbol: {key!r}")
        if isinstance(value, Mapping):
            ticker = str(value.get("kalshi_ticker") or "").strip()
            side = str(value.get("side") or "").strip().lower()
        elif isinstance(value, (list, tuple)) and (len(value) == 2):
            ticker = str(value[0] or "").strip()
            side = str(value[1] or "").strip().lower()
        else:
            raise ValueError(f"manual override for {key!r} must be a mapping or a [ticker, side] pair")
        if (not ticker) or (side not in {"yes", "no"}):
            raise ValueError(f"manual override for {key!r} needs a non-empty ticker and side yes|no")
