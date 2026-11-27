#!/usr/bin/env python3
"""Turn a merged corpus run into the compatibility chart.

    progress.py corpus.json history.csv compat.svg [--date YYYY-MM-DD]

Reads the merged results (a list of xtask SiteResult objects), puts each site
in its furthest stage, appends or replaces today's row in history.csv, and
draws compat.svg from the whole history.

The results come from jobs that ran third-party code, so they are untrusted:
only numbers and booleans are read from them, and no string from them reaches
the SVG except a version number that must look like one.
"""

import csv
import datetime
import json
import re
import sys

STAGES = [
    ("config", "Config doesn't load"),
    ("blocked", "Config loads, pages refused"),
    ("some", "Some pages build"),
    ("all", "Every page builds"),
    ("identical", "Byte-identical to 11ty"),
]
# One-hue ordinal ramps, light->dark with progress (validated with the
# dataviz skill's validator, --ordinal, on #fcfcfb and #1a1a19).
LIGHT = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]
DARK = ["#184f95", "#256abf", "#3987e5", "#6da7ec", "#b7d3f6"]
FIELDS = ["date", "brrrty", "sites", "excluded"] + [k for k, _ in STAGES] + [
    "pages_identical",
    "pages_total",
]


def num(v):
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else 0


def get(d, *path):
    for p in path:
        if not isinstance(d, dict):
            return None
        d = d.get(p)
    return d


def stage(r):
    """The site's furthest stage, or None when 11ty itself didn't build it."""
    if get(r, "reference", "ok") is not True:
        return None
    ref = num(r.get("reference_files"))
    c = r.get("compare") if isinstance(r.get("compare"), dict) else {}
    if (
        ref > 0
        and num(c.get("identical")) == ref
        and not any(num(c.get(k)) for k in ("different", "missing", "extra", "equivalent"))
    ):
        return "identical"
    total = num(get(r, "doctor", "pages_total"))
    building = num(get(r, "doctor", "pages_building"))
    if total == 0:
        return "config"
    if building == 0:
        return "blocked"
    if building < total:
        return "some"
    return "all"


def summarize(results, date):
    row = {f: 0 for f in FIELDS}
    row["date"] = date
    versions = set()
    for r in results:
        if not isinstance(r, dict):
            continue
        row["sites"] += 1
        s = stage(r)
        if s is None:
            row["excluded"] += 1
            continue
        row[s] += 1
        row["pages_total"] += num(r.get("reference_files"))
        row["pages_identical"] += num(get(r, "compare", "identical"))
        m = re.fullmatch(r"brrrty (\d+\.\d+\.\d+)", str(r.get("brrrty", "")))
        if m:
            versions.add(m.group(1))
    row["brrrty"] = max(versions, key=lambda v: tuple(map(int, v.split(".")))) if versions else ""
    return row


def load_history(path):
    try:
        with open(path, newline="") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []


