"""Minimaalinen iCalendar (RFC 5545) -jäsennin: riittää FIS-syötteen VEVENTien lukemiseen."""


def _unfold(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def unescape(value: str) -> str:
    out = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            if nxt in "nN":
                out.append("\n")
                i += 2
                continue
            if nxt in ",;\\":
                out.append(nxt)
                i += 2
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def parse_events(text: str) -> list[dict]:
    """Palauttaa listan VEVENTejä: {PROP: {"value": str, "params": {..}}}."""
    events: list[dict] = []
    current: dict | None = None
    depth_other = 0
    for line in _unfold(text):
        if not line:
            continue
        if line == "BEGIN:VEVENT":
            current = {}
            continue
        if line == "END:VEVENT":
            if current is not None:
                events.append(current)
            current = None
            continue
        if current is None:
            continue
        if line.startswith("BEGIN:"):
            depth_other += 1  # esim. VALARM – ohitetaan
            continue
        if line.startswith("END:"):
            depth_other = max(0, depth_other - 1)
            continue
        if depth_other or ":" not in line:
            continue
        head, value = line.split(":", 1)
        name, *param_parts = head.split(";")
        params = {}
        for part in param_parts:
            if "=" in part:
                k, v = part.split("=", 1)
                params[k.upper()] = v
        current[name.upper()] = {"value": unescape(value), "params": params}
    return events
