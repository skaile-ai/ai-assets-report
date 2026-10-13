#!/usr/bin/env python3
"""Detect entities and their connections in a data dump; write a type schema and a draft report.

    python3 detect.py <dump> <outdir> [--title T] [--lang de] [--max N] [--skip c1,c2]

<dump>: a JSON file `{collection: [row, ...]}`, or a directory of `<collection>.json`
(array, or `{"data": [...]}` as Directus returns) and `<collection>.jsonl` files.

Writes to <outdir>:
  schema.json  collections, primary key, typed fields, relations, enums (machine-readable)
  schema.ts    the same as TypeScript types (for reading and for app code)
  report.json  a draft for build.py: one entity per row, refs from foreign keys,
               tree from hierarchies, badges from enum fields; edit it, then render.

Detection is by value, not by name: a field is a foreign key when (almost) every value
is a primary key of one collection. Names only break ties (`parent*` = parent side).
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?$")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
TITLE_FIELDS = ("title", "name", "label", "heading", "key", "external_id", "slug", "code")
LABEL_FIELDS = ("external_id", "key", "slug", "code", "chapter_id", "name")
ORDER_FIELDS = ("position", "sort", "order", "root_position", "index", "rank")
PALETTE = ["blue", "green", "orange", "pink", "teal", "purple", "brown", "navy", "yellow", "red", "gray"]
FK_COVERAGE = 0.9
ENUM_MAX = 12


def load(src):
    p = Path(src)
    if p.is_file():
        data = json.loads(p.read_text())
        return {k: v for k, v in data.items() if isinstance(v, list)}
    out = {}
    for f in sorted(p.iterdir()):
        if f.suffix == ".json":
            d = json.loads(f.read_text())
            rows = d.get("data", d) if isinstance(d, dict) else d
        elif f.suffix == ".jsonl":
            rows = [json.loads(line) for line in f.read_text().splitlines() if line.strip()]
        else:
            continue
        if isinstance(rows, list):
            out[f.stem] = [r for r in rows if isinstance(r, dict)]
    return out


def scalar_type(v):
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "number"
    if isinstance(v, str):
        if UUID.match(v):
            return "uuid"
        if ISO.match(v):
            return "datetime" if len(v) > 10 else "date"
        return "string"
    if isinstance(v, dict):
        return "object"
    return "unknown"


def field_type(values):
    """Merge the types seen in one field into one type string."""
    kinds, items, nullable = set(), set(), False
    for v in values:
        if v is None:
            nullable = True
        elif isinstance(v, list):
            kinds.add("array")
            items.update(scalar_type(x) for x in v if x is not None)
        else:
            kinds.add(scalar_type(v))
    if {"integer", "number"} <= kinds:
        kinds -= {"integer"}
    if len(kinds - {"array"}) > 1 and kinds - {"array"} <= {"string", "uuid", "date", "datetime"}:
        kinds = (kinds & {"array"}) | {"string"}
    if "array" in kinds:
        it = items.pop() if len(items) == 1 else ("unknown" if not items else "|".join(sorted(items)))
        base = f"{it}[]" if len(kinds) == 1 else "unknown"
    else:
        base = kinds.pop() if len(kinds) == 1 else ("null" if not kinds else "|".join(sorted(kinds)))
    return base, nullable


def refs_of(v):
    """Scalar key values held by a field value (scalar, array, or {id: ...} object)."""
    if v is None:
        return []
    if isinstance(v, list):
        return [x for y in v for x in refs_of(y)]
    if isinstance(v, dict):
        return [v["id"]] if "id" in v and not isinstance(v["id"], (dict, list)) else []
    if isinstance(v, (bool, float)):
        return []
    return [v]


def get(row, path):
    """Value at a field path: `f`, `f.sub` (object) or `f[].sub` (array of objects, flattened)."""
    head, _, rest = path.partition(".")
    arr = head.endswith("[]")
    v = row.get(head[:-2] if arr else head)
    if not rest:
        return v
    if arr:
        return [x.get(rest) for x in v if isinstance(x, dict)] if isinstance(v, list) else None
    return v.get(rest) if isinstance(v, dict) else None


def paths(rows):
    """Top-level fields plus one level into objects and arrays of objects. Objects keyed by
    data (more than 12 distinct keys, or keys that are ids) stay maps and are not expanded."""
    out = []
    for f in dict.fromkeys(k for r in rows for k in r):
        out.append(f)
        subs = {}
        for r in rows:
            v = r.get(f)
            if isinstance(v, dict):
                subs.update(dict.fromkeys(f"{f}.{k}" for k in v))
            elif isinstance(v, list):
                subs.update(dict.fromkeys(f"{f}[].{k}" for x in v if isinstance(x, dict) for k in x))
        names = [p.rsplit(".", 1)[1] for p in subs]
        if len(names) <= 12 and not any(UUID.search(n) or re.search(r"\d{4,}", n) for n in names):
            out += list(subs)
    return out


KEYLIKE = re.compile(r"^[\w.:-]{1,64}$")
HASH = re.compile(r"^[0-9a-f]{32,}$", re.I)


def unique_keys(rows, pk):
    """Primary key first, then business keys: unique, present, identifier-shaped values.
    Collections with fewer than 3 rows get no business keys: any value is unique there."""
    if not rows:
        return []
    fields = list(dict.fromkeys(k for r in rows for k in r))
    keys = {}
    for f in ([pk] if pk else []) + [f for f in fields if f != pk]:
        vals = [r.get(f) for r in rows]
        if not all(isinstance(v, (str, int)) and not isinstance(v, bool) for v in vals):
            continue
        dups = sorted((v for v, n in Counter(vals).items() if n > 1), key=str)
        # A business key may carry a few duplicates (a data error worth reporting); a primary key may not.
        if dups and (f == pk or len(set(vals)) < 0.97 * len(vals)):
            continue
        if f != pk and (len(rows) < 3 or not all(isinstance(v, str) and KEYLIKE.match(v) and not HASH.match(v)
                                                 and not ISO.match(v) for v in vals)):
            continue
        keys[f] = dups
    return keys


def primary_key(rows):
    keys = unique_keys(rows, "id" if rows and all("id" in r for r in rows) else None)
    return next(iter(keys), None)


def find_ref(c, f, t, rows, vals, keys, pk):
    """Best (collection, key field) whose key values cover the values of field f."""
    pairs = [(r, x) for r, v in zip(rows, vals) for x in refs_of(v)]
    if not pairs:
        return None
    best = None
    ints = all(isinstance(x, int) for _, x in pairs)
    for oc, cand in keys.items():
        for kf, ks in cand.items():
            # Identity: a self-reference to the row's own key is a copy, not a link.
            usable = [x for own, x in pairs if not (oc == c and own.get(kf) == x)]
            if not usable or (oc == c and len(usable) < len(pairs) / 2):
                continue
            cov = sum(1 for x in usable if x in ks) / len(usable)
            if cov < FK_COVERAGE:
                continue
            leaf = f.rsplit(".", 1)[-1]
            if ints and not (leaf.endswith(("_id", "_ids")) or leaf in (oc, oc.rstrip("s"))):
                continue
            score = (cov, kf == "id" or kf == keys_pk(cand), len(ks))
            if best is None or score > best[0]:
                best = (score, oc, kf)
    return best and best[1:]


def keys_pk(cand):
    return next(iter(cand), None)


def detect(data, skip=()):
    cols = {c: rows for c, rows in data.items() if c not in skip}
    pks = {c: primary_key(rows) for c, rows in cols.items()}
    ukeys = {c: unique_keys(rows, pks[c]) for c, rows in cols.items() if pks[c]}
    keys = {c: {k: {r[k] for r in cols[c]} for k in uk} for c, uk in ukeys.items()}
    schema = {"collections": {}, "relations": []}
    for c, rows in cols.items():
        pk = pks[c]
        fields = {}
        for f in paths(rows):
            vals = [get(r, f) for r in rows]
            t, nullable = field_type(vals)
            fd = {"type": t}
            if nullable or (("." not in f) and any(f not in r for r in rows)):
                fd["nullable"] = True
            leaf = f.rsplit(".", 1)[-1]
            if f == pk:
                fd["primary"] = True
            elif t != "object" and not t.startswith("object"):
                ref = find_ref(c, f, t, rows, vals, keys, pk) if pk else None
                if ref:
                    oc, kf = ref
                    fd["ref"] = oc
                    if kf != pks[oc]:
                        fd["ref_key"] = kf
                    schema["relations"].append({"from": c, "field": f, "to": oc, "key": kf,
                                                "many": t.endswith("[]") or "[]" in f})
                elif f in keys.get(c, {}):
                    fd["unique"] = True
                elif leaf not in TITLE_FIELDS and len(rows) >= 4:
                    flat = [x for v in vals for x in (v if isinstance(v, list) else [v])]
                    if t == "boolean" or (t in ("string", "string[]") and enum_like(flat)):
                        fd["enum"] = sorted({x for x in flat if x is not None}, key=str)
            if f in ukeys.get(c, {}) and ukeys[c][f]:
                fd["duplicates"] = ukeys[c][f]
            fields[f] = fd
        schema["collections"][c] = {"rows": len(rows), "primary": pk, "fields": fields}
    classify(schema)
    return schema


def enum_like(vals):
    present = [v for v in vals if v is not None]
    if not present:
        return False
    distinct = set(present)
    if any(not isinstance(v, str) or len(v) > 40 for v in distinct):
        return False
    return len(distinct) <= ENUM_MAX and len(distinct) < len(present) / 2


def classify(schema):
    """Mark hierarchies: a self-reference, or a join table whose two keys hit one collection."""
    cols = schema["collections"]
    for c, info in cols.items():
        top = {f: d for f, d in info["fields"].items() if "." not in f}
        refs = {f: d["ref"] for f, d in top.items() if "ref" in d and "ref_key" not in d}
        self_refs = [f for f, t in refs.items() if t == c and not top[f]["type"].endswith("[]")]
        if self_refs:
            info["hierarchy"] = {"parent": sorted(self_refs, key=lambda f: "parent" not in f)[0]}
        same = defaultdict(list)
        for f, t in refs.items():
            if t != c:
                same[t].append(f)
        other = [f for f, d in top.items() if "ref" not in d and not d.get("primary")]
        for t, fs in same.items():
            if len(fs) == 2 and len(other) <= 3:
                p, ch = sorted(fs, key=lambda f: ("parent" not in f, "from" not in f, "source" not in f))
                info["join"] = {"of": t, "parent": p, "child": ch,
                                "order": next((f for f in ORDER_FIELDS if f in info["fields"]), None)}
        if len(refs) >= 2 and len(other) <= 2 and "join" not in info:
            info["link_table"] = True


# -- TypeScript --------------------------------------------------------------

TS = {"string": "string", "uuid": "string", "date": "string", "datetime": "string", "integer": "number",
      "number": "number", "boolean": "boolean", "object": "Record<string, unknown>", "unknown": "unknown", "null": "null"}


def pascal(name):
    return "".join(p[:1].upper() + p[1:] for p in re.split(r"[^0-9a-zA-Z]+", name) if p)


def ts_type(c, f, d, cols):
    t = d["type"]
    arr = t.endswith("[]")
    base = t[:-2] if arr else t
    if "enum" in d and base != "boolean":
        out = " | ".join(json.dumps(v) for v in d["enum"])
        out = f"({out})" if arr and len(d["enum"]) > 1 else out
    elif "ref" in d:
        key = d.get("ref_key") or cols[d["ref"]]["primary"]
        out = f"{pascal(d['ref'])}[{json.dumps(key)}]"
    else:
        out = " | ".join(TS.get(x, "unknown") for x in base.split("|"))
        out = f"({out})" if arr and "|" in base else out
    out += "[]" if arr else ""
    return out + (" | null" if d.get("nullable") and out != "null" else "")


def to_ts(schema):
    cols = schema["collections"]
    lines = ["// Generated by report-table/detect.py from a data dump. Types are inferred from values:",
             "// nullable = a null or a missing value was seen; unions = every value seen.", ""]
    for c, info in cols.items():
        notes = []
        if info.get("hierarchy"):
            notes.append(f"tree via {info['hierarchy']['parent']}")
        if info.get("join"):
            j = info["join"]
            notes.append(f"joins {j['of']}: {j['parent']} -> {j['child']}")
        notes.append(f"{info['rows']} rows")
        lines.append(f"/** `{c}` · {' · '.join(notes)} */")
        lines.append(f"export interface {pascal(c)} {{")
        fields = info["fields"]
        for f, d in fields.items():
            if "." in f:
                continue
            subs = {p.split(".", 1)[1]: sd for p, sd in fields.items() if p.startswith((f + ".", f + "[]."))}
            if subs:
                arr_el = lambda sd: {**sd, "type": sd["type"][:-2]} if d["type"].endswith("[]") and sd["type"].endswith("[]") else sd
                body = "; ".join(f"{k if re.match(r'^[A-Za-z_$][\w$]*$', k) else json.dumps(k)}: {ts_type(c, k, arr_el(sd), cols)}" for k, sd in subs.items())
                arr = d["type"].endswith("[]")
                key = f if re.match(r"^[A-Za-z_$][\w$]*$", f) else json.dumps(f)
                refs = [f"{k} -> {sd['ref']}" for k, sd in subs.items() if "ref" in sd]
                note = f"  // {', '.join(refs)}" if refs else ""
                lines.append(f"  {key}: {{ {body} }}{'[]' if arr else ''}{' | null' if d.get('nullable') else ''}{note}")
                continue
            key = f if re.match(r"^[A-Za-z_$][\w$]*$", f) else json.dumps(f)
            note = "  // primary key" if d.get("primary") else (f"  // unique, duplicates: {', '.join(map(str, d['duplicates']))}" if d.get("duplicates") else "") or (f"  // -> {d['ref']}" + (f".{d['ref_key']}" if "ref_key" in d else "") if "ref" in d else "")
            lines.append(f"  {key}: {ts_type(c, f, d, cols)}{note}")
        lines += ["}", ""]
    return "\n".join(lines)


# -- draft report --------------------------------------------------------------

def title_of(row, info):
    """First title-like field, top level before nested (`document.title`), then any short text."""
    fields = [f for f in info["fields"] if "[]" not in f]
    for name in TITLE_FIELDS:
        for f in sorted((f for f in fields if f.rsplit(".", 1)[-1] == name), key=lambda f: f.count(".")):
            v = get(row, f)
            if isinstance(v, str) and v.strip():
                return v.strip()[:120]
    for f in fields:
        d, v = info["fields"][f], get(row, f)
        if d["type"] == "string" and "enum" not in d and "ref" not in d and isinstance(v, str) \
                and v.strip() and not UUID.match(v) and not ISO.match(v):
            return v.strip()[:80]
    return str(row.get(info["primary"]))


def label_of(row, info):
    for f in LABEL_FIELDS:
        v = row.get(f)
        if isinstance(v, (str, int)) and not isinstance(v, bool):
            return str(v)
    pk = row.get(info["primary"])
    return str(pk)[:8] if UUID.match(str(pk)) else str(pk)


def draft(data, schema, title, lang, max_rows):
    cols = schema["collections"]
    eid = lambda c, k: f"{c}:{k}"
    badges = {"kind": {"label": "Collection" if lang != "de" else "Collection · eckig", "shape": "square", "values": {}}}
    shapes = iter(["round", "pill", "dashed", "text"] * 10)
    colors = iter(PALETTE * 10)
    enum_cats = {}
    for c, info in cols.items():
        if info.get("join") or info.get("link_table") or not info["primary"]:
            continue
        badges["kind"]["values"][c] = {"label": c, "color": next(colors), "desc": f"{info['rows']}"}
        for f, d in info["fields"].items():
            if "enum" in d and d["type"] != "boolean":
                cat = f
                if cat in badges and cat not in enum_cats.values():
                    cat = f"{c}.{f}"
                if cat not in badges:
                    badges[cat] = {"label": f, "shape": next(shapes), "values": {}}
                for v in d["enum"]:
                    badges[cat]["values"].setdefault(str(v), {"color": next(colors)})
                enum_cats[(c, f)] = cat
    ents, parent, order, in_tree = {}, {}, {}, set()
    keymap = defaultdict(dict)  # (collection, key field) -> {value: primary key}
    for r in schema["relations"]:
        pk = cols[r["to"]]["primary"]
        if r["key"] != pk:
            m = keymap[(r["to"], r["key"])]
            for row in data[r["to"]]:
                m.setdefault(row.get(r["key"]), row[pk])  # duplicate key: first row wins

    def target(c, f, d, v):
        k = d.get("ref_key")
        return eid(d["ref"], keymap[(d["ref"], k)].get(v) if k else v)

    for c, info in cols.items():
        if info.get("join") or info.get("link_table") or not info["primary"]:
            continue
        rows = data[c][:max_rows]
        for r in rows:
            k = r[info["primary"]]
            b = {"kind": [c]}
            for f, d in info["fields"].items():
                v = get(r, f)
                if (c, f) in enum_cats and v not in (None, []):
                    vals = [x for x in (v if isinstance(v, list) else [v]) if x is not None]
                    b[enum_cats[(c, f)]] = list(dict.fromkeys(str(v) for v in vals))
            meta = [f"`{f}`" for f, d in info["fields"].items() if d["type"] == "boolean" and r.get(f) is True][:4]
            ents[eid(c, k)] = {"id": eid(c, k), "title": title_of(r, info), "label": label_of(r, info),
                               "badges": b, "meta": meta, "refs": []}
            o = next((r.get(f) for f in ORDER_FIELDS if isinstance(r.get(f), (int, float))), None)
            if o is not None:
                order[eid(c, k)] = o
    for c, info in cols.items():
        if not info["primary"] and not info.get("join"):
            continue
        for r in data[c][:max_rows] if not info.get("join") else data[c]:
            j = info.get("join")
            if j:
                fs = info["fields"]
                p = target(c, j["parent"], fs[j["parent"]], r.get(j["parent"])).split(":", 1)[1]
                ch = target(c, j["child"], fs[j["child"]], r.get(j["child"])).split(":", 1)[1]
                if eid(j["of"], p) in ents and eid(j["of"], ch) in ents:
                    parent[eid(j["of"], ch)] = eid(j["of"], p)
                    in_tree.update({eid(j["of"], ch), eid(j["of"], p)})
                    if j["order"] and isinstance(r.get(j["order"]), (int, float)):
                        order[eid(j["of"], ch)] = r[j["order"]]
                continue
            if info.get("link_table"):
                rf = [target(c, f, d, r.get(f)) for f, d in info["fields"].items() if "ref" in d and "." not in f]
                for b in rf[1:]:
                    if rf[0] in ents and b in ents:
                        ents[rf[0]]["refs"].append(b)
                continue
            src = eid(c, r[info["primary"]])
            if src not in ents:
                continue
            h = info.get("hierarchy")
            for f, d in info["fields"].items():
                if "ref" not in d:
                    continue
                for v in refs_of(get(r, f)):
                    tgt = target(c, f, d, v)
                    if tgt not in ents or tgt == src:
                        continue
                    if h and f == h["parent"]:
                        parent[src] = tgt
                        in_tree.update({src, tgt})
                    elif tgt not in ents[src]["refs"]:
                        ents[src]["refs"].append(tgt)
    # Break cycles a bad parent field may cause.
    for k in list(parent):
        seen, cur = {k}, parent.get(k)
        while cur:
            if cur in seen:
                del parent[k]
                break
            seen.add(cur)
            cur = parent.get(cur)
    groups = {}
    for k, e in ents.items():
        c = k.split(":", 1)[0]
        if k in parent:
            e["parent"] = parent[k]
        elif k not in in_tree:
            # Outside any hierarchy: group the rows under one node per collection.
            g = groups.setdefault(c, {"id": f"collection:{c}", "title": c, "label": f"{cols[c]['rows']} rows",
                                      "badges": {"kind": [c]}, "refs": []})
            e["parent"] = g["id"]
        if k in order:
            e["order"] = order[k]
        if not e["refs"]:
            del e["refs"]
        if not e["meta"]:
            del e["meta"]
    entities = list(groups.values()) + list(ents.values())
    rels = schema["relations"]
    kinds = [c for c in badges["kind"]["values"]]
    pos = layout(kinds, rels, cols)
    flow = {"type": "flow", "label": "Datenmodell", "box": [200, 58], "gap": [80, 26],
            "nodes": [{"id": c, "label": c, "sub": f"{cols[c]['rows']} rows", "col": pos[c][0], "row": pos[c][1],
                       "color": badges["kind"]["values"][c]["color"], **({"ref": f"collection:{c}"} if c in groups else {})}
                      for c in kinds],
            "edges": [[r["from"], r["to"]] for r in rels if r["from"] in pos and r["to"] in pos and r["from"] != r["to"]]}
    rel_rows = [[f"`{r['from']}.{r['field']}`", f"`{r['to']}.{r['key']}`", "n" if r["many"] else "1",
                 "Baum" if cols[r["from"]].get("hierarchy", {}).get("parent") == r["field"] or cols[r["from"]].get("join") else "Verweis"]
                for r in rels]
    backs = Counter(t for e in ents.values() for t in e.get("refs", []))
    top = [[k, n] for k, n in backs.most_common(12)]
    sections = [
        {"title": "Datenmodell", "sub": "aus den Werten erkannt", "blocks": [
            flow,
            {"type": "table", "columns": ["Feld", "Ziel", "Kard.", "Art"], "rows": rel_rows or [["—", "—", "—", "—"]]}]},
        {"title": "Baum", "sub": "Hierarchie und Verweise", "blocks": [
            {"type": "tree", "filter": list(badges), "count_label": "sichtbar"}]},
    ]
    if top:
        sections.append({"title": "Meistzitiert", "sub": "eingehende Verweise", "blocks": [{"type": "bars", "items": top, "color": "blue"}]})
    return {"title": title, "lang": lang, "meta": [f"{len(cols)} Collections · {sum(i['rows'] for i in cols.values())} Zeilen",
                                                     "Entwurf von detect.py: Texte, Badges und Abschnitte prüfen"],
            "stats": [["Collections", len(kinds)], ["Entitäten", len(ents)], ["Relationen", len(rels)]],
            "badges": badges, "entities": entities, "sections": sections}


def layout(kinds, rels, cols):
    """Columns by reference depth: referenced collections left, referencing ones right."""
    deps = defaultdict(set)
    for r in rels:
        if r["from"] in kinds and r["to"] in kinds and r["from"] != r["to"]:
            deps[r["from"]].add(r["to"])
    depth = {}

    def d(c, stack=()):
        if c in depth:
            return depth[c]
        if c in stack:
            return 0
        depth[c] = 1 + max((d(x, stack + (c,)) for x in deps[c]), default=-1)
        return depth[c]

    rows = Counter()
    pos = {}
    for c in sorted(kinds, key=lambda c: (d(c), c)):
        rows[d(c)] += 1
    deepest = max((d(c) for c in kinds), default=0)
    seen = Counter()
    for c in sorted(kinds, key=lambda c: (-d(c), c)):
        col = deepest - d(c)  # referencing collections left, referenced ones right: arrows run left to right
        pos[c] = (col, seen[col])
        seen[col] += 1
    return pos


def main():
    args = sys.argv[1:]
    opts = {"--title": "Datenbericht", "--lang": "de", "--max": "500", "--skip": ""}
    pos = []
    while args:
        a = args.pop(0)
        if a in opts:
            opts[a] = args.pop(0)
        else:
            pos.append(a)
    if len(pos) != 2:
        sys.exit(__doc__)
    data = load(pos[0])
    if not data:
        sys.exit(f"{pos[0]}: no collections found")
    schema = detect(data, skip=set(filter(None, opts["--skip"].split(","))))
    out = Path(pos[1])
    out.mkdir(parents=True, exist_ok=True)
    (out / "schema.json").write_text(json.dumps(schema, indent=2, ensure_ascii=False))
    (out / "schema.ts").write_text(to_ts(schema))
    rep = draft(data, schema, opts["--title"], opts["--lang"], int(opts["--max"]))
    (out / "report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False))
    cols = schema["collections"]
    for c, i in cols.items():
        tag = "tree" if i.get("hierarchy") else "join" if i.get("join") else "link" if i.get("link_table") else ""
        refs = [f"{f}->{d['ref']}" + (f".{d['ref_key']}" if "ref_key" in d else "") for f, d in i["fields"].items() if "ref" in d]
        enums = [f for f, d in i["fields"].items() if "enum" in d]
        dups = {f: d["duplicates"] for f, d in i["fields"].items() if d.get("duplicates")}
        print(f"{c:28} {i['rows']:>5} rows  pk={i['primary']}  {tag:4}  refs={refs}  enums={enums}" + (f"  DUPLICATE KEYS={dups}" if dups else ""))
    print(f"-> {out}/schema.json, schema.ts, report.json")


if __name__ == "__main__":
    main()
