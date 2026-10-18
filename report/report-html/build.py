#!/usr/bin/env python3
"""Render a report.json into one self-contained HTML file.

    python3 build.py [--strict] [--check-choice <stem>.choice.json] report.json out.html

Schema: see SKILL.md ("report.json") and the extension skills (report-flow/NOTATION.md, report-diagram, report-table, report-charts, report-video). Every entity gets the anchor
`#e-<id>`, every diagram `#f-<id>`, every diagram node `#f-<id>-<node>`. `refs`,
`{"ref": id}` table cells and diagram nodes link to them; back-links ("cited by")
and drill-down links (from a diagram's `parent`) are computed here, so the data
states each link once.
"""
import os
import hashlib
import html
import re
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

E = html.escape
CITE = re.compile(r"\[@([^\[\]`\n]*)\]")  # inline citation: text without brackets, backticks or newlines
TEMPLATE = Path(__file__).with_name("template.html")
LINKS_SHOWN = 12  # per direction and tree row; the rest is counted
COLORS = {"purple", "blue", "green", "gray", "orange", "pink", "teal", "yellow", "red", "navy", "brown", "ink"}
CHANGE = {"new": "green", "changed": "orange", "removed": "red"}  # `change` value -> mark colour
DIAGRAMS = {"flow", "lineage", "states", "map"}
ID_FIGURES = {"mermaid", "vega", "video"}  # figures with an id and a `#f-<id>` anchor but no nodes; their renderers register below
FIND_TYPES = {"tree", "data"}  # block types that switch on the header find box
PROFILES = {"explanation", "structure", "inventory", "critique", "comparison", "exploration", "change"}  # top-level `profile`
AT_REQUIRED = {"explanation", "structure"}  # profiles in which every flow/map edge needs `at`
LINT_PROSE_WORDS = 60  # a p/bullets/steps block longer than this needs one [[id]] link
LINT_KIND_MIN = 5  # entities of one kind needed before a missing meta key is reported
HEAD = {}  # block type -> HTML for <head> (CDN tags); added once when a block of that type is in the report
HEAD["mermaid"] = (
    '<script type="module">\n'
    'import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";\n'
    'mermaid.initialize({startOnLoad: false, securityLevel: "strict", theme: "neutral", '
    'fontFamily: "JetBrains Mono, monospace", suppressErrorRendering: true});\n'
    'await mermaid.run({querySelector: "pre.mermaid", suppressErrors: true});\n'
    'document.querySelectorAll("pre.mermaid svg").forEach(s => s.classList.add("dg"));\n'
    '</script>')
HEAD["data"] = (
    '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/simple-datatables@10/dist/style.css">\n'
    '<script type="module">\n'
    'import {DataTable, exportCSV} from "https://cdn.jsdelivr.net/npm/simple-datatables@10/dist/module.js";\n'
    'window.DT = {DataTable, exportCSV}; dispatchEvent(new Event("dt-ready"));\n'
    '</script>')
HEAD["vega"] = (  # classic UMD builds; `defer` scripts run before DOMContentLoaded, where the template's vgInit() starts
    '<script defer src="https://cdn.jsdelivr.net/npm/vega@6"></script>\n'
    '<script defer src="https://cdn.jsdelivr.net/npm/vega-lite@6"></script>\n'
    '<script defer src="https://cdn.jsdelivr.net/npm/vega-embed@7"></script>')
VEGA_SCHEMA = "https://vega.github.io/schema/vega-lite/v6.json"
DATA_TYPES = {"number", "date", "string"}  # `data` column types
MERMAID_HREF = re.compile(r'\bclick\s+\S+\s+(?:href\s+)?"#([^"]+)"')  # in-page `click <node> href "#id"` targets
SHAPES = {"process", "store", "external", "decision", "data", "state"}
EDGE_KINDS = {"flow", "error", "opt"}
PSEUDO = "[*]"  # UML initial (as source) / final (as target) pseudo-state, as in Mermaid
CH = {13: 7.8, 12: 7.2, 11: 6.6}  # advance width of the mono font per px size
TXT = {
    "de": {"ev": "Belege", "el": "Element", "at": "Beleg", "from": "Von", "to": "Nach", "fn": "Funktion",
           "note": "Änderung", "trigger": "Auslöser", "guard": "Bedingung", "up": "Teil von",
           "process": "Prozess", "store": "Datenspeicher", "external": "extern", "boundary": "Nachbar aus der Elternebene",
           "decision": "Entscheidung", "data": "Datentyp", "state": "Zustand", "pseudo": "Start · Ende",
           "flow": "Fluss", "error": "Fehlerpfad", "opt": "optional", "drill": "Detaildiagramm",
           "new": "NEU", "changed": "GEÄNDERT", "removed": "ENTFERNT", "since": "Änderungen seit",
           "dimmed": "Unverändertes ist abgeblendet.", "full": "Alles voll zeigen",
           "zoom": "Vergrößern: zoomen und verschieben", "toggle": "Klicken: diese Kanten aus- oder einblenden",
           "m_fit": "Einpassen", "m_reset": "Anordnung zurücksetzen", "m_all": "Alle aktiv",
           "m_copy": "Anordnung kopieren", "m_full": "Vollbild",
           "m_hint": "Kasten klicken: ausgrauen · ⌘/Strg-Klick oder ↗: Link · Kasten ziehen: verschieben · "
                     "Hintergrund ziehen: schwenken · ⌘/Strg + Mausrad oder zwei Finger: zoomen · "
                     "Anordnung und Ausgegrautes bleiben in diesem Browser",
           "find": "Suchen…", "csv": "CSV", "chart_cdn": "Diagramm braucht das vega-CDN",
           "t_hint": "Klicken Sie auf ein Badge: Es schaltet den Wert ein oder aus.",
           "t_reset": "Zurücksetzen", "t_count": "sichtbar", "sources": "Quellen und Laufdetails"},
    "en": {"ev": "Evidence", "el": "Element", "at": "Evidence", "from": "From", "to": "To", "fn": "Function",
           "note": "Change", "trigger": "Trigger", "guard": "Guard", "up": "Part of",
           "process": "process", "store": "data store", "external": "external", "boundary": "neighbour from parent level",
           "decision": "decision", "data": "data type", "state": "state", "pseudo": "start · end",
           "flow": "flow", "error": "error path", "opt": "optional", "drill": "detail diagram",
           "new": "NEW", "changed": "CHANGED", "removed": "REMOVED", "since": "Changes since",
           "dimmed": "Unchanged parts are dimmed.", "full": "Show all at full contrast",
           "zoom": "Enlarge: zoom and pan", "toggle": "Click: hide or show these edges",
           "m_fit": "Fit", "m_reset": "Reset layout", "m_all": "All active",
           "m_copy": "Copy layout", "m_full": "Full screen",
           "m_hint": "click a box: grey it out · ⌘/Ctrl-click or ↗: link · drag a box: move · "
                     "drag the background: pan · ⌘/Ctrl + wheel or two fingers: zoom · "
                     "layout and greyed boxes stay in this browser",
           "find": "Find…", "csv": "CSV", "chart_cdn": "Chart needs the vega CDN",
           "t_hint": "Click a badge to switch the value on or off.",
           "t_reset": "Reset", "t_count": "visible", "sources": "Sources and run details"},
}


def fail(msg):
    sys.exit(f"report.json: {msg}")


def warn(msg):
    print(f"report.json: warning: {msg}", file=sys.stderr)


def as_list(v):
    return v if isinstance(v, list) else [v]


def edge_of(e):
    """Edge as dict; the list form [from, to, label?, kind?] stays valid."""
    if isinstance(e, dict):
        return {"label": "", "kind": "flow", **e}
    return {"from": e[0], "to": e[1], "label": e[2] if len(e) > 2 else "", "kind": e[3] if len(e) > 3 else "flow"}


def walk(blocks):
    """Every block, including the ones nested in `tabs`."""
    for b in blocks:
        yield b
        for t in b.get("tabs", []) if b.get("type") == "tabs" else []:
            yield from walk(t.get("blocks", []))


def changes(x):
    """Every `change` value anywhere in the report data."""
    if isinstance(x, dict):
        if "change" in x:
            yield x["change"]
        for v in x.values():
            yield from changes(v)
    elif isinstance(x, list):
        for v in x:
            yield from changes(v)


def diagram_nodes(b):
    """Node ids a diagram block exposes as drill-down / anchor targets."""
    if b["type"] in ID_FIGURES:
        return []
    if b["type"] in ("flow", "map"):
        return [n["id"] for n in b["nodes"]]
    if b["type"] == "lineage":
        return [t["id"] for t in b["types"]]
    return [s["id"] for s in b["states"]]


