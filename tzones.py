"""Time zones (2.92.0): the customer's (an effort's submission) and yours, so a due time is never misread.

Built in, with no time zone database to install: the US zones and their daylight saving time (since 2007 it starts the
second Sunday in March at 2:00 a.m. local and ends the first Sunday in November at 2:00 a.m.), Arizona and Hawaii (no
daylight saving), UTC, and a fixed offset from UTC for anywhere else ("UTC+01:00"). A zone is kept as a short key
(ET, CT, MT, AZ, PT, AK, HI, UTC, or UTC+hh:mm / UTC-hh:mm).

to_utc(naive local datetime, key) and from_utc(utc datetime, key) convert; label(key, when) says EST or EDT; guess(text)
reads what a customer wrote (Mountain Time, 2:00 p.m. ET, MDT, UTC); local_key() guesses this PC's zone from Windows.
Standard library only.
"""
import datetime, re, time

ZONES = {  # key: (name, standard offset hours, has daylight saving, standard abbreviation, daylight abbreviation)
    "ET": ("Eastern", -5, True, "EST", "EDT"),
    "CT": ("Central", -6, True, "CST", "CDT"),
    "MT": ("Mountain", -7, True, "MST", "MDT"),
    "AZ": ("Arizona (Mountain, no daylight time)", -7, False, "MST", "MST"),
    "PT": ("Pacific", -8, True, "PST", "PDT"),
    "AK": ("Alaska", -9, True, "AKST", "AKDT"),
    "HI": ("Hawaii", -10, False, "HST", "HST"),
    "UTC": ("UTC", 0, False, "UTC", "UTC"),
}
KEYS = tuple(ZONES)
_OFF = re.compile(r"^UTC([+-])(\d{1,2})(?::?(\d{2}))?$", re.I)


def valid(key):
    return key in ZONES or bool(_OFF.match(key or ""))


def name(key):
    if key in ZONES:
        return ZONES[key][0]
    return key or ""


def choices():
    """[(key, text)] for a drop-down."""
    return [(k, f"{v[0]} ({v[3]}" + (f"/{v[4]})" if v[2] else ")")) for k, v in ZONES.items()]


def _nth_sunday(year, month, n):
    d = datetime.date(year, month, 1)
    d += datetime.timedelta(days=(6 - d.weekday()) % 7)            # the first Sunday
    return d + datetime.timedelta(weeks=n - 1)


def _dst_utc_bounds(year, std_hours):
    """(start, end) of US daylight saving time in UTC for a zone with that standard offset."""
    start_local = datetime.datetime.combine(_nth_sunday(year, 3, 2), datetime.time(2))     # 2:00 standard time
    end_local = datetime.datetime.combine(_nth_sunday(year, 11, 1), datetime.time(2))      # 2:00 daylight time
    return start_local - datetime.timedelta(hours=std_hours), end_local - datetime.timedelta(hours=std_hours + 1)


def offset_at_utc(key, utc):
    """Hours east of UTC for the zone at that UTC moment (naive UTC datetime)."""
    if key in ZONES:
        _n, std, dst, _a, _b = ZONES[key]
        if dst:
            a, b = _dst_utc_bounds(utc.year, std)
            if a <= utc < b:
                return std + 1
        return std
    m = _OFF.match(key or "")
    if m:
        h = int(m.group(2)) + int(m.group(3) or 0) / 60
        return h if m.group(1) == "+" else -h
    return None


def to_utc(local, key):
    """A naive local time in the zone -> naive UTC (None for an unknown zone). In the hour the clocks go back, the
    first (daylight) time is meant; a time skipped when they go forward is read as standard time."""
    if not valid(key):
        return None
    if key in ZONES:
        std = ZONES[key][1]
        guess = local - datetime.timedelta(hours=std)                # as standard time
        off = offset_at_utc(key, guess - datetime.timedelta(hours=1))
        utc = local - datetime.timedelta(hours=off)
        return utc if offset_at_utc(key, utc) == off else guess
    return local - datetime.timedelta(hours=offset_at_utc(key, local))