def save_history(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def svg(history):
    W, H = 760, 330
    pad = 24
    last = history[-1]
    n = lambda r, k: int(r.get(k) or 0)
    counted = sum(n(last, k) for k, _ in STAGES)
    pages_t, pages_i = n(last, "pages_total"), n(last, "pages_identical")
    pct = f"{100 * pages_i / pages_t:.1f}%" if pages_t else "0%"
    ver = last.get("brrrty") or ""
    out = []
    a = out.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
      f'role="img" aria-label="Brrrty corpus compatibility: {n(last, "identical")} of {counted} sites byte-identical">')
    css = ["svg{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif}",
           ".bg{fill:#fcfcfb}.t1{fill:#1f1f1e}.t2{fill:#5e5d59}.grid{stroke:#e4e3df}"]
    css += [f".s{i}{{fill:{c}}}" for i, c in enumerate(LIGHT)]
    dark = [".bg{fill:#1a1a19}.t1{fill:#ecebe8}.t2{fill:#a3a29d}.grid{stroke:#383835}"]
    dark += [f".s{i}{{fill:{c}}}" for i, c in enumerate(DARK)]
    a("<style>" + "".join(css) + "@media (prefers-color-scheme:dark){" + "".join(dark) + "}</style>")
    a(f'<rect class="bg" width="{W}" height="{H}" rx="8"/>')
    a(f'<text class="t1" x="{pad}" y="34" font-size="17" font-weight="600">Corpus compatibility</text>')
    sub = (f"{counted} public 11ty sites, rebuilt daily with Brrrty {('v' + ver) if ver else 'main'}"
           f" · pages byte-identical: {pages_i:,} of {pages_t:,} ({pct})")
    a(f'<text class="t2" x="{pad}" y="56" font-size="13">{sub}</text>')

    # Today: one segmented bar, 2px gaps, 4px rounded ends.
    x0, bw, by, bh = pad, W - 2 * pad, 72, 26
    x = x0
    segs = [(i, n(last, k)) for i, (k, _) in enumerate(STAGES) if n(last, k)]
    for j, (i, c) in enumerate(segs):
        w = bw * c / counted if counted else 0
        gap = 2 if j < len(segs) - 1 else 0
        a(f'<rect class="s{i}" x="{x:.1f}" y="{by}" width="{max(w - gap, 1):.1f}" height="{bh}" rx="4"/>')
        x += w

    # Legend with counts (identity never by color alone).
    lx, ly = pad, by + bh + 26
    for i, (k, label) in enumerate(STAGES):
        txt = f"{label} {n(last, k)}"
        a(f'<rect class="s{i}" x="{lx}" y="{ly - 10}" width="10" height="10" rx="2"/>')
        a(f'<text class="t1" x="{lx + 15}" y="{ly}" font-size="12">{txt}</text>')
        lx += 15 + 7 * len(txt) + 18
        if lx > W - 160 and i < len(STAGES) - 1:
            lx, ly = pad, ly + 20

    # History: one stacked column per run.
    hx, hy, hw, hh = pad + 26, ly + 30, W - 2 * pad - 26, H - (ly + 30) - 50
    top = max((sum(n(r, k) for k, _ in STAGES) for r in history), default=1) or 1
    for frac in (0, 0.5, 1):
        y = hy + hh - hh * frac
        a(f'<line class="grid" x1="{hx}" x2="{hx + hw}" y1="{y:.1f}" y2="{y:.1f}" stroke-width="1"/>')
        a(f'<text class="t2" x="{hx - 6}" y="{y + 4:.1f}" font-size="11" text-anchor="end">{round(top * frac)}</text>')
    shown = history[-60:]
    slot = hw / max(len(shown), 1)
    cw = max(min(slot - 2, 18), 1)
    for idx, r in enumerate(shown):
        cx = hx + idx * slot + (slot - cw) / 2
        y = hy + hh
        for i, (k, _) in enumerate(STAGES):
            c = n(r, k)
            if not c:
                continue
            h = hh * c / top
            a(f'<rect class="s{i}" x="{cx:.1f}" y="{y - h + 1:.1f}" width="{cw:.1f}" height="{max(h - 2, 1):.1f}" rx="1.5"/>')
            y -= h
    a(f'<text class="t2" x="{hx}" y="{hy + hh + 16:.1f}" font-size="11">{shown[0]["date"]}</text>')
    if len(shown) > 1:
        a(f'<text class="t2" x="{hx + hw}" y="{hy + hh + 16:.1f}" font-size="11" text-anchor="end">{shown[-1]["date"]}</text>')
    note = "Sites per stage, by run."
    if n(last, "excluded"):
        note += f" Not counted: {n(last, 'excluded')} where 11ty itself didn't build in the runner."
    a(f'<text class="t2" x="{pad}" y="{H - 10}" font-size="11">{note}</text>')
    a("</svg>")
    return "\n".join(out) + "\n"


def main(argv):
    args = [a for a in argv if not a.startswith("--date")]
    date = datetime.date.today().isoformat()
    for a in argv:
        if a.startswith("--date="):
            date = a.split("=", 1)[1]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise SystemExit("bad --date")
    results_path, history_path, svg_path = args
    results = json.load(open(results_path))
    if not isinstance(results, list):
        raise SystemExit("expected a list of site results")
    row = summarize(results, date)
    history = [r for r in load_history(history_path) if r.get("date") != date] + [row]
    history.sort(key=lambda r: r["date"])
    save_history(history_path, history)
    with open(svg_path, "w") as f:
        f.write(svg(history))
    print(json.dumps(row))


if __name__ == "__main__":
    main(sys.argv[1:])