class Report:
    def __init__(self, data, out_dir=None, src=None):
        self.d = data
        self.out_dir = out_dir  # directory of the output HTML; media (`video`) resolves against it
        self.src = src  # path of report.json; the data dump (`count` stats) resolves against it
        self.lints = []  # lint lines; printed by main() after the build
        self.cats = data.get("badges", {})
        self.ents = {e["id"]: e for e in data.get("entities", [])}
        if len(self.ents) != len(data.get("entities", [])):
            fail("duplicate entity id")
        self.kids = defaultdict(list)
        self.back = defaultdict(list)
        for e in data.get("entities", []):
            if e.get("parent") is not None:
                if e["parent"] not in self.ents:
                    fail(f"entity {e['id']}: unknown parent {e['parent']}")
                self.kids[e["parent"]].append(e)
            for r in e.get("refs", []):
                if r not in self.ents:
                    fail(f"entity {e['id']}: unknown ref {r}")
                self.back[r].append(e["id"])
        for v in self.kids.values():
            v.sort(key=lambda e: e.get("order", 0))
        for c, cat in self.cats.items():
            for k, val in cat["values"].items():
                if val.get("color", "gray") not in COLORS:
                    fail(f"badge {c}:{k}: colour must be one of {sorted(COLORS)}")
        self.t = TXT.get(str(data.get("lang", "de"))[:2], TXT["en"])
        self.ntabs, self.tab_entity = 0, None
        bad = sorted({str(v) for v in changes(data)} - set(CHANGE))
        if bad:
            fail(f"change must be one of {sorted(CHANGE)}, not {', '.join(bad)}")
        self.chg = any(True for _ in changes(data))  # a change document: marks in colour, the rest dimmed
        self.under = False  # inside a `new`/`removed` part: everything below is that, so no more marks
        self.nchg = Counter()
        self.diagrams()
        if data.get("profile") is not None and data["profile"] not in PROFILES:
            fail(f"profile must be one of {sorted(PROFILES)}, not {data['profile']}")
        self.require_at()

    # -- change document -------------------------------------------------
    def changed(self, x):
        """x or anything inside it (blocks, tabs, nodes, edges, rows, items, a tab's or a tree's entities) carries `change`."""
        if isinstance(x, list):
            return any(self.changed(v) for v in x)
        if not isinstance(x, dict):
            return False
        if x.get("change"):
            return True
        if x.get("type") == "tree":
            return any(e.get("change") for e in self.d.get("entities", []) if e.get("tree", True))
        if x.get("entity") in self.ents and self.changed_ent(self.ents[x["entity"]]):
            return True
        return any(self.changed(v) for v in x.values() if isinstance(v, (list, dict)))

    def changed_ent(self, e):
        return bool(e.get("change")) or any(self.changed_ent(k) for k in self.kids.get(e["id"], []))

    def scope(self, kids):
        """Unmarked kids dim only in a change document, outside a new/removed part, next to a marked sibling."""
        return self.chg and not self.under and self.changed(kids)

    def state(self, x, scope, changed=None, count=True):
        """(change, class suffix, mark html) of one item; counts the mark for the header."""
        k = x.get("change") if self.chg and not self.under else None
        if k:
            self.nchg[k] += count
            return k, f" chg c-{k}", self.mark(k)
        if scope and not (changed if changed is not None else self.changed(x)):
            return None, " dim", ""
        return None, "", ""

    def mark(self, k):
        return f'<b class="bg s-square cm" style="--c:var(--{CHANGE[k]});--cb:var(--{CHANGE[k]}-bg)">{E(self.t[k])}</b>'

    def inside(self, k, fn, *args):
        """Render fn(*args); below a new or removed part no further marks or dims."""
        prev, self.under = self.under, self.under or k in ("new", "removed")
        try:
            return fn(*args)
        finally:
            self.under = prev

    # -- diagram hierarchy -------------------------------------------------
    def diagrams(self):
        """Collect diagram blocks, resolve `parent` (drill-down) and check DFD balancing."""
        self.dg, self.dkid = {}, {}
        n = 0
        for sec in self.d.get("sections", []):
            for b in walk(sec.get("blocks", [])):
                if b.get("type") not in DIAGRAMS | ID_FIGURES:
                    continue
                n += 1
                b.setdefault("id", f"d{n}")
                if b["id"] in self.dg:
                    fail(f"duplicate diagram id {b['id']}")
                if len(set(diagram_nodes(b))) != len(diagram_nodes(b)):
                    fail(f"{b['type']} {b['id']}: duplicate node id")
                self.dg[b["id"]] = b
        for b in self.dg.values():
            if b["type"] in ID_FIGURES:
                if b.get("parent"):
                    fail(f"{b['type']} {b['id']}: `parent` applies to flow, lineage, states and map only")
                continue
            if not b.get("parent"):
                continue
            pid, _, nid = b["parent"].partition(":")
            p = self.dg.get(pid)
            if not p or p["type"] != "flow":
                fail(f"{b['type']} {b['id']}: parent {b['parent']} must be <flow id>:<node id>")
            if nid not in diagram_nodes(p):
                fail(f"{b['type']} {b['id']}: flow {pid} has no node {nid}")
            if (pid, nid) in self.dkid:
                fail(f"{b['type']} {b['id']}: node {b['parent']} already drills into {self.dkid[(pid, nid)]}")
            self.dkid[(pid, nid)] = b["id"]
        for b in self.dg.values():
            if b["type"] in ID_FIGURES:
                b["_level"] = 0
                continue
            seen, p = {b["id"]}, b
            while p.get("parent"):
                p = self.dg[p["parent"].partition(":")[0]]
                if p["id"] in seen:
                    fail(f"diagram {b['id']}: parent chain loops")
                seen.add(p["id"])
            b["_level"] = len(seen) - 1
            if b["type"] == "flow" and b.get("parent"):
                self.balance(b)

    def neighbours(self, pid, nid):
        """Parent-flow nodes with an edge into (`in`) or out of (`out`) node nid."""
        es = [edge_of(e) for e in self.dg[pid].get("edges", [])]
        return ([e["from"] for e in es if e["to"] == nid and e["from"] != nid],
                [e["to"] for e in es if e["from"] == nid and e["to"] != nid])

    def balance(self, b):
        """DFD balancing: every flow into/out of the parent node crosses the child's boundary."""
        pid, _, nid = b["parent"].partition(":")
        ins, outs = self.neighbours(pid, nid)
        ids = set(diagram_nodes(b))
        es = [edge_of(e) for e in b.get("edges", [])]
        for m, side, ok in [(m, "outgoing", any(e["from"] == m for e in es)) for m in ins] + \
                           [(m, "incoming", any(e["to"] == m for e in es)) for m in outs]:
            if m not in ids:
                fail(f"flow {b['id']}: add boundary node `{m}` (parent {pid} links it to {nid}; DFD balancing)")
            if not ok:
                fail(f"flow {b['id']}: boundary node `{m}` needs an {side} edge, as in parent {pid}")
        par = {n["id"]: n for n in self.dg[pid]["nodes"]}
        for n in b["nodes"]:
            if n.get("shape") == "external" and n["id"] not in ins + outs and n["id"] not in par:
                warn(f"flow {b['id']}: external `{n['id']}` is missing in parent {pid} (DFD: add it there too)")

    # -- links -----------------------------------------------------------
    def anchor(self, eid):
        return "e-" + str(eid)

    def link(self, eid, text=None):
        """An entity link. Visible text: explicit `text`, else the entity's `label`, else its `title`, else the id.
        The id is only the key; `title` stays the hover text and the anchor never changes."""
        if eid not in self.ents:
            fail(f"unknown ref {eid}")
        e = self.ents[eid]
        shown = text or e.get("label") or e.get("title") or str(eid)
        return f'<a href="#{E(self.anchor(eid))}" title="{E(e.get("title", eid))}">{E(shown)}</a>'

    # -- badges ----------------------------------------------------------
    def badge(self, cat, val, toggle):
        c = self.cats.get(cat)
        if not c or val not in c["values"]:
            fail(f"badge {cat}:{val} is not declared")
        v = c["values"][val]
        col = v.get("color", "gray")
        shape = c.get("shape", "round")
        style = f"--c:var(--{col});--cb:var(--{col}-bg)" if col != "ink" else "--c:var(--ink);--cb:transparent"
        label = E(v.get("label", val))
        if not toggle:
            return f'<span class="bg s-{shape}" style="{style}">{label}</span>'
        k = f"{cat}:{val}"
        return (f'<span class="bg s-{shape} tg" style="{style}" role="button" tabindex="0" '
                f':aria-pressed="!off[\'{k}\']" :class="off[\'{k}\'] &amp;&amp; \'off\'" '
                f'@click="t(\'{k}\')" @keydown.enter.prevent="t(\'{k}\')" @keydown.space.prevent="t(\'{k}\')">{label}</span>')

    # -- blocks ----------------------------------------------------------
    def source(self, value):
        """A source reference as literal text in muted grey brackets: not HTML, not a URL, not an entity ref."""
        return f'<span class="src">[{E(str(value))}]</span>'

    def inline(self, text):
        """Plain text with `code` spans, [[entity-id]] / [[entity-id|label]] links and [@source text] citations.
        A citation is `[@` + text + `]`; the text is non-empty, one line, and has no `[`, `]` or backtick.
        Anything else after `[@` (empty, unclosed, nested, multi-line) stays literal text."""
        out, i = [], 0
        s = str(text)
        while i < len(s):
            if s.startswith("[[", i) and "]]" in s[i:]:
                j = s.index("]]", i)
                ref = s[i + 2:j]
                eid, _, label = ref.partition("|")
                out.append(self.link(eid, label or None))
                i = j + 2
            elif s.startswith("[@", i) and (m := CITE.match(s, i)) and m.group(1).strip():
                out.append(self.source(m.group(1).strip()))
                i = m.end()
            elif s[i] == "`" and "`" in s[i + 1:]:
                j = s.index("`", i + 1)
                out.append(f"<code>{E(s[i + 1:j])}</code>")
                i = j + 1
            else:
                j = min([k for k in (s.find("[[", i + 1), s.find("[@", i + 1), s.find("`", i + 1)) if k != -1] or [len(s)])
                out.append(E(s[i:j]))
                i = j
        return "".join(out)

    def b_p(self, b):
        return f"<p>{self.inline(b['text'])}</p>"

    def items(self, tag, b):
        """List items: inline text, or {text, change} in a change document."""
        scope, out = self.scope(b["items"]), []
        for x in b["items"]:
            x = x if isinstance(x, dict) else {"text": x}
            _, cls, mk = self.state(x, scope)
            out.append(f'<li class="{cls.strip()}">{mk} {self.inline(x["text"])}</li>' if cls else f"<li>{self.inline(x['text'])}</li>")
        return f'<{tag} class="ste">{"".join(out)}</{tag}>'

    def b_bullets(self, b):
        return self.items("ul", b)

    def b_steps(self, b):
        return self.items("ol", b)

    def b_bars(self, b):
        items = b["items"]
        m = max((it[1] for it in items), default=0) or 1
        rows = []
        for it in items:
            label, val = it[0], it[1]
            col = it[2] if len(it) > 2 else b.get("color", "ink")
            lab = self.link(label) if label in self.ents and b.get("link", True) else E(str(label))
            bar = f"--bar:var(--{col})"
            zero = " zero" if val == 0 else ""
            rows.append(f'<tr><th>{lab}</th><td class="n{zero}">{val}</td><td class="b"><span style="width:{val / m * 100:.1f}%;{bar}"></span></td></tr>')
        return '<table class="bars">' + "".join(rows) + "</table>"

    def cell(self, c):
        if isinstance(c, dict):
            if "ref" in c:
                return self.link(c["ref"], c.get("text"))
            if "badge" in c:
                cat, val = c["badge"]
                return self.badge(cat, val, False)
            if "refs" in c:
                return " ".join(self.link(r) for r in c["refs"]) or "—"
        if isinstance(c, (int, float)):
            return f"{c:,}".replace(",", "\u2009")
        return self.inline(c) if c not in (None, "") else "—"

    def b_table(self, b):
        cols = b["columns"]
        num = set(b.get("numeric", []))
        head = "".join(f'<th class="{"n" if i in num else ""}">{E(c)}</th>' for i, c in enumerate(cols))
        rows, scope = [], self.scope(b["rows"])
        for r in b["rows"]:
            cells, rid, rcls, mk = r, None, "", ""
            if isinstance(r, dict):
                cells, rid = r["cells"], r.get("anchor")
                _, rcls, mk = self.state(r, scope)
            elif scope:
                rcls = " dim"
            tds = []
            for i, c in enumerate(cells):
                cls = []
                if i in num:
                    cls.append("n")
                    if c == 0:
                        cls.append("zero")
                if i == 0:
                    cls.append("nw")
                tds.append(f'<td class="{" ".join(cls)}">{mk if i == 0 else ""}{self.cell(c)}</td>')
            idattr = f' id="{E(self.anchor(rid))}"' if rid is not None else ""
            clsattr = f' class="{rcls.strip()}"' if rcls else ""
            rows.append(f"<tr{idattr}{clsattr}>{''.join(tds)}</tr>")
        return f'<div class="tw"><table><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'

    def b_data(self, b):
        """Interactive table: a plain `<table class="dt">` that the template upgrades with simple-datatables
        (sort, search, pages, CSV). Without JS or CDN the plain table shows; the CSV button stays hidden."""
        did = b.get("id")
        if not did:
            fail("data: needs an id")
        cols, rows = b.get("columns") or [], b.get("rows") or []
        if not cols:
            fail(f"data {did}: needs `columns`")
        if not all(isinstance(c, dict) and c.get("key") is not None for c in cols):
            fail(f"data {did}: every column needs a key")
        keys = [c["key"] for c in cols]
        if len(set(keys)) != len(keys):
            fail(f"data {did}: duplicate column key")
        for c in cols:
            if c.get("type", "string") not in DATA_TYPES:
                fail(f"data {did}: column {c['key']}: type must be one of {sorted(DATA_TYPES)}, not {c['type']}")
        key = b.get("key")
        if key is not None and key not in keys:
            fail(f"data {did}: key {key} is not a column key")
        for i, r in enumerate(rows, 1):
            bad = [k for k in r if k not in keys]
            if bad:
                fail(f"data {did}: row {i}: unknown column key {', '.join(bad)}")
        page = b.get("page", 25)
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            fail(f"data {did}: page must be a positive integer")
        listen = b.get("listen")
        if listen is not None:
            if not isinstance(listen, dict) or not all(isinstance(listen.get(k), str) for k in ("chart", "param", "field")):
                fail(f"data {did}: listen needs chart, param and field")
            chart = self.dg.get(listen["chart"])
            if not chart or chart["type"] != "vega":
                fail(f"data {did}: listen.chart must be a vega block, not {listen['chart']}")
            if listen["field"] not in keys:
                fail(f"data {did}: listen.field {listen['field']} is not a column key")

            def params(x):
                if isinstance(x, dict):
                    yield from (p for p in x["params"] if isinstance(p, dict)) if isinstance(x.get("params"), list) else ()
                    for v in x.values():
                        yield from params(v)
                elif isinstance(x, list):
                    for v in x:
                        yield from params(v)
            p = next((p for p in params(chart.get("spec", {})) if p.get("name") == listen["param"]), None)
            if p is None:
                fail(f"data {did}: listen.param {listen['param']} is not a param of vega {listen['chart']}")
            sel = p.get("select")
            if (sel.get("type") if isinstance(sel, dict) else sel) != "point":
                fail(f"data {did}: listen.param {listen['param']} must be a point selection (select.type \"point\"), not {sel}")
        num = [i for i, c in enumerate(cols) if c.get("type") == "number"]
        head = "".join(("<th class=\"n\">" if i in num else "<th>") + E(str(c.get("label", c["key"]))) + "</th>" for i, c in enumerate(cols))
        body = []
        for r in rows:
            tds = []
            for i, c in enumerate(cols):
                v = r.get(c["key"])
                if c["key"] == key and isinstance(v, (str, int)) and not isinstance(v, bool) and v in self.ents:
                    inner = self.link(v)
                elif i in num and isinstance(v, (int, float)) and not isinstance(v, bool):
                    inner = str(v)  # no thousands space: the table script parses the cell text as a number
                else:
                    inner = self.cell(v)
                cls = " ".join(x for x in ("n" if i in num else "", "zero" if i in num and v == 0 else "") if x)
                tds.append(f'<td class="{cls}">{inner}</td>' if cls else f"<td>{inner}</td>")
            kv = r.get(key) if key is not None else None
            de = f' data-e="{E(str(kv))}"' if isinstance(kv, (str, int)) and not isinstance(kv, bool) and kv in self.ents else ""
            body.append(f"<tr{de}>{''.join(tds)}</tr>")
        cap = f'<b>{E(b["label"])}</b>' if b.get("label") else ""
        if not rows:
            warn(f"data {did}: no rows" + (", listen ignored" if listen else ""))
            body = [f'<tr><td colspan="{len(cols)}">—</td></tr>']
            return (f'<figure class="fg" id="{E(self.danchor(did))}"><figcaption>{cap}</figcaption><div class="tw"><table>'
                    f'<thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div></figure>')
        cfg = {"page": page, "num": num, **({"listen": {**listen, "col": keys.index(listen["field"])}} if listen else {})}  # col: position of listen.field
        csv = (f'<button type="button" class="csv" data-dt="{E(did)}" hidden title="{E(self.t["csv"])}">{E(self.t["csv"])}</button>')
        return (f'<figure class="fg" id="{E(self.danchor(did))}"><figcaption>{cap}{csv}</figcaption><div class="tw">'
                f'<table class="dt" id="dt-{E(did)}" data-dt="{E(json.dumps(cfg, ensure_ascii=False))}">'
                f'<thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div></figure>')

    # -- diagrams --------------------------------------------------------
    @staticmethod
    def danchor(gid, nid=None):
        return f"f-{gid}" + (f"-{nid}" if nid is not None else "")

    def node_href(self, b, n):
        """Drill-down child first, then entity ref. Returns (href, drill)."""
        if n.get("ref") and n["ref"] not in self.ents:
            fail(f"{b['type']} {b['id']}: node {n['id']}: unknown ref {n['ref']}")
        kid = self.dkid.get((b["id"], n["id"]))
        if kid:
            return "#" + self.danchor(kid), True
        return ("#" + self.anchor(n["ref"]) if n.get("ref") else None), False

    def layout(self, b, nodes, edges, right):
        """rank (along the flow) and slot (across) per node: manual col/row, or
        longest path over the edges minus back edges; a source moves up to one rank before its
        nearest successor and takes the free slot nearest to its successors. Barycentre sweeps in
        both directions order each rank (fewer crossings); the slot stays near the predecessors' mean."""
        ids = [n["id"] for n in nodes]
        manual = [n for n in nodes if "col" in n or "row" in n]
        if manual:
            if len(manual) != len(nodes):
                fail(f"{b['type']} {b['id']}: give col and row to every node or to none")
            return ({n["id"]: n["col"] if right else n["row"] for n in nodes},
                    {n["id"]: n["row"] if right else n["col"] for n in nodes})
        succ = defaultdict(list)
        for e in edges:
            if e["from"] != e["to"]:
                succ[e["from"]].append(e["to"])
        state, dag = {}, defaultdict(list)

        def dfs(u):
            state[u] = 1
            for v in succ[u]:
                if state.get(v) == 1:
                    continue  # back edge: drawn, but ignored for ranking
                dag[u].append(v)
                if not state.get(v):
                    dfs(v)
            state[u] = 2

        has_in = {v for vs in succ.values() for v in vs}
        for u in [u for u in ids if u not in has_in] + ids:
            if not state.get(u):
                dfs(u)
        rank, indeg, pred, topo = {u: 0 for u in ids}, defaultdict(int), defaultdict(list), []
        for u in ids:
            for v in dag[u]:
                indeg[v] += 1
                pred[v].append(u)
        queue = [u for u in ids if not indeg[u]]
        while queue:
            u = queue.pop(0)
            topo.append(u)
            for v in dag[u]:
                rank[v] = max(rank[v], rank[u] + 1)
                indeg[v] -= 1
                if not indeg[v]:
                    queue.append(v)
        for u in reversed(topo):  # a source has no edge holding it back: its out-edges only get shorter
            if not pred[u] and dag[u]:
                rank[u] = min(rank[v] for v in dag[u]) - 1
        layers = defaultdict(list)
        for u in ids:
            layers[rank[u]].append(u)
        rs = sorted(layers)
        pos = {}

        def index(r):
            for i, u in enumerate(layers[r]):
                pos[u] = (i + .5) / len(layers[r])

        def sweep(order, nb):
            for r in order:
                key = {u: sum(pos[v] for v in nb[u]) / len(nb[u]) if nb[u] else pos[u] for u in layers[r]}
                layers[r].sort(key=key.get)  # stable: ties keep the previous order
                index(r)

        def crossings():
            """Edge pairs between the same two ranks whose ends swap order."""
            by = defaultdict(list)
            for u in ids:
                for v in dag[u]:
                    by[rank[u], rank[v]].append((pos[u], pos[v]))
            return sum(a[0] < b[0] and a[1] > b[1] or a[0] > b[0] and a[1] < b[1]
                       for es in by.values() for i, a in enumerate(es) for b in es[i + 1:])

        for r in rs:
            index(r)
        best = (crossings(), {r: layers[r][:] for r in rs})  # input order wins ties
        for _ in range(4):
            sweep(rs[1:], pred)
            sweep(rs[-2::-1], dag)
            sweep(rs[1:], pred)  # last pass by predecessors, as the slots below
            c = crossings()
            if c < best[0]:
                best = (c, {r: layers[r][:] for r in rs})
        for r in rs:
            layers[r] = best[1][r]
            index(r)
        slot, late = {}, []
        for r in rs:
            nxt = 0
            for u in layers[r]:
                if not pred[u] and r != rs[0]:
                    late.append(u)  # a moved source: placed once its successors have slots
                    continue
                ps = [slot[p] for p in pred[u] if p in slot]
                slot[u] = max(nxt, round(sum(ps) / len(ps)) if ps else nxt)
                nxt = slot[u] + 1
        for u in late:
            taken = {slot[v] for v in layers[rank[u]] if v in slot}
            want = round(sum(slot[v] for v in dag[u]) / len(dag[u]))
            slot[u] = min((s for s in range(max(taken | {want}) + 2) if s not in taken), key=lambda s: (abs(s - want), s))
        return rank, slot

    def graph(self, b, nodes, edges, dirn):
        """Draw nodes and orthogonal edges as SVG. Returns (svg, legend keys used).

        node: id, label, sub?, shape, color?, href?, drill?, boundary?, pseudo? (init|final), at?
        edge: from, to, label, kind
        Edges between neighbouring ranks bend in the gap between them; all others
        leave into the gap after their source and run in the channel beside the
        target's slot, so no edge crosses a box.
        """
        gid, right = b["id"], dirn == "right"
        if dirn not in ("right", "down"):
            fail(f"{b['type']} {gid}: dir must be right or down")
        ids = {n["id"]: n for n in nodes}
        for n in nodes:
            if n.get("shape", "process") not in SHAPES:
                fail(f"{b['type']} {gid}: node {n['id']}: shape must be one of {sorted(SHAPES)}")
            if n.get("color") and n["color"] not in COLORS:
                fail(f"{b['type']} {gid}: node {n['id']}: colour must be one of {sorted(COLORS)}")
        kinds = self.kinds(b)
        for e in edges:
            for k in ("from", "to"):
                if e[k] not in ids:
                    fail(f"{b['type']} {gid}: edge {e['from']} → {e['to']}: unknown node {e[k]}")
            if e["kind"] not in EDGE_KINDS and e["kind"] not in kinds:
                fail(f"{b['type']} {gid}: edge {e['from']} → {e['to']}: kind must be one of "
                     f"{sorted(EDGE_KINDS)} or declared in `kinds`")
        real = [n for n in nodes if not n.get("pseudo")]
        if "box" in b:
            W, H = b["box"]
        else:
            need = max([max(len(n["label"]) * CH[13] + (16 if n.get("drill") else 0), len(n.get("sub") or "") * CH[12])
                        + (40 if n.get("shape") in ("data", "decision") else 26) for n in real] or [120])
            W, H = int(min(max(need, 120), 300)), 58 if any(n.get("sub") for n in real) else 40
        rank, slot = self.layout(b, nodes, edges, right)
        if "gap" in b:
            GM, GC = b["gap"] if right else b["gap"][::-1]
        elif right:
            adj = [len(e["label"]) for e in edges if e["label"] and rank[e["to"]] == rank[e["from"]] + 1]
            GM, GC = int(min(max(48, max(adj or [0]) * CH[11] + 28), 260)), 34
        else:
            GM, GC = (48 if any(e["label"] for e in edges) else 34), 56
        MB, CB = (W, H) if right else (H, W)
        msize = defaultdict(int)
        for u, r in rank.items():
            msize[r] = max(msize[r], 18 if ids[u].get("pseudo") else MB)
        mstart, acc = {}, 0
        for r in range(min(rank.values()), max(rank.values()) + 2):
            mstart[r] = acc
            acc += (msize[r] or MB) + GM
        R = {}  # u -> m0, m1, c0, c1 (box), cc0, cc1 (cell across)
        for u, n in ids.items():
            m, c = mstart[rank[u]], slot[u] * (CB + GC)
            if n.get("pseudo"):
                m0, c0 = m + (msize[rank[u]] - 18) / 2, c + (CB - 18) / 2
                R[u] = (m0, m0 + 18, c0, c0 + 18, c, c + CB)
            else:
                R[u] = (m, m + MB, c, c + CB, c, c + CB)

        def xy(m, c):
            return (m, c) if right else (c, m)

        boxes = []
        out_lab = defaultdict(int)
        for e in edges:
            out_lab[e["from"]] += bool(e["label"])
        pairs = {(e["from"], e["to"]) for e in edges}
        # Ports: three or more edges between neighbouring ranks on one side of a box spread along
        # that side, ordered by the far end; each port sits as near its far end as the side and a
        # minimum gap allow, so an edge to a box straight opposite stays straight. Edges at a
        # spread side bend on their own track in the gap, so they neither share an entry point
        # nor run on top of each other.
        cmid = {u: (R[u][2] + R[u][3]) / 2 for u in ids}
        nbr = [i for i, e in enumerate(edges) if e["from"] != e["to"] and rank[e["to"]] == rank[e["from"]] + 1
               and not ((e["to"], e["from"]) in pairs and slot[e["to"]] == slot[e["from"]])]
        port = {}  # (edge index, "from"|"to") -> across coordinate
        for end, far in (("from", "to"), ("to", "from")):
            side = defaultdict(list)
            for i in nbr:
                side[edges[i][end]].append(i)
            for u, lst in side.items():
                lo, hi = R[u][2] + 10, R[u][3] - 10
                if len(lst) < 3 or (hi - lo) / (len(lst) - 1) < 6:  # too crowded: one shared trunk reads better
                    continue
                lst.sort(key=lambda i: (cmid[edges[i][far]], i))
                step = min(14, (hi - lo) / (len(lst) - 1))
                ps = []
                for i in lst:  # forward: at the far end, or one step after the previous port
                    ps.append(max(min(max(cmid[edges[i][far]], lo), hi), ps[-1] + step if ps else lo))
                for k in range(len(ps) - 1, -1, -1):  # backward: pushed back inside the side
                    ps[k] = min(ps[k], ps[k + 1] - step if k + 1 < len(ps) else hi)
                for i, p in zip(lst, ps):
                    port[i, end] = p
        sp = lambda i: port.get((i, "from"), cmid[edges[i]["from"]])
        tp = lambda i: port.get((i, "to"), cmid[edges[i]["to"]])
        track, into = {}, defaultdict(list)
        for i in {i for i, _ in port}:
            if abs(sp(i) - tp(i)) >= .5:  # a straight edge needs no track
                into[rank[edges[i]["to"]]].append(i)
        for rt, lst in into.items():
            # rightward edges: the one ending furthest right bends first; leftward ones mirrored
            lst.sort(key=lambda i: (0, -tp(i), -sp(i)) if tp(i) >= sp(i) else (1, tp(i), sp(i)))
            lo, hi = mstart[rt] - GM + 8, mstart[rt] - 8
            for k, i in enumerate(lst):
                track[i] = lo + (k + .5) * (hi - lo) / len(lst)
        gap_n, chan_n = defaultdict(int), defaultdict(int)
        drawn, gaps = [], []  # drawn: (points m/c, edge, segment index, label position); gaps: (drawn index, rank, n)
        for i, e in enumerate(edges):
            a, z = e["from"], e["to"]
            s, t = R[a], R[z]
            sm, tm = (s[0] + s[1]) / 2, (t[0] + t[1]) / 2
            sc, tc = port.get((i, "from"), cmid[a]), port.get((i, "to"), cmid[z])
            rs, rt = rank[a], rank[z]
            near = "end" if out_lab[a] > 1 else "start"
            clear = all(not (rs < rank[u] < rt and R[u][2] - 1 <= sc <= R[u][3] + 1) for u in ids)
            if a == z:
                pts = [(s[1] - 24, s[2]), (s[1] - 24, s[2] - 14), (s[1] - 8, s[2] - 14), (s[1] - 8, s[2])]
                seg, where = 1, "loop"
            elif (z, a) in pairs and slot[z] == slot[a] and abs(rt - rs) == 1:
                off = 9 if rt < rs else -9  # a pair in both directions: two parallel lines
                pts = [(s[1], sc + off), (t[0], tc + off)] if rt > rs else [(s[0], sc + off), (t[1], tc + off)]
                seg, where = 0, "lo" if off < 0 else "hi"
            elif rt == rs and abs(slot[z] - slot[a]) == 1:
                off = (9 if slot[z] < slot[a] else -9) if (z, a) in pairs else 0
                pts = [(sm + off, s[3]), (tm + off, t[2])] if slot[z] > slot[a] else [(sm + off, s[2]), (tm + off, t[3])]
                seg, where = 0, "lo" if off < 0 else "hi" if off > 0 else "mid"
            elif rt > rs and abs(sc - tc) < .5 and clear:
                pts, seg, where = [(s[1], sc), (t[0], tc)], 0, near
            elif rt == rs + 1:
                mid = track.get(i, mstart[rt] - GM / 2)
                pts = [(s[1], sc), (mid, sc), (mid, tc), (t[0], tc)]
                seg, where = (2, "end") if near == "end" else (0, "start")
            else:
                if slot[z] > slot[a]:
                    ch, enter, sign, side = t[4] - GC / 2, t[2], -1, s[3]
                else:
                    ch, enter, sign, side = t[5] + GC / 2, t[3], 1, s[2] if slot[z] < slot[a] else s[3]
                key = round(ch)
                ch += sign * 4 * chan_n[key]
                chan_n[key] += 1
                if abs(slot[z] - slot[a]) <= 1:  # channel runs along the source: leave sideways
                    pts, seg, where = [(sm, side), (sm, ch), (tm, ch), (tm, enter)], 0, "start"  # label at the source
                else:  # the bend into the gap after the source rank is set below, once all of them are known
                    gaps.append((len(drawn), rs, gap_n[rs]))
                    gap_n[rs] += 1
                    pts, seg, where = [(s[1], sc), (0, sc), (0, ch), (tm, ch), (tm, enter)], 0, "start"
            drawn.append((pts, e, seg, where))
        for j, rs, k in gaps:  # one track each, all inside the gap
            g = mstart[rs] + (msize[rs] or MB) + GM * .7 - min(5, GM * .5 / max(gap_n[rs] - 1, 1)) * (gap_n[rs] - 1 - k)
            pts = drawn[j][0]
            pts[1], pts[2] = (g, pts[1][1]), (g, pts[2][1])
        drawn = [([xy(*p) for p in pts], e, seg, where) for pts, e, seg, where in drawn]

        node_boxes = []
        for u in ids:
            (bx0, by0), (bx1, by1) = xy(R[u][0], R[u][2]), xy(R[u][1], R[u][3])
            node_boxes.append((bx0, by0, bx1, by1))
        placed = []

        def spots(p, q, where):
            """Label positions (x, y, anchor) along one segment, preferred first."""
            (x1, y1), (x2, y2) = p, q
            if abs(y1 - y2) < .5:
                sg = 1 if x2 >= x1 else -1
                if where == "start":
                    x, anc = x1 + 6 * sg, "start" if sg > 0 else "end"
                elif where == "end":
                    x, anc = x2 - 10 * sg, "end" if sg > 0 else "start"
                else:
                    x, anc = (x1 + x2) / 2, "middle"
                ys = (y1 + 13, y1 - 5) if where == "hi" else (y1 - 5, y1 + 13)
                return [(x, y, anc) for y in ys]
            sg = 1 if y2 >= y1 else -1
            y = {"start": y1 + (14 if sg > 0 else -6), "end": y2 - (8 if sg > 0 else -16)}.get(
                "start" if where in ("lo", "hi") else where, (y1 + y2) / 2 + 4)  # pairs: clear of the mid-gap bus
            sides = [(x1 - 6, "end"), (x1 + 6, "start")]
            if where not in ("loop", "lo"):
                sides.reverse()
            return [(x, y, anc) for x, anc in sides]

        lines = [(min(p[0], q[0]) - 1, min(p[1], q[1]) - 1, max(p[0], q[0]) + 1, max(p[1], q[1]) + 1)
                 for pts, *_ in drawn for p, q in zip(pts, pts[1:])]

        def label_at(pts, seg, where, text, kind, attrs):
            """Least-covered spot (nodes, lines, earlier labels) in preference order: the preferred side,
            the other side, then every other segment of the same edge."""
            w = len(text) * CH[11]
            cands = spots(pts[seg], pts[seg + 1], where)
            for i in range(len(pts) - 1):
                if i != seg:
                    cands += [c for wh in ("mid", "start", "end") for c in spots(pts[i], pts[i + 1], wh)]

            def box(c):
                x, y, anc = c
                x0 = {"start": x, "end": x - w, "middle": x - w / 2}[anc]
                return (x0, y - 10, x0 + w, y + 3)

            def overlap(bx):
                return sum(max(0, min(bx[2], o[2]) - max(bx[0], o[0])) * max(0, min(bx[3], o[3]) - max(bx[1], o[1]))
                           for o in node_boxes + lines + placed)
            x, y, anc = min(cands, key=lambda c: overlap(box(c)))  # first free spot; ties keep preference order
            placed.append(box((x, y, anc)))
            boxes.append(placed[-1])
            return f'<text class="el {kind}"{attrs} x="{x:.1f}" y="{y:.1f}" text-anchor="{anc}">{E(text)}</text>'

        svg_edges, svg_labels, used = [], [], set()
        scope = self.scope(nodes + edges)
        for pts, e, seg, where in drawn:
            used.add(e["kind"])
            cx = self.state(e, scope)[1]
            kc, ks = self.kind_style(kinds, e["kind"])
            attrs = f' data-f="{E(e["from"])}" data-t="{E(e["to"])}" data-k="{E(e["kind"])}"{ks}'  # hover and kind toggles
            d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
            svg_edges.append(f'<path class="ln {kc}{cx}"{attrs} d="{d}" marker-end="url(#m-{E(gid)}-{e["kind"]})"/>')
            for x, y in pts:
                boxes.append((x, y, x, y))
            if e["label"]:
                svg_labels.append(label_at(pts, seg, where, e["label"].replace("`", ""), kc + cx, attrs))  # inline code marks
        svg_nodes = []
        for u, n in ids.items():
            m0, m1, c0, c1 = R[u][:4]
            (x, y), (x2, y2) = xy(m0, c0), xy(m1, c1)
            w, h = x2 - x, y2 - y
            boxes.append((x, y, x2, y2))
            svg_nodes.append(self.node_svg(gid, n, x, y, w, h, used, self.state(n, scope)[1]))
        x0, y0 = min(bx[0] for bx in boxes) - 4, min(bx[1] for bx in boxes) - 4
        wd, ht = math.ceil(max(bx[2] for bx in boxes) + 4 - x0), math.ceil(max(bx[3] for bx in boxes) + 4 - y0)
        marks = "".join(f'<marker id="m-{E(gid)}-{k}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
                        f'<path d="M0,0 L8,4 L0,8" class="mk {self.kind_style(kinds, k)[0]}"{self.kind_style(kinds, k)[1]}/></marker>'
                        for k in sorted(used & (EDGE_KINDS | set(kinds))))
        svg = (f'<svg viewBox="{x0:.1f} {y0:.1f} {wd} {ht}" width="{wd}" height="{ht}" class="dg" role="img" '
               f'style="width:clamp({int(wd * .8)}px,100%,{wd}px);height:auto" '
               f'aria-label="{E(b.get("label") or b["id"])}"><defs>{marks}</defs>'
               + "".join(svg_edges + svg_nodes + svg_labels) + "</svg>")
        return svg, used

    def node_svg(self, gid, n, x, y, w, h, used, chg=""):
        sh = n.get("shape", "process")
        if n.get("pseudo"):
            used.add("pseudo")
            cx, cy = x + w / 2, y + h / 2
            g = (f'<circle cx="{cx}" cy="{cy}" r="8" class="pd"/>' if n["pseudo"] == "init" else
                 f'<circle cx="{cx}" cy="{cy}" r="9" class="pf"/><circle cx="{cx}" cy="{cy}" r="5" class="pd"/>')
            return f'<g class="nd{chg}" id="{E(self.danchor(gid, n["id"]))}" data-n="{E(n["id"])}"><title>{E(n["label"])}</title>{g}</g>'
        used.add("boundary" if n.get("boundary") else sh)
        cls = "bx" + (" ext" if sh == "external" else "") + (" bd" if n.get("boundary") else "")
        col = n.get("color")
        st = f' style="stroke:var(--{col});fill:var(--{col}-bg);stroke-width:1.6"' if col else ""
        if sh == "data":
            k = 10
            body = f'<polygon points="{x + k},{y} {x + w},{y} {x + w - k},{y + h} {x},{y + h}" class="{cls}"{st}/>'
        elif sh == "decision":
            k = 12
            body = (f'<polygon points="{x + k},{y} {x + w - k},{y} {x + w},{y + h / 2} {x + w - k},{y + h} '
                    f'{x + k},{y + h} {x},{y + h / 2}" class="{cls}"{st}/>')
        elif sh == "store":
            body = (f'<path d="M{x + w} {y} H{x} V{y + h} H{x + w}" class="{cls}"{st}/>'
                    f'<path d="M{x + 8} {y} V{y + h}" class="{cls}"{st}/>')
        else:
            rx = ' rx="10"' if sh == "state" else ""
            body = f'<rect x="{x}" y="{y}" width="{w}" height="{h}"{rx} class="{cls}"{st}/>'
        pad = {"data": 18, "decision": 18, "store": 16}.get(sh, 12)
        room = w - pad - 10 - (16 if n.get("drill") else 0)
        lab, sub = n["label"], n.get("sub") or ""

        def cut(s, size):
            k = max(int(room / CH[size]), 4)
            return s if len(s) <= k else s[:k - 1] + "…"
        if sub:
            body += (f'<text x="{x + pad}" y="{y + h / 2 - 7}" class="bt">{E(cut(lab, 13))}</text>'
                     f'<text x="{x + pad}" y="{y + h / 2 + 13}" class="bs">{E(cut(sub, 12))}</text>')
        else:
            body += f'<text x="{x + pad}" y="{y + h / 2 + 4.5}" class="bt">{E(cut(lab, 13))}</text>'
        if n.get("drill"):
            used.add("drill")
            body += self.drill_mark(x + w - 17, y + 5)
        tip = " · ".join(v for v in (self.t.get(n.get("change")), lab, sub, n.get("at")) if v)
        de = f' data-e="{E(str(n["ref"]))}"' if n.get("ref") else ""  # a tree with `drives` filters by it
        g = f'<g class="nd{chg}" id="{E(self.danchor(gid, n["id"]))}" data-n="{E(n["id"])}"{de}><title>{E(tip)}</title>{body}</g>'
        return f'<a class="dgl" href="{E(n["href"])}">{g}</a>' if n.get("href") else g

    @staticmethod
    def drill_mark(x, y):
        """BPMN collapsed sub-process marker: a small square with a plus."""
        return (f'<rect x="{x}" y="{y}" width="11" height="11" class="dz"/>'
                f'<path d="M{x + 2.5} {y + 5.5} H{x + 8.5} M{x + 5.5} {y + 2.5} V{y + 8.5}" class="dzp"/>')

    def legend(self, b, used):
        """Swatches of the shapes and edge kinds in use; with two or more edge kinds each kind is a
        button that hides or shows its edges (template: `kind toggles`)."""
        sw = {
            "process": '<rect x="1" y="2" width="22" height="12" class="bx"/>',
            "state": '<rect x="1" y="2" width="22" height="12" rx="5" class="bx"/>',
            "external": '<rect x="1" y="2" width="22" height="12" class="bx ext"/>',
            "boundary": '<rect x="1" y="2" width="22" height="12" class="bx bd"/>',
            "data": '<polygon points="6,2 23,2 18,14 1,14" class="bx"/>',
            "decision": '<polygon points="6,2 18,2 23,8 18,14 6,14 1,8" class="bx"/>',
            "store": '<path d="M23 2 H1 V14 H23" class="bx"/><path d="M5 2 V14" class="bx"/>',
            "pseudo": '<circle cx="6" cy="8" r="5" class="pd"/><circle cx="18" cy="8" r="5.5" class="pf"/><circle cx="18" cy="8" r="3" class="pd"/>',
            "drill": self.drill_mark(6, 2.5),
        }
        kinds = self.kinds(b)
        ek = [k for k in [*sorted(EDGE_KINDS, key=["flow", "error", "opt"].index), *kinds] if k in used]
        icon = lambda s: f'<svg width="24" height="16" viewBox="0 0 24 16">{s}</svg>'
        out = [f'<span>{icon(sw[k])}{E(self.t[k])}</span>' for k in sw if k in used]
        for k in ek:
            kc, ks = self.kind_style(kinds, k)
            label = E(kinds[k].get("label", k) if k in kinds else self.t[k])
            sym = icon(f'<path d="M1 8 H22" class="ln {kc}"{ks}/>')
            out.append(f'<button type="button" class="lk" data-k="{E(k)}" aria-pressed="true" title="{E(self.t["toggle"])}">{sym}{label}</button>'
                       if len(ek) > 1 else f'<span>{sym}{label}</span>')
        return '<div class="lg">' + "".join(out) + "</div>" if out else ""

    def kinds(self, b):
        """Edge kinds a diagram declares beside flow/error/opt: {kind: {label?, color?, dash?: dash|dot}}."""
        kinds = b.get("kinds", {})
        for k, v in kinds.items():
            if not re.fullmatch(r"[A-Za-z0-9_-]+", k) or k in EDGE_KINDS | SHAPES | {"boundary", "pseudo", "drill"}:
                fail(f"{b['type']} {b['id']}: kind `{k}` must be a new name of letters, digits, - or _")
            if v.get("color", "ink") not in COLORS:
                fail(f"{b['type']} {b['id']}: kind {k}: colour must be one of {sorted(COLORS)}")
            if v.get("dash") not in (None, "dash", "dot"):
                fail(f"{b['type']} {b['id']}: kind {k}: dash must be dash or dot")
        return kinds

    @staticmethod
    def kind_style(kinds, k):
        """(class, style attribute) of one edge kind: built-in kinds by class, declared ones by colour token."""
        if k not in kinds:
            return k, ""
        v = kinds[k]
        return "ck" + (f' {v["dash"]}' if v.get("dash") else ""), f' style="--k:var(--{v.get("color", "ink")})"'

    def figure(self, b, svg, used, caption_extra="", after="", tools=None):
        """Caption, diagram, legend; `tools` replaces the ⤢ zoom button (a map has its own toolbar)."""
        gid = b["id"]
        cap = []
        lvl = b.get("_level", 0)
        if lvl or any(k[0] == gid for k in self.dkid):
            cap.append(f'<span class="lvl">L{lvl}</span>')
        if b.get("label") and b["label"] != self.ents.get(self.tab_entity, {}).get("title"):
            cap.append(f'<b>{E(b["label"])}</b>')
        if b.get("parent"):
            pid, _, nid = b["parent"].partition(":")
            pn = next(n for n in self.dg[pid]["nodes"] if n["id"] == nid)
            up = f'↑ {E(self.t["up"])} <a href="#{E(self.danchor(pid, nid))}">{E(pn.get("label", nid))}</a>'
            if pn.get("ref") and pn["ref"] != self.tab_entity:  # a tab's card already shows its entity
                title = self.ents[pn["ref"]].get("title", "").replace("`", "")
                if title != pn.get("label", nid):
                    up += " · " + self.link(pn["ref"], title or None)
            cap.append(f"<span>{up}</span>")
        if caption_extra:
            cap.append(f"<span>{caption_extra}</span>")
        cap.append(tools if tools is not None else
                   f'<button type="button" class="zb" onclick="zoomFig(this)" title="{E(self.t["zoom"])}" '
                   f'aria-label="{E(self.t["zoom"])}">⤢</button>')
        return (f'<figure class="fg" id="{E(self.danchor(gid))}"><figcaption>{"".join(cap)}</figcaption><div class="dw">{svg}</div>'
                f'{self.legend(b, used)}{after}</figure>')

    def check_evidence(self, b, what, items):
        """`at` on some but not all edges means unproven edges slipped in."""
        missing = [label for label, at in items if not at]
        if missing and len(missing) < len(items):
            warn(f"{b['type']} {b['id']}: {len(missing)} {what} without `at`: {', '.join(missing[:5])}")

    def evidence(self, rows):
        if not rows:
            return ""
        body = "".join(f"<tr><td>{el}</td><td>{self.source(at)}</td></tr>" for el, at in rows)
        return (f'<details class="ev"><summary>{E(self.t["ev"])} · {len(rows)}</summary><div class="tw"><table>'
                f'<thead><tr><th>{E(self.t["el"])}</th><th>{E(self.t["at"])}</th></tr></thead><tbody>{body}</tbody></table></div></details>')

    def grid(self, cols, rows, src=None):
        """Plain table; `src` (one item per row) marks the rows of changed steps or transitions without counting them twice."""
        head = "".join(f"<th>{E(c)}</th>" for c in cols)
        scope, body = self.scope(src or []), []
        for i, r in enumerate(rows):
            _, cls, mk = self.state(src[i], scope, count=False) if src else (None, "", "")
            ca = f' class="{cls.strip()}"' if cls else ""
            body.append(f"<tr{ca}>" + "".join(f"<td>{mk if j == 0 else ''}{c}</td>" for j, c in enumerate(r)) + "</tr>")
        return f'<div class="tw"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'

    def b_flow(self, b):
        """Process/data-flow diagram; a child flow (`parent`) shows the parent node's neighbours as boundary."""
        gid = b["id"]
        pid, _, pnid = (b.get("parent") or "").partition(":")
        ins, outs = self.neighbours(pid, pnid) if pid else ([], [])
        plab = {n["id"]: n.get("label", n["id"]) for n in self.dg[pid]["nodes"]} if pid else {}
        nodes = []
        for n in b["nodes"]:
            href, drill = self.node_href(b, n)
            n2 = {**n, "label": n.get("label", plab.get(n["id"], n["id"])), "href": href, "drill": drill}
            if n["id"] in ins + outs:
                n2["boundary"] = True
                if not drill:
                    other = self.dkid.get((pid, n["id"]))
                    n2["href"] = "#" + (self.danchor(other) if other else self.danchor(pid, n["id"]))
            nodes.append(n2)
        edges = [edge_of(e) for e in b.get("edges", [])]
        lab = {n["id"]: n["label"] for n in nodes}
        erows = [(f'{lab[e["from"]]} → {lab[e["to"]]}' + (f' · {e["label"]}' if e["label"] else ""), e.get("at")) for e in edges]
        self.check_evidence(b, "edges", erows)
        svg, used = self.graph(b, nodes, edges, b.get("dir", "right"))
        rows = [(E(n["label"]), n["at"]) for n in nodes if n.get("at")] + [(E(el), at) for el, at in erows if at]
        return self.figure(b, svg, used, after=self.evidence(rows))

    def b_lineage(self, b):
        """Type transformations: types are nodes, a step's function labels the edge
        (1 → 1) or becomes a job node (n → m), as in OpenLineage dataset → job → dataset."""
        gid = b["id"]
        nodes = []
        for t in b["types"]:
            href, drill = self.node_href(b, t)
            nodes.append({**t, "label": t.get("label", t["id"]), "shape": t.get("shape", "data"), "href": href, "drill": drill})
        lab = {n["id"]: n["label"] for n in nodes}
        edges, rows = [], []
        for i, s in enumerate(b["steps"], 1):
            fr, to = as_list(s["from"]), as_list(s["to"])
            for t in fr + to:
                if t not in lab:
                    fail(f"lineage {gid}: step {s['fn']}: unknown type {t}")
            kind = s.get("kind", "flow")
            if len(fr) == 1 and len(to) == 1:
                edges.append({"from": fr[0], "to": to[0], "label": s["fn"], "kind": kind, "change": s.get("change")})
            else:
                jid = f"job{i}"
                nodes.append({"id": jid, "label": s["fn"], "shape": "process", "change": s.get("change")})
                edges += [{"from": f, "to": jid, "label": "", "kind": kind} for f in fr]
                edges += [{"from": jid, "to": t, "label": "", "kind": kind} for t in to]
            cell = lambda ts: "<br>".join(f'<a href="#{E(self.danchor(gid, t))}">{E(lab[t])}</a>' for t in ts)
            rows.append([cell(fr), f"<code>{E(s['fn'])}</code>", cell(to),
                         self.source(s["at"]) if s.get("at") else "—", self.inline(s.get("note", "")) or "—"])
        self.check_evidence(b, "steps", [(s["fn"], s.get("at")) for s in b["steps"]])
        svg, used = self.graph(b, nodes, edges, b.get("dir", "down"))
        t = self.t
        return self.figure(b, svg, used, after=self.grid([t["from"], t["fn"], t["to"], t["at"], t["note"]], rows, b["steps"]))

    @staticmethod
    def place_pseudo(b, nodes, trs):
        """Manual layout: start one rank before its first target, end one rank after the last state."""
        along, across = ("row", "col") if b.get("dir", "down") == "down" else ("col", "row")
        st = {n["id"]: n for n in nodes if not n.get("pseudo")}
        first = lambda key, other: next((st[x[other]] for x in trs if x[key] == PSEUDO and x[other] in st), None)
        for n in nodes:
            ref = first("from", "to") if n["id"] == "__init" else first("to", "from") if n["id"] == "__final" else None
            if ref:
                last = max(s[along] for s in st.values())
                n.update({along: ref[along] - 1 if n["id"] == "__init" else last + 1, across: ref[across]})
        low = min(n[along] for n in nodes if along in n)
        if low < 0:
            for n in nodes:
                if along in n:
                    n[along] -= low

    def b_states(self, b):
        """UML state machine; `[*]` as source is the initial, as target the final pseudo-state."""
        gid, t = b["id"], self.t
        nodes = []
        trs = b["transitions"]
        if any(x["from"] == PSEUDO for x in trs):
            nodes.append({"id": "__init", "label": "[*] start", "pseudo": "init"})
        for s in b["states"]:
            href, drill = self.node_href(b, s)
            nodes.append({**s, "label": s.get("label", s["id"]), "shape": "state", "href": href, "drill": drill})
        if any(x["to"] == PSEUDO for x in trs):
            nodes.append({"id": "__final", "label": "[*] end", "pseudo": "final"})
        if all("col" in s and "row" in s for s in b["states"]):
            self.place_pseudo(b, nodes, trs)
        slabel = {s["id"]: s.get("label", s["id"]) for s in b["states"]}
        known = set(slabel)
        edges, rows = [], []
        for x in trs:
            for k in ("from", "to"):
                if x[k] != PSEUDO and x[k] not in known:
                    fail(f"states {gid}: transition {x['from']} → {x['to']}: unknown state {x[k]}")
            a = "__init" if x["from"] == PSEUDO else x["from"]
            z = "__final" if x["to"] == PSEUDO else x["to"]
            edges.append({"from": a, "to": z, "label": x.get("label", x.get("trigger", "")), "kind": x.get("kind", "flow"),
                          "change": x.get("change")})
            st = lambda v, n: f"<code>{PSEUDO}</code>" if v == PSEUDO else f'<a href="#{E(self.danchor(gid, n))}">{E(slabel[v])}</a>'
            trig = self.inline(x.get("trigger", "")) + (f" / {self.inline(x['action'])}" if x.get("action") else "")
            rows.append([st(x["from"], a), st(x["to"], z), trig or "—", self.inline(x.get("guard", "")) or "—",
                         self.source(x["at"]) if x.get("at") else "—"])
        reach, todo = set(), [e["from"] for e in edges if e["from"] == "__init"]
        while todo:
            u = todo.pop()
            if u not in reach:
                reach.add(u)
                todo += [e["to"] for e in edges if e["from"] == u]
        if "__init" in reach:
            lost = sorted(known - reach)
            if lost:
                warn(f"states {gid}: not reachable from {PSEUDO}: {', '.join(lost)}")
        self.check_evidence(b, "transitions", [(f"{x['from']} → {x['to']}", x.get("at")) for x in trs])
        svg, used = self.graph(b, nodes, edges, b.get("dir", "down"))
        extra = (f"<code>{E(b['field'])}</code>" if b.get("field") else "") + (f" · {self.source(b['at'])}" if b.get("at") else "")
        return self.figure(b, svg, used, caption_extra=extra,
                           after=self.grid([t["from"], t["to"], t["trigger"], t["guard"], t["at"]], rows, trs))

    def b_map(self, b):
        """Working canvas after the deps-map page: the reader drags boxes, greys them out and pans;
        the template draws curved edges with labels that avoid boxes and keeps the reader's changes
        in localStorage. Here: checks, box sizes and the start layout (layers in barycentre order,
        long rows wrapped so the whole map fits the page), or `pos` as copied with "Copy layout"."""
        gid, t = b["id"], self.t
        nodes, kinds = b["nodes"], self.kinds(b)
        ids = {n["id"]: n for n in nodes}
        edges = [edge_of(e) for e in b.get("edges", [])]
        for n in nodes:
            if n.get("shape", "process") not in ("process", "external"):
                fail(f"map {gid}: node {n['id']}: shape must be process or external")
            if n.get("color") and n["color"] not in COLORS:
                fail(f"map {gid}: node {n['id']}: colour must be one of {sorted(COLORS)}")
        for e in edges:
            for k in ("from", "to"):
                if e[k] not in ids:
                    fail(f"map {gid}: edge {e['from']} → {e['to']}: unknown node {e[k]}")
            if e["from"] == e["to"]:
                fail(f"map {gid}: edge {e['from']} → {e['to']}: a map draws no loops")
            if e["kind"] not in EDGE_KINDS and e["kind"] not in kinds:
                fail(f"map {gid}: edge {e['from']} → {e['to']}: kind must be one of {sorted(EDGE_KINDS)} or declared in `kinds`")
        pos, off = b.get("pos", {}), set(b.get("off", []))
        for u in [*pos, *off]:
            if u not in ids:
                fail(f"map {gid}: pos/off: unknown node {u}")
        for u, p in pos.items():
            if not (isinstance(p, list) and len(p) == 2 and all(isinstance(c, (int, float)) for c in p)):
                fail(f"map {gid}: pos {u}: must be [x, y]")

        def lines_of(v):
            return [str(x) for x in as_list(v) if str(x)] if v else []

        def cut(s, k):
            return s if len(s) <= k else s[:max(k, 4) - 1] + "…"

        # boxes: title, optional sub line, then `lines` in mono; ↗ when the node links somewhere
        size, inner = {}, {}
        for n in nodes:
            u, lab, sub, ls = n["id"], n.get("label", n["id"]), n.get("sub") or "", lines_of(n.get("lines"))
            href = self.node_href(b, n)[0] or n.get("href")
            lk = 18 if href else 0
            need = max([len(lab) * CH[13], len(sub) * CH[12], *(len(s) * CH[12] for s in ls)]) + 28 + lk
            w = int(min(max(math.ceil(need), 160), 360))
            txt, y = [f'<text x="14" y="26" class="bt">{E(cut(lab, int((w - 28 - lk) / CH[13] + 1e-6)))}</text>'], 26
            for s, cls in [(sub, "bs")] * bool(sub) + [(s, "bl") for s in ls]:
                y += 18 if cls == "bs" else 16
                txt.append(f'<text x="14" y="{y}" class="{cls}">{E(cut(s, int((w - 28) / CH[12] + 1e-6)))}</text>')
            if href:
                tgt = "" if href.startswith("#") else ' target="_blank" rel="noopener"'
                txt.append(f'<a href="{E(href)}"{tgt} class="mla"><text x="{w - 20}" y="24" class="mlk">↗</text></a>')
            size[u], inner[u] = (w, y + 14), (lab, sub, href, "".join(txt))

        # start layout as on the deps-map page: ranks top-down, each rank one row, a long row
        # wrapped into sub-rows; the wrap width is the one whose whole map fits VW x VH largest
        VW, VH, GAP, SUB, LAYER = 1100, 640, 40, 56, 110
        rank, slot = self.layout(b, [{"id": u} for u in ids], edges, False)
        rows = [sorted((u for u in ids if rank[u] == r), key=slot.get) for r in sorted(set(rank.values()))]
        rw = lambda r: sum(size[u][0] for u in r) + GAP * (len(r) - 1)
        rh = lambda r: max(size[u][1] for u in r)

        def wrap(r, mw):
            k = max(1, math.ceil(rw(r) / mw))
            target, subs, cum = (rw(r) + GAP) / k, [[] for _ in range(k)], 0
            for u in r:
                wu = size[u][0] + GAP
                subs[min(k - 1, int((cum + wu / 2) // target))].append(u)
                cum += wu
            return [s for s in subs if s]

        def arrange(mw):
            bands = [wrap(r, mw) for r in rows]
            subs = [s for band in bands for s in band]
            h = sum(map(rh, subs)) + SUB * (len(subs) - len(bands)) + LAYER * (len(bands) - 1)
            return bands, max(map(rw, subs)), h

        widest, narrowest = max(map(rw, rows)), max(w for w, _ in size.values())
        best = None
        for s in range(40, -1, -1):  # widest first: ties keep fewer wraps
            a = arrange(narrowest + (widest - narrowest) * s / 40)
            sc = min(VW / (a[1] + 80), VH / (a[2] + 80))
            if not best or sc > best[0] + 1e-9:
                best = (sc, a)
        bands, W, _ = best[1]
        xy, y = {}, 0
        for bi, band in enumerate(bands):
            for si, s in enumerate(band):
                y += (LAYER if si == 0 else SUB) if bi or si else 0
                x = (W - rw(s)) / 2
                for u in s:
                    xy[u] = [round(x), y]
                    x += size[u][0] + GAP
                y += rh(s)
        xy.update({u: list(p) for u, p in pos.items()})

        scope, used, svg_e, svg_l = self.scope(nodes + edges), set(), [], []
        for i, e in enumerate(edges):
            used.add(e["kind"])
            kc, ks = self.kind_style(kinds, e["kind"])
            cls = kc + self.state(e, scope)[1] + (" off" if e["from"] in off or e["to"] in off else "")
            attrs = f' data-f="{E(e["from"])}" data-t="{E(e["to"])}" data-k="{E(e["kind"])}" data-i="{i}"{ks}'
            svg_e.append(f'<path class="ln {cls}"{attrs}/><path class="ah {cls}"{attrs}/>')
            ls = [cut(s.replace("`", ""), 48) for s in lines_of(e["label"])]
            if ls:  # a pill where it fits, else a dot that opens on hover
                lw, lh = math.ceil(max(map(len, ls)) * CH[11]) + 12, 14 * len(ls) + 4
                tx = "".join(f'<tspan x="0" y="{-lh / 2 + 13 + 14 * j:g}">{E(s)}</tspan>' for j, s in enumerate(ls))
                svg_l.append(f'<g class="ml {cls}{" wr" if e.get("warn") else ""}"{attrs} data-w="{lw}" data-h="{lh}">'
                             f'<g class="mlp"><rect x="{-lw / 2:g}" y="{-lh / 2:g}" width="{lw}" height="{lh}" rx="7"/>'
                             f'<text text-anchor="middle">{tx}</text></g><circle r="3.5" class="mld"/></g>')
        svg_n = []
        for n in nodes:
            u, (w, h), (lab, sub, href, txt) = n["id"], size[n["id"]], inner[n["id"]]
            o, col, ext = u in off, n.get("color"), n.get("shape") == "external"
            if ext:
                used.add("external")
            st = f' style="stroke:var(--{col});fill:var(--{col}-bg);stroke-width:1.6"' if col else ""
            tip = " · ".join(v for v in (self.t.get(n.get("change")), lab, sub, n.get("at")) if v)
            dh = (f' data-href="{E(href)}"' if href else "") + (f' data-e="{E(str(n["ref"]))}"' if n.get("ref") else "")
            svg_n.append(f'<g class="nd mn{" off" if o else ""}{self.state(n, scope)[1]}" id="{E(self.danchor(gid, u))}" '
                         f'data-n="{E(u)}" data-w="{w}" data-h="{h}"{dh} transform="translate({xy[u][0]} {xy[u][1]})" '
                         f'tabindex="0" role="button" aria-pressed="{str(o).lower()}"><title>{E(tip)}</title>'
                         f'<rect width="{w}" height="{h}" rx="6" class="bx{" ext" if ext else ""}"{st}/>{txt}</g>')
        x0, y0 = min(p[0] for p in xy.values()) - 20, min(p[1] for p in xy.values()) - 20
        wd = max(xy[u][0] + size[u][0] for u in ids) + 20 - x0
        ht = max(xy[u][1] + size[u][1] for u in ids) + 20 - y0
        # the box keeps the map's aspect, at most at natural size and VH tall, at least 280 px
        # (phone); `height` fixes it
        box = (f'height:{int(b["height"])}px' if b.get("height") else
               f'aspect-ratio:{wd}/{ht};min-height:{min(280, ht)}px;max-height:{min(VH, ht)}px')
        # stored reader changes belong to one build of the map; a new layout or `off` drops them
        ver = hashlib.sha1(json.dumps([sorted(xy.items()), sorted(off), sorted(size.items())]).encode()).hexdigest()[:8]
        svg = (f'<div class="mw" style="{box}"><svg viewBox="{x0} {y0} {wd} {ht}" class="dg mp" data-v="{ver}" '
               f'role="group" aria-label="{E(b.get("label") or gid)}"><g class="me">{"".join(svg_e)}</g>'
               f'{"".join(svg_n)}{"".join(svg_l)}</svg></div>')

        lab = {n["id"]: n.get("label", n["id"]) for n in nodes}
        erows = [(f'{lab[e["from"]]} → {lab[e["to"]]}' + (f' · {" / ".join(lines_of(e["label"]))}' if e["label"] else ""), e.get("at"))
                 for e in edges]
        self.check_evidence(b, "edges", erows)
        rows = [(E(lab[n["id"]]), n["at"]) for n in nodes if n.get("at")] + [(E(el), at) for el, at in erows if at]
        tools = ('<span class="mtb"><span class="mc" aria-live="polite"></span>'
                 + "".join(f'<button type="button" data-m="{k}">{E(t["m_" + k])}</button>' for k in ("fit", "reset", "all", "copy", "full"))
                 + "</span>")
        return self.figure(b, svg, used, after=f'<p class="mh">{E(t["m_hint"])}</p>' + self.evidence(rows), tools=tools)

    def b_tree(self, b):
        filt = b.get("filter", list(self.cats))
        cats = [{"key": c, "mode": self.cats[c].get("filter", "any")} for c in filt]
        kind_cat = b.get("kind", filt[0] if filt else None)
        roots = [e for e in self.d["entities"] if e.get("parent") is None and e.get("tree", True)]
        roots.sort(key=lambda e: e.get("order", 0))
        count_kind = b.get("count")
        scope = self.chg and not self.under and any(self.changed_ent(r) for r in roots)

        def li(e, depth):
            kids = self.kids.get(e["id"], [])
            bvals = e.get("badges", {})
            kind = (bvals.get(kind_cat) or [None])[0]
            kind_badge = "".join(self.badge(kind_cat, v, True) for v in bvals.get(kind_cat, []))
            kind_badge = f'<span class="kb">{kind_badge}</span>' if kind_badge else ""  # one grid cell, however many values
            groups = [f'<span class="id">{E(str(e.get("label") or e["id"]))}</span>'] + self.groups(e, kind_cat, filt)
            lc = ""
            if depth == 0 and kind is not None:
                lc = f' style="--lc:var(--{self.cats[kind_cat]["values"][kind].get("color", "ink")})"'
            cls = ["d0"] if depth == 0 else []
            if kids:
                cls.append("has-kids")
            if e.get("muted"):
                cls.append("muted")
            data = json.dumps({c: bvals.get(c, []) for c in filt if bvals.get(c)}, ensure_ascii=False)
            attrs = f' data-id="{E(str(e["id"]))}" data-b="{E(data)}"'
            if not kids:
                attrs += " data-leaf"
            if (kind == count_kind) if count_kind else not kids:
                attrs += " data-count"
            k, rcls, mk = self.state(e, scope, self.changed_ent(e))
            s = (f'<li class="{" ".join(cls)}"{lc}{attrs} x-show="v[{E(json.dumps(str(e["id"])))}] !== false">'
                 f'<div class="row{rcls}" id="{E(self.anchor(e["id"]))}">{kind_badge}<span class="bd">{mk}'
                 f'<span class="tt">{E(e.get("title") or str(e["id"]))}</span>'
                 + "".join(f'<span class="grp">{g}</span>' for g in groups) + "</span></div>")
            if kids:
                s += "<ul>" + self.inside(k, lambda: "".join(li(c, depth + 1) for c in kids)) + "</ul>"
            return s + "</li>"

        legend = []
        for c in filt:
            cat = self.cats[c]
            vals = "".join(f'{self.badge(c, k, True)}<span class="lv">{E(v.get("desc", ""))}</span>' for k, v in cat["values"].items())
            legend.append(f'<dt>{E(cat.get("label", c))}</dt><dd>{vals}</dd>')
        hint = b.get("hint", self.t["t_hint"])
        reset = b.get("reset", self.t["t_reset"])
        label = b.get("count_label", self.t["t_count"])
        # `drives`: diagrams whose nodes (by `ref`) follow this filter; a map hides them, others fade them
        tree_ids = {str(e["id"]) for e in self.d["entities"] if e.get("tree", True)}
        for gid in b.get("drives", []):
            g = self.dg.get(gid)
            if not g:
                fail(f"tree: drives: unknown diagram {gid}")
            if g["type"] == "vega":
                rows = self.vega_check(g)
                if not g.get("entity"):
                    fail(f"tree: drives {gid}: vega block needs `entity` (the row field that holds entity ids)")
                if not {str(r[g["entity"]]) for r in rows} & tree_ids:
                    fail(f"tree: drives {gid}: no row of it has an `{g['entity']}` that is an entity of this tree")
            elif not any(str(n.get("ref")) in tree_ids for n in g.get("nodes") or g.get("types") or g.get("states") or []):
                fail(f"tree: drives {gid}: no node of it has a `ref` to an entity of this tree")
        drives = [self.danchor(g) for g in b.get("drives", [])]
        return (f'<div x-data="treeFilter({E(json.dumps(cats))},{E(json.dumps(label))},{E(json.dumps(drives))})">'
                f'<dl class="legend">{"".join(legend)}</dl>'
                f'<div class="ctl"><span>{E(hint)}</span><span class="cnt" x-text="count"></span>'
                f'<button type="button" @click="reset()" :disabled="!Object.values(off).some(Boolean)">{E(reset)}</button></div>'
                f'<div class="tree"><ul class="tr">{"".join(li(r, 0) for r in roots)}</ul></div></div>')

    def groups(self, e, kind_cat, toggles):
        """Meta, badges other than the kind, refs and back-links of one entity, one group each."""
        bvals = e.get("badges", {})
        out = [f'<span class="mt">{self.inline(m)}</span>' for m in e.get("meta", [])]
        for c in self.cats:
            if c != kind_cat and c in bvals:
                out.append("".join(self.badge(c, v, c in toggles) for v in dict.fromkeys(bvals[c])))
        for arrow, ids in (("→", e.get("refs", [])), ("←", self.back.get(e["id"], []))):
            if ids:
                more = f'<span class="mt">+{len(ids) - LINKS_SHOWN}</span>' if len(ids) > LINKS_SHOWN else ""
                out.append(f'<span class="xr">{arrow} ' + " ".join(self.link(r) for r in ids[:LINKS_SHOWN]) + more + "</span>")  # spaces: wrap points on a phone
        return out

    def card(self, eid, kind_cat):
        """One entity as a summary row: its anchor, kind badge, title, meta, badges and links."""
        if eid not in self.ents:
            fail(f"tabs: unknown entity {eid}")
        e = self.ents[eid]
        kind = "".join(self.badge(kind_cat, v, False) for v in e.get("badges", {}).get(kind_cat, []))
        kind = f'<span class="kb">{kind}</span>' if kind else ""
        _, cls, mk = self.state(e, False)
        return (f'<div class="row card{cls}" id="{E(self.anchor(eid))}">{kind}<span class="bd">{mk}'
                f'<span class="tt">{E(e.get("title") or str(eid))}</span>'
                + "".join(f'<span class="grp">{g}</span>' for g in self.groups(e, kind_cat, ())) + "</span></div>")

    def b_tabs(self, b):
        """Sibling items of one kind side by side: a scrollable tab bar, one panel each.
        A panel opens itself when a link targets anything inside it."""
        self.ntabs += 1
        tid = f't-{b.get("id", self.ntabs)}'
        kind_cat = b.get("kind", next(iter(self.cats), None))
        bar, panels = [], []
        scope = self.scope(b["tabs"])
        first = next((i for i, t in enumerate(b["tabs"]) if self.changed(t)), 0) if scope else 0  # open the first change
        for i, t in enumerate(b["tabs"]):
            eid = t.get("entity")
            ent = self.ents.get(eid, {}) if eid else {}
            label = t.get("label") or (eid and (ent.get("label") or ent.get("title", "").replace("`", "") or eid))
            if not label:
                fail(f"tabs {tid}: tab {i + 1} needs a label or an entity")
            pid, on = f"{tid}-{i + 1}", i == first
            k, cls, mk = self.state(t, scope)
            dot = ""
            if self.chg and not self.under and self.changed(t):  # a dot on every tab with a change inside
                dot = f'<span class="cdot c-{k or "changed"}"></span>'
            num = f'<span class="tn">{i + 1}</span>' if b.get("numbered", True) else ""
            bcls = ' class="dim"' if cls == " dim" else ""
            bar.append(f'<button type="button" role="tab" id="{pid}-b" aria-controls="{pid}" aria-selected="{str(on).lower()}"'
                       f' tabindex="{0 if on else -1}"{bcls}>{dot}{num}{E(str(label))}</button>')

            def panel():
                head = self.card(eid, kind_cat) if eid else ""
                if t.get("summary"):
                    head += f'<p class="sum">{self.inline(t["summary"])}</p>'
                self.tab_entity = eid
                inner = self.scope(t.get("blocks", []))
                body = "".join(self.block(x, f"tabs {tid}", inner) for x in t.get("blocks", []))
                self.tab_entity = None
                return head + body
            panels.append(f'<div class="tp{" on" if on else ""}{cls}" role="tabpanel" id="{pid}" aria-labelledby="{pid}-b">'
                          f'{mk}{self.inside(k, panel)}</div>')
        return (f'<div class="tabs" id="{E(tid)}"><div class="tl" role="tablist" aria-label="{E(b.get("label", ""))}">'
                f'{"".join(bar)}</div>{"".join(panels)}</div>')

    def b_html(self, b):
        return b["html"]

    def b_mermaid(self, b):
        """Mermaid source (`report-diagram`) rendered in the browser from the CDN module in HEAD; the escaped
        source stays readable in the <pre> when the render or the network fails. `click` hrefs are checked in render()."""
        gid = b["id"]
        if not isinstance(b.get("code"), str) or not b["code"].strip():
            fail(f"mermaid {gid}: `code` is required")
        after = self.evidence([(E(b.get("label", gid)), b["at"])]) if b.get("at") else ""
        return self.figure(b, f'<pre class="mermaid">{E(b["code"])}</pre>', used={}, after=after)

    def b_video(self, b):
        """Explainer video (`report-video`): `src`/`poster` resolve next to the output HTML, else next to report.json
        (the emitted path is then rewritten relative to the output HTML)."""
        gid = b["id"]
        out_dir = Path(self.out_dir) if self.out_dir is not None else Path(".")
        bases = [out_dir] + ([Path(self.src).parent] if self.src is not None else [])
        for key in ("src", "poster"):
            if key == "src" and not b.get(key):
                fail(f"video {gid}: `src` is required")
            if not b.get(key):
                continue
            found = next((x / b[key] for x in bases if (x / b[key]).is_file()), None)
            if found is None:
                fail(f"video {gid}: file not found {b[key]}")
            if found != out_dir / b[key]:
                b[key] = Path(os.path.relpath(found.resolve(), out_dir.resolve())).as_posix()
        poster = f' poster="{E(b["poster"])}"' if b.get("poster") else ""
        el = (f'<video controls preload="metadata"{poster} src="{E(b["src"])}" '
              f'style="width:100%;max-height:70vh"></video>')
        after = f'<p class="mt">{self.inline(b["caption"])}</p>' if b.get("caption") else ""
        if b.get("at"):
            after += self.evidence([(E(b.get("label", gid)), b["at"])])
        return self.figure(b, el, used={}, tools="", after=after)

    def vega_check(self, b):
        """Validate and normalise one `vega` block once (the spec stays inline, the dataset is named `rows` for the page script);
        returns the inline rows. Called from b_vega and from a tree that `drives` the chart."""
        gid, spec = b["id"], b.get("spec")
        if not isinstance(spec, dict):
            fail(f"vega {gid}: `spec` (a Vega-Lite spec object) is required")
        if not b.get("_vega_ok"):
            def no_url(x):
                if isinstance(x, dict):
                    if isinstance(x.get("data"), dict) and "url" in x["data"]:
                        fail(f"vega {gid}: data must be inline values (`data.url` would break the one-file page)")
                    for v in x.values():
                        no_url(v)
                elif isinstance(x, list):
                    for v in x:
                        no_url(v)
            no_url(spec)
            data = spec.get("data")
            if not isinstance(data, dict) or not isinstance(data.get("values"), list):
                fail(f"vega {gid}: data must be inline values (`spec.data.values` as an array of row objects)")
            for n, r in enumerate(data["values"], 1):
                if not isinstance(r, dict):
                    fail(f"vega {gid}: data row {n} is not an object")
                if b.get("entity") and b["entity"] not in r:
                    fail(f"vega {gid}: entity {b['entity']} missing in row {n}")
            spec.setdefault("$schema", VEGA_SCHEMA)
            spec.setdefault("width", "container")
            data["name"] = "rows"
            b["_vega_ok"] = True
        return spec["data"]["values"]

    def b_vega(self, b):
        """Vega-Lite chart (`report-charts`): the spec travels as JSON next to an empty <div class="vg">; the page script
        embeds it from the CDN scripts in HEAD. `entity` names the row field that holds entity ids (tree `drives`)."""
        gid = b["id"]
        self.vega_check(b)
        js = json.dumps(b["spec"], ensure_ascii=False).replace("<", "\\u003c")
        ent = f' data-e="{E(str(b["entity"]))}"' if b.get("entity") else ""
        after = self.evidence([(E(b.get("label", gid)), b["at"])]) if b.get("at") else ""
        inner = (f'<div class="vg" id="vg-{E(gid)}" data-nocdn="{E(self.t["chart_cdn"])}"></div>'
                 f'<script type="application/json" class="vgs">{js}</script>')
        return self.figure(b, inner, used={}, tools="", after=after).replace('<figure class="fg"', f'<figure class="fg"{ent}', 1)

    def block(self, b, where, scope=False):
        """One block; in a change document a marked block gets its mark and rule, an unmarked one next to a marked sibling dims."""
        fn = getattr(self, "b_" + b["type"], None)
        if not fn:
            fail(f"{where}: unknown block type {b['type']}")
        k, cls, mk = self.state(b, scope)
        out = self.inside(k, fn, b)
        return f'<div class="cx{cls}">{mk}{out}</div>' if cls else out

    # -- computed stats, evidence and lint ---------------------------------
    def require_at(self):
        """Profiles explanation and structure: every flow/map edge carries `at` (other profiles only warn, see check_evidence)."""
        if self.d.get("profile") not in AT_REQUIRED:
            return
        miss = [f"{b['type']} {b['id']}: edge {e['from']}->{e['to']} without at"
                for b in self.dg.values() if b["type"] in ("flow", "map")
                for e in map(edge_of, b.get("edges", [])) if not e.get("at")]
        if miss:
            fail("\nreport.json: ".join(miss[:12]) + (f"\nreport.json: … +{len(miss) - 12} more" if len(miss) > 12 else ""))

    def dump_rows(self, label, name):
        """Rows of collection `name` from the dump: `<name>.json` (array or Directus {"data": [...]}) or `.jsonl` in
        the folder `data_dir` (top level, relative to report.json) or, by convention, `<report stem>.data/` next to report.json."""
        if self.src is None:
            fail(f'stat "{label}": count needs the path of report.json')
        base = self.src.parent
        folder = base / self.d["data_dir"] if self.d.get("data_dir") else base / (self.src.stem + ".data")
        for ext in (".json", ".jsonl"):
            f = folder / (name + ext)
            if f.is_file():
                break
        else:
            fail(f'stat "{label}": unknown collection {name} (no {folder / (name + ".json")})')
        text = f.read_text()
        rows = [json.loads(ln) for ln in text.splitlines() if ln.strip()] if ext == ".jsonl" else json.loads(text)
        if isinstance(rows, dict) and isinstance(rows.get("data"), list):
            rows = rows["data"]
        if not isinstance(rows, list):
            fail(f'stat "{label}": {f} is not an array of rows')
        return rows

    def stat(self, label, v):
        """Header stat value as text: `{"count": <collection>, "where"?: {field: value}}` counts dump rows, `{"rows": <table id>}`
        counts the body rows of a `table`/`data` block, `{"value": n, "source": <file>}` is a literal that names its source
        (lint line). A bare number fails; other text (a label such as "v2") stays as typed."""
        if isinstance(v, dict):
            if "count" in v:
                def field(r, path):
                    for k in path.split("."):
                        r = r.get(k) if isinstance(r, dict) else None
                    return r
                where = v.get("where") or {}
                rows = [r for r in self.dump_rows(label, v["count"])
                        if all(field(r, k) == w or (isinstance(field(r, k), list) and w in field(r, k)) for k, w in where.items())]
                return str(len(rows))
            if "rows" in v:
                blk = next((b for sec in self.d.get("sections", []) for b in walk(sec.get("blocks", []))
                            if b.get("id") == v["rows"] and b.get("type") in ("table", "data")), None)
                if blk is None:
                    fail(f'stat "{label}": unknown table {v["rows"]}')
                return str(len(blk.get("rows", [])))
            if "value" in v:
                if not v.get("source"):
                    fail(f'stat "{label}": literal number needs source, count or rows')
                self.lints.append(f'stat "{label}": literal, source {v["source"]}')
                return str(v["value"])
            fail(f'stat "{label}": give count, rows, or value with source')
        if (isinstance(v, (int, float)) and not isinstance(v, bool)) or re.fullmatch(r"[\d.,\s]+", str(v)):
            fail(f'stat "{label}": bare number {v}; write {{count: "<collection>"}} against <stem>.data/ or {{value, source}}')
        return str(v)

    def incoming(self):
        """Entity ids that something links to: `refs`, [[id]] in any text, {ref}/{refs} cells, node `ref`, tab `entity`, bars labels,
        `key` column values of `data` rows, mermaid `click … "#e-<id>"` targets.
        A link from an entity to itself does not count; `parent` is structure, not a link."""
        known = {str(k): k for k in self.ents}
        inc = set()

        def add(x, owner):
            k = known.get(str(x))
            if k is not None and k != owner:
                inc.add(k)

        def scan(x, owner):
            if isinstance(x, str):
                for m in re.finditer(r"\[\[([^\]|]+)", x):
                    add(m.group(1), owner)
            elif isinstance(x, list):
                for v in x:
                    scan(v, owner)
            elif isinstance(x, dict):
                if x.get("type") == "data" and isinstance(x.get("key"), str) and isinstance(x.get("rows"), list):
                    for r in x["rows"]:
                        if isinstance(r, dict) and isinstance(r.get(x["key"]), (str, int)) and not isinstance(r[x["key"]], bool):
                            add(r[x["key"]], owner)
                elif x.get("type") == "mermaid" and isinstance(x.get("code"), str):
                    for h in MERMAID_HREF.findall(x["code"]):
                        if h.startswith("e-"):
                            add(h[2:], owner)
                for k, v in x.items():
                    if k == "ref" and not isinstance(v, (dict, list)):
                        add(v, owner)
                    elif k == "refs" and isinstance(v, list):
                        for r in v:
                            add(r, owner)
                    elif k == "entity" and "blocks" in x:
                        add(v, owner)
                    elif k == "items" and x.get("type") == "bars" and x.get("link", True):
                        for it in v:
                            add(it[0], owner)
                    scan(v, owner)

        for e in self.d.get("entities", []):
            scan(e, e["id"])
        scan(self.d.get("sections", []), None)
        return inc

    @staticmethod
    def meta_key(m):
        """Key of a `meta` line: the part before a colon, else the text without numbers and backticks."""
        s = str(m)
        head, colon, _ = s.partition(":")
        if colon and "`" not in head and len(head.split()) <= 3:
            return head.strip().lower()
        return re.sub(r"\s+", " ", re.sub(r"[\d.,]+", " ", s.replace("`", ""))).strip().lower()

    def lint(self):
        """Lint lines for the weaknesses of the 2026-10-13 review; stat lines are already in self.lints."""
        out, d = list(self.lints), self.d
        secs = d.get("sections", [])
        inc = self.incoming()
        for e in d.get("entities", []):
            if e.get("tree", True) is not False and e["id"] not in inc:
                out.append(f"orphan {e['id']}: no incoming link")
        for sec in secs:
            for b in walk(sec.get("blocks", [])):
                if b.get("type") in ("p", "bullets", "steps"):
                    text = b["text"] if b["type"] == "p" else " ".join(x["text"] if isinstance(x, dict) else x for x in b["items"])
                    if "[[" not in text:
                        n = len(text.split())
                        if n > LINT_PROSE_WORDS:
                            out.append(f'prose: section "{sec["title"]}" has {n} words and 0 links')
        for c, cat in self.cats.items():
            have = [e for e in d.get("entities", []) if e.get("badges", {}).get(c)]
            if len(have) < 10:
                continue
            for val in cat["values"]:
                n = sum(1 for e in have if val in e["badges"][c])
                pct = n * 100 / len(have)
                if pct > 85 or pct < 5:
                    out.append(f"badge {c}={val}: {n} of {len(have)} entities ({pct:.0f} %)")
        depth = {}
        for e in d.get("entities", []):
            n, p = 0, e.get("parent")
            while p is not None and n <= len(self.ents):
                n, p = n + 1, self.ents[p].get("parent")
            depth[e["id"]] = n
        for c, cat in self.cats.items():
            have = [e for e in d.get("entities", []) if e.get("badges", {}).get(c)]
            if len(have) < 3 or len(cat["values"]) < 2:
                continue
            levels = defaultdict(set)  # value -> depths it occurs at
            for e in have:
                for val in e["badges"][c]:
                    levels[val].add(depth[e["id"]])
            if len(levels) >= 2 and all(len(ls) == 1 for ls in levels.values()) \
                    and len({next(iter(ls)) for ls in levels.values()}) == len(levels):
                out.append(f"badge {c}: mirrors tree level, not a filter")
        tree = next((b for b in (b for sec in secs for b in walk(sec.get("blocks", []))) if b.get("type") == "tree"), {})
        filt = tree.get("filter", list(self.cats))
        kind_cat = tree.get("kind", filt[0] if filt else next(iter(self.cats), None))
        kinds = defaultdict(list)
        for e in d.get("entities", []):
            if e.get("badges", {}).get(kind_cat):
                kinds[e["badges"][kind_cat][0]].append(e)
        for kind, es in kinds.items():
            if len(es) < LINT_KIND_MIN:
                continue
            keys = [{self.meta_key(m) for m in e.get("meta", [])} - {""} for e in es]
            for key in sorted(set().union(*keys)):
                if sum(key in ks for ks in keys) >= 0.8 * len(es):
                    out += [f'kind {kind}: {e["id"]} lacks meta "{key}"' for e, ks in zip(es, keys) if key not in ks]
        pos, trees, i = {}, [], 0
        for sec in secs:
            for b in walk(sec.get("blocks", [])):
                i += 1
                if b.get("type") in DIAGRAMS | ID_FIGURES:
                    pos[b["id"]] = i
                elif b.get("type") == "tree" and b.get("drives"):
                    trees.append((i, sec["title"], b["drives"]))
        for i, title, drives in trees:
            if any(pos.get(g, i) < i for g in drives):
                out.append(f'section "{title}": tree after the diagram it drives')
        return out

    # -- page ------------------------------------------------------------
    def render(self):
        d = self.d
        used = {b.get("type") for sec in d.get("sections", []) for b in walk(sec.get("blocks", []))}
        t = self.t
        find = (f'<div class="find"><input id="find" type="search" placeholder="{E(t["find"])}" aria-label="{E(t["find"])}">'
                '<span id="findn"></span></div>') if used & FIND_TYPES else ""
        meta = d.get("meta", [])
        prov = (f'<details class="provenance"><summary>{E(t["sources"])}</summary><p>'
                + "<br>".join(self.inline(m) for m in meta) + "</p></details>") if meta else ""
        # closed <details> content is not printed: a print-only copy keeps the sources on paper
        prov_print = ('<p class="prov-print">' + "<br>".join(self.inline(m) for m in meta) + "</p>") if meta else ""
        head = [f'<header><h1>{E(d["title"])}</h1>{prov}{prov_print}{find}</header>']
        stats = ""
        if d.get("stats"):
            stats = '<dl class="stats">' + "".join(f"<div><dt>{E(k)}</dt><dd>{E(self.stat(k, v))}</dd></div>" for k, v in d["stats"]) + "</dl>"
        secs = d.get("sections", [])
        parts = []
        top = self.scope(secs)
        for i, sec in enumerate(secs, 1):
            k, cls, mk = self.state(sec, top)
            inner = self.scope(sec.get("blocks", []))
            body = self.inside(k, lambda: [self.block(b, f"section {sec['title']}", inner) for b in sec.get("blocks", [])])
            num = f"{i} " if d.get("numbered", True) else ""
            sid = f' id="{E(sec["id"])}"' if sec.get("id") else ""
            ccls = f' class="{cls.strip()}"' if cls else ""
            parts.append(f'<section{sid}{ccls}><h2>{num}{mk}{E(sec["title"])}<span>{E(sec.get("sub", ""))}</span></h2>'
                         f'<div class="body">{"".join(body)}</div></section>')
        summary = ""
        if self.chg:
            since = f' {E(str(d["since"]))}' if d.get("since") else ""
            counts = " ".join(f'{self.mark(k)}<span class="cn">{self.nchg[k]}</span>' for k in CHANGE if self.nchg[k])
            summary = (f'<div class="chgbar"><span>{E(self.t["since"])}{since}:</span>{counts}'
                       f'<span class="mt">{E(self.t["dimmed"])}</span>'
                       f'<button type="button" aria-pressed="false" onclick="nodim(this)">{E(self.t["full"])}</button></div>')
        # reading order: title and find box, the first section (the answer), statistics and change summary, the rest
        parts = head + parts[:1] + [x for x in (stats, summary) if x] + parts[1:]
        body = "\n".join(parts)
        found = Counter(html.unescape(i) for i in re.findall(r'\sid="([^"]+)"', body))
        twice = sorted(i for i, k in found.items() if k > 1)
        if twice:
            fail("anchor rendered twice: " + ", ".join(twice[:12]) + " (an entity belongs in one tree or one tab, not both)")
        ids = set(found)
        mm = {h for sec in d.get("sections", []) for b in walk(sec.get("blocks", [])) if b.get("type") == "mermaid"
              for h in MERMAID_HREF.findall(b.get("code", ""))}
        dead = sorted(({html.unescape(h) for h in re.findall(r'href="#([^"]+)"', body)} | mm) - ids)
        if dead:
            fail("links without a target: " + ", ".join(dead[:12]) + " (an entity needs a tree row, a table `anchor` or a tab `entity`)")
        page = TEMPLATE.read_text()
        head = "\n".join(HEAD[k] for k in sorted(used & HEAD.keys()))
        vals = {"LANG": E(d.get("lang", "de")), "TITLE": E(d["title"]), "HEAD": head, "BODY": body}
        return re.sub(r"\{\{(LANG|TITLE|HEAD|BODY)\}\}", lambda m: vals[m.group(1)], page)  # one pass: report text cannot inject a placeholder


CHOICE_KEYS = ("tree", "data", "charts", "crossfilter", "badge-chart", "find", "flow", "map", "mermaid", "video")
CHOICE_BLOCKS = {"tree": "tree", "table": "tree", "data": "data", "vega": "charts", "bars": "charts",
                 "flow": "flow", "lineage": "flow", "states": "flow", "map": "map", "mermaid": "mermaid", "video": "video"}


def check_choice(data, path):
    """Compare the features and questions the report uses with the ones the choice file lists; fail on a used, unchosen one."""
    try:
        choice = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        fail(f"--check-choice {path}: {e}")
    feats = choice.get("features") if isinstance(choice, dict) else None
    if not isinstance(feats, list):
        fail(f'--check-choice {path}: expected {{"profile": ..., "features": [...]}}')
    unknown = [f for f in feats if f not in CHOICE_KEYS]
    if unknown:
        fail(f"--check-choice {path}: unknown feature keys {', '.join(map(str, unknown))}")
    used = set()
    for sec in data.get("sections", []):
        for b in walk(sec.get("blocks", [])):
            if b.get("type") in CHOICE_BLOCKS:
                used.add(CHOICE_BLOCKS[b["type"]])
    if data.get("badges"):
        used.add("tree")
    for k in CHOICE_KEYS:
        print(f"choice: {k} chosen={'yes' if k in feats else 'no'} used={'yes' if k in used else 'no'}")
    bad = [k for k in CHOICE_KEYS if k in used and k not in feats]
    if bad:
        fail(f"--check-choice: used but not chosen: {', '.join(bad)}")
    qs = choice.get("questions")
    if qs is None:
        return
    if not isinstance(qs, list) or not all(isinstance(q, dict) and q.get("id") and q.get("text") for q in qs):
        fail(f'--check-choice {path}: "questions" must be [{{"id", "chapter", "text", "feature"}}]')
    ids = [q["id"] for q in qs]
    if len(set(ids)) != len(ids):
        fail(f"--check-choice {path}: duplicate question ids")
    for q in qs:
        f = q.get("feature", "none")
        if f != "none" and f not in feats:
            fail(f'--check-choice: question {q["id"]} needs feature {f}, which is not in "features"')
    answered = defaultdict(list)
    for n, sec in enumerate(data.get("sections", [])):
        q = sec.get("question")
        if q is None and n == 0:
            continue
        if q not in ids:
            fail(f'--check-choice: section "{sec.get("title")}" answers no chosen question; '
                 f'set "question" to one of {", ".join(ids)} or drop the section')
        answered[q].append(sec.get("title"))
    for q in qs:
        secs = answered.get(q["id"], [])
        print(f'choice: question {q["id"]} sections={len(secs)} "{q["text"]}"')
    missing = [q["id"] for q in qs if not answered.get(q["id"])]
    if missing:
        fail(f"--check-choice: chosen questions without a section: {', '.join(missing)}")
    twice = [q for q, s in answered.items() if len(s) > 1]
    if twice:
        fail(f"--check-choice: questions answered by more than one section (merge them): {', '.join(twice)}")


def main():
    argv = sys.argv[1:]
    choice = None
    if "--check-choice" in argv:
        i = argv.index("--check-choice")
        if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
            sys.exit(__doc__)
        choice = argv[i + 1]
        del argv[i:i + 2]
    args = [a for a in argv if a != "--strict"]
    strict = len(args) != len(argv)
    if len(args) != 2:
        sys.exit(__doc__)
    data = json.loads(Path(args[0]).read_text())
    if choice:
        check_choice(data, choice)
    out = Path(args[1])
    rep = Report(data, out_dir=out.parent, src=Path(args[0]))
    page = rep.render()
    lints = rep.lint()
    for line in lints:
        print(f"lint: {line}", file=sys.stderr)
    print(f"lint: {len(lints)} findings", file=sys.stderr)
    if strict and lints:
        sys.exit(f"report.json: --strict: {len(lints)} lint findings")
    out.write_text(page)
    print(args[1])


if __name__ == "__main__":
    main()