def from_utc(utc, key):
    off = offset_at_utc(key, utc)
    return None if off is None else utc + datetime.timedelta(hours=off)


def convert(local, src, dst):
    u = to_utc(local, src)
    return from_utc(u, dst) if u is not None and valid(dst) else None


def label(key, local=None):
    """EST or EDT (for that local time), the key otherwise."""
    if key in ZONES:
        v = ZONES[key]
        if not v[2] or local is None:
            return v[3] if not v[2] else key
        u = to_utc(local, key)
        return v[4] if offset_at_utc(key, u) != v[1] else v[3]
    return key or ""


def guess(text):
    """The zone a customer wrote ('Mountain Time', 'MDT', '2:00 PM EST', 'Eastern Standard Time', 'UTC', 'Zulu') -> key
    or ''."""
    t = " ".join(str(text or "").split()).lower()
    if not t:
        return ""
    if valid(t.upper()):
        return t.upper() if t.upper() in ZONES else t.upper()
    words = {"eastern": "ET", "central": "CT", "mountain": "MT", "pacific": "PT", "alaska": "AK", "hawaii": "HI",
             "arizona": "AZ", "zulu": "UTC", "gmt": "UTC", "utc": "UTC", "coordinated universal": "UTC"}
    for w, k in words.items():
        if w in t:
            return "AZ" if k == "MT" and "arizona" in t else k
    abbr = {"est": "ET", "edt": "ET", "et": "ET", "cst": "CT", "cdt": "CT", "ct": "CT", "mst": "MT", "mdt": "MT", "mt": "MT",
            "pst": "PT", "pdt": "PT", "pt": "PT", "akst": "AK", "akdt": "AK", "hst": "HI", "z": "UTC"}
    for tok in re.findall(r"[a-z]+", t):
        if tok in abbr:
            return abbr[tok]
    m = re.search(r"utc\s*([+-])\s*(\d{1,2})(?::?(\d{2}))?", t)
    if m:
        return f"UTC{m.group(1)}{int(m.group(2)):02d}:{m.group(3) or '00'}"
    return ""


def local_key():
    """This PC's zone, guessed from Windows (its standard offset and whether it keeps daylight time)."""
    std = -time.timezone / 3600
    has_dst = bool(time.daylight)
    for k, v in ZONES.items():
        if v[1] == std and v[2] == has_dst and k != "UTC":
            return k
    if std == 0 and not has_dst:
        return "UTC"
    sign = "+" if std >= 0 else "-"
    h = abs(std)
    return f"UTC{sign}{int(h):02d}:{int(round((h % 1) * 60)):02d}"


def fmt(local, key, with_zone=True):
    """'Dec 15, 2026, 2:00 p.m. EST'."""
    h = local.hour % 12 or 12
    s = f"{local.strftime('%b')} {local.day}, {local.year}, {h}:{local.minute:02d} {'a.m.' if local.hour < 12 else 'p.m.'}"
    return s + (f" {label(key, local)}" if with_zone and key else "")


def fmt_time(local, key=""):
    h = local.hour % 12 or 12
    return f"{h}:{local.minute:02d} {'a.m.' if local.hour < 12 else 'p.m.'}" + (f" {label(key, local)}" if key else "")


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def my_zone(settings=None):
    """The person's own time zone (Settings), else this PC's."""
    k = (settings or {}).get("my_zone", "")
    return k if valid(k) else local_key()


def both(local, key, mine):
    """'Dec 15, 2026, 2:00 p.m. EST' and, when the person's zone differs, '12:00 p.m. MST your time' ('' otherwise)."""
    first = fmt(local, key)
    if not key or not mine or key == mine:
        return first, ""
    other = convert(local, key, mine)
    if other is None:
        return first, ""
    day = "" if other.date() == local.date() else f"{other.strftime('%b')} {other.day}, "
    return first, f"{day}{fmt_time(other, mine)} your time"
