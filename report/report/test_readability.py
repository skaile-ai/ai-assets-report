"""Behavioural tests for readable source citations: `[@source text]` in prose and structured `at` values.

Run from the reporting source root:  python3 -m unittest discover -s report -p 'test_readability.py'
The tests assert on rendered HTML fragments, not on the renderer's source text.
"""
import base64
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location("report_build", Path(__file__).with_name("build.py"))
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)


def src(text):
    """The markup of one citation, written out independently of the renderer's helper."""
    return f'<span class="src">[{text}]</span>'


def report(size=None, **extra):
    data = {"title": "T", "lang": "en", "entities": [{"id": "alpha", "title": "Alpha", "label": "A"}], "sections": []}
    data.update(extra)
    return build.Report(data, size=size)


class InlineCitations(unittest.TestCase):
    def setUp(self):
        self.r = report()

    def test_plain_citation(self):
        self.assertEqual(self.r.inline("see [@scripts/import.ts:31] now"), f"see {src('scripts/import.ts:31')} now")

    def test_line_range_and_no_line_suffix(self):
        self.assertEqual(self.r.inline("[@server/screen.ts:36-52]"), src("server/screen.ts:36-52"))
        self.assertEqual(self.r.inline("[@server/screen.ts]"), src("server/screen.ts"))

    def test_spaces_and_surrounding_whitespace(self):
        self.assertEqual(self.r.inline("[@my notes.md section 2]"), src("my notes.md section 2"))
        self.assertEqual(self.r.inline("[@  padded.md  ]"), src("padded.md"))

    def test_long_path_is_kept_whole(self):
        path = "/".join(["packages/some-long-directory-name"] * 6) + "/file.ts:1234"
        self.assertEqual(self.r.inline(f"[@{path}]"), src(path))

    def test_html_is_escaped(self):
        out = self.r.inline("[@a<b>&c.ts:1]")
        self.assertEqual(out, src("a&lt;b&gt;&amp;c.ts:1"))
        self.assertNotIn("<b>", out)

    def test_quotes_are_escaped(self):
        self.assertEqual(self.r.inline('[@a"b\'c]'), src("a&quot;b&#x27;c"))

    def test_url_and_entity_refs_are_literal_text(self):
        self.assertEqual(self.r.inline("[@https://example.com/x]"), src("https://example.com/x"))
        self.assertEqual(self.r.inline("[@alpha]"), src("alpha"))  # not an entity link
        self.assertNotIn("<a ", self.r.inline("[@alpha]"))

    def test_several_citations_in_one_text(self):
        self.assertEqual(self.r.inline("[@a.ts:1] and [@b.ts:2]"), f"{src('a.ts:1')} and {src('b.ts:2')}")


class MalformedTokens(unittest.TestCase):
    def setUp(self):
        self.r = report()

    def assert_literal(self, text, expected):
        out = self.r.inline(text)
        self.assertNotIn('class="src"', out)
        self.assertEqual(out, expected)

    def test_empty_token(self):
        self.assert_literal("a [@] b", "a [@] b")
        self.assert_literal("a [@   ] b", "a [@   ] b")

    def test_unclosed_token(self):
        self.assert_literal("a [@path.ts:1 b", "a [@path.ts:1 b")

    def test_lone_marker_terminates(self):
        self.assert_literal("[@", "[@")
        self.assert_literal("[@[@[@", "[@[@[@")
        self.assert_literal("x[@", "x[@")

    def test_nested_brackets(self):
        self.assert_literal("[@a [b] c]", "[@a [b] c]")

    def test_outer_of_nested_tokens_is_literal(self):
        # the outer token is rejected; the inner one is a well-formed token of its own
        self.assertEqual(self.r.inline("[@a [@b] c]"), f"[@a {src('b')} c]")

    def test_newline_in_token(self):
        self.assert_literal("[@a.ts\nb.ts]", "[@a.ts\nb.ts]")

    def test_malformed_text_is_still_escaped(self):
        self.assert_literal("[@<i>& no end", "[@&lt;i&gt;&amp; no end")

    def test_text_after_failed_token_is_still_parsed(self):
        out = self.r.inline("[@ [[alpha]] `x`")
        self.assertIn('<a href="#e-alpha"', out)
        self.assertIn("<code>x</code>", out)

    def test_plain_brackets_untouched(self):
        self.assert_literal("a [b] c @d", "a [b] c @d")


class CodePrecedence(unittest.TestCase):
    def setUp(self):
        self.r = report()

    def test_token_inside_code_span_stays_literal(self):
        self.assertEqual(self.r.inline("`[@a.ts:1]`"), "<code>[@a.ts:1]</code>")

    def test_code_span_opening_inside_a_token_wins(self):
        out = self.r.inline("[@a `b] c`")
        self.assertNotIn('class="src"', out)
        self.assertIn("<code>b] c</code>", out)

    def test_citation_next_to_code(self):
        self.assertEqual(self.r.inline("`f()` [@a.ts:1]"), f"<code>f()</code> {src('a.ts:1')}")

    def test_code_with_html_stays_escaped(self):
        self.assertEqual(self.r.inline("`<x>`"), "<code>&lt;x&gt;</code>")


class EntityLinks(unittest.TestCase):
    def setUp(self):
        self.r = report()

    def test_entity_link_forms_still_work(self):
        self.assertEqual(self.r.inline("[[alpha]]"), '<a href="#e-alpha" title="Alpha">A</a>')
        self.assertEqual(self.r.inline("[[alpha|see here]]"), '<a href="#e-alpha" title="Alpha">see here</a>')

    def test_adjacent_link_and_citation(self):
        out = self.r.inline("[[alpha]][@a.ts:1]")
        self.assertEqual(out, f'<a href="#e-alpha" title="Alpha">A</a>{src("a.ts:1")}')

    def test_citation_then_link(self):
        out = self.r.inline("[@a.ts:1][[alpha|x]]")
        self.assertEqual(out, f'{src("a.ts:1")}<a href="#e-alpha" title="Alpha">x</a>')

    def test_unknown_entity_ref_still_fails(self):
        with self.assertRaises(SystemExit) as cm:
            self.r.inline("[[nope]]")
        self.assertIn("unknown ref nope", str(cm.exception))

    def test_citation_text_is_never_resolved_as_entity(self):
        self.r.inline("[@nope]")  # must not raise


class StructuredEvidence(unittest.TestCase):
    def test_evidence_row_matches_inline_citation(self):
        r = report()
        out = r.evidence([("Edge", "scripts/import.ts:31")])
        self.assertIn(f"<td>{r.inline('[@scripts/import.ts:31]')}</td>", out)
        self.assertNotIn("<code>scripts/import.ts:31</code>", out)

    def test_evidence_escapes(self):
        out = report().evidence([("E", "a<b>&c.ts")])
        self.assertIn(src("a&lt;b&gt;&amp;c.ts"), out)
        self.assertNotIn("<b>", out)

    def test_evidence_stays_collapsed_and_empty_rows_render_nothing(self):
        r = report()
        self.assertTrue(r.evidence([("E", "x.ts:1")]).startswith('<details class="ev">'))
        self.assertEqual(r.evidence([]), "")

    def test_mermaid_at_uses_same_markup(self):
        r = report(sections=[{"title": "S", "blocks": [
            {"type": "mermaid", "id": "m", "label": "Order", "at": "scripts/import.ts:10", "code": "graph TD; A-->B"}]}])
        page = r.render()
        self.assertIn(src("scripts/import.ts:10"), page)

    def test_lineage_at_cell_and_function_name(self):
        r = report(size="technical", sections=[{"title": "S", "blocks": [
            {"type": "lineage", "id": "l", "types": [{"id": "a", "label": "Raw"}, {"id": "b", "label": "Clean"}, {"id": "c", "label": "Done"}],
             "steps": [{"from": "a", "to": "b", "fn": "clean()", "at": "x/clean.ts:7-9", "note": "see [@n.md:2]"},
                       {"from": "b", "to": "c", "fn": "finish()"}]}]}])
        page = r.render()
        self.assertIn(f"<td>{src('x/clean.ts:7-9')}</td>", page)
        self.assertIn("<code>clean()</code>", page)  # function names stay ordinary code
        self.assertNotIn("<code>x/clean.ts:7-9</code>", page)
        self.assertIn(src("n.md:2"), page)  # note text uses the inline grammar
        self.assertIn("<td>—</td>", page)  # a step without `at` still shows a dash

    def test_states_at_cell_and_caption(self):
        r = report(sections=[{"title": "S", "blocks": [
            {"type": "states", "id": "s", "field": "doc.status", "at": "schema.ts:4",
             "states": [{"id": "new"}, {"id": "done"}],
             "transitions": [{"from": "new", "to": "done", "trigger": "finish", "at": "server/done.ts:5"}]}]}])
        page = r.render()
        self.assertIn(f"<td>{src('server/done.ts:5')}</td>", page)
        self.assertIn(f" · {src('schema.ts:4')}", page)  # caption
        self.assertIn("<code>doc.status</code>", page)  # state field stays code
        self.assertNotIn("<code>schema.ts:4</code>", page)

    def test_explanation_needs_at_only_under_technical(self):
        secs = [{"title": "S", "blocks": [
            {"type": "flow", "id": "f", "nodes": [{"id": "a"}, {"id": "b"}], "edges": [{"from": "a", "to": "b"}]}]}]
        report(profile="explanation", sections=secs)
        with self.assertRaises(SystemExit) as cm:
            report(size="technical", profile="explanation", sections=secs)
        self.assertIn("without at", str(cm.exception))


class Footnotes(unittest.TestCase):
    TEXT = "A [@a.py:1]. B [@b.py:2]. C [@a.py:1]."

    def test_citations_become_numbered_notes_per_section(self):
        page = report(sections=[section("S", self.TEXT)]).render()
        self.assertEqual(page.count('href="#n-1-1"'), 2)
        self.assertEqual(page.count('href="#n-1-2"'), 1)
        self.assertIn('<details class="notes"><summary>Notes (<span class="nn">2</span>)</summary>', page)
        self.assertIn(f'<li id="n-1-1" value="1">{src("a.py:1")}</li>', page)
        para = re.search(r'<p data-src="sections/0/blocks/0">A .*?</p>', page, re.S).group(0)
        self.assertNotIn('<span class="src">', para)

    def test_technical_keeps_inline_brackets(self):
        page = report(size="technical", sections=[section("S", self.TEXT)]).render()
        self.assertIn(f"A {src('a.py:1')}.", page)
        self.assertNotIn('details class="notes"', page)

    def test_source_id_links_to_bibliography_without_note(self):
        page = wr().render()
        self.assertIn('a class="src cite"', page)
        self.assertNotIn('details class="notes"', page)
        self.assertNotIn('class="fn"', page)

    def test_header_meta_stays_inline(self):
        page = report(meta=["Source: [@x]"], sections=[section("S")]).render()
        self.assertIn(src("x"), page)
        self.assertNotIn('class="fn"', page)

    @staticmethod
    def depth(*blocks):
        """A report with reader depths; the notes under test sit in section 2."""
        secs = [section("Answer"), {"title": "S", "blocks": list(blocks)}]
        return report(readers=READERS_CFG, sections=secs).render()

    def test_note_cited_only_from_a_deeper_block_carries_its_reader(self):
        page = self.depth({"type": "p", "text": "Plain [@a.py:1]."},
                          {"type": "p", "text": "Deep [@b.py:2].", "reader": "professional"})
        self.assertIn(f'<li id="n-2-1" value="1">{src("a.py:1")}</li>', page)
        self.assertIn(f'<li id="n-2-2" value="2" data-reader="professional">{src("b.py:2")}</li>', page)
        self.assertIn('<details class="notes"><summary>Notes (<span class="nn">2</span>)</summary>', page)

    def test_note_also_cited_from_a_general_block_stays_general(self):
        page = self.depth({"type": "p", "text": "Deep [@a.py:1].", "reader": "professional"},
                          {"type": "p", "text": "Plain [@a.py:1]."})
        self.assertIn(f'<span id="n-2-1">{src("a.py:1")}</span>', page)
        self.assertIn('<p class="notes notes-1">', page)

    def test_section_with_only_deeper_notes_hides_the_whole_list(self):
        page = self.depth({"type": "p", "text": "Plain."},
                          {"type": "p", "text": "Deep [@a.py:1].", "reader": "professional"})
        self.assertIn('<details class="notes" data-reader="professional"><summary>', page)
        self.assertIn(f'<li id="n-2-1" value="1" data-reader="professional">{src("a.py:1")}</li>', page)


class TreeRows(unittest.TestCase):
    def page(self, size=None):
        return report(size=size, sections=[{"title": "S", "blocks": [{"type": "p", "text": "Rows."}, {"type": "tree"}]}]).render()

    def test_id_group_only_under_technical(self):
        self.assertNotIn('<span class="id">', self.page())
        self.assertIn('<span class="id">A</span>', self.page("technical"))


class HeaderMeta(unittest.TestCase):
    def test_header_meta_renders_citations(self):
        page = report(meta=["Source: [@a/b.ts:3]", "Date: 2026-10-18"]).render()
        self.assertIn(f"Source: {src('a/b.ts:3')}<br>Date: 2026-10-18", page)

    def test_header_meta_escapes_html(self):
        page = report(meta=["<script>x</script>"]).render()
        self.assertNotIn("<script>x</script>", page)
        self.assertIn("&lt;script&gt;x&lt;/script&gt;", page)


class LinkLabels(unittest.TestCase):
    def link(self, ent, ref):
        data = {"title": "T", "lang": "en", "entities": [dict(ent, id="n05")], "sections": []}
        return build.Report(data).inline(ref)

    def test_label_wins_over_title(self):
        out = self.link({"title": "Install script", "label": "Install"}, "[[n05]]")
        self.assertEqual(out, '<a href="#e-n05" title="Install script">Install</a>')

    def test_title_when_no_label(self):
        out = self.link({"title": "Install script"}, "[[n05]]")
        self.assertEqual(out, '<a href="#e-n05" title="Install script">Install script</a>')

    def test_id_when_neither(self):
        self.assertEqual(self.link({}, "[[n05]]"), '<a href="#e-n05" title="n05">n05</a>')

    def test_explicit_text_is_never_overridden(self):
        out = self.link({"title": "Install script", "label": "Install"}, "[[n05|the installer]]")
        self.assertEqual(out, '<a href="#e-n05" title="Install script">the installer</a>')

    def test_label_text_is_escaped(self):
        out = self.link({"title": "<b>x</b>"}, "[[n05]]")
        self.assertIn(">&lt;b&gt;x&lt;/b&gt;</a>", out)
        self.assertNotIn("<b>", out)


def section(title, text="Body."):
    return {"title": title, "blocks": [{"type": "p", "text": text}]}


class PageOrder(unittest.TestCase):
    STATS = [["Files", "three"]]

    def pos(self, page, needle):
        self.assertIn(needle, page)
        return page.index(needle)

    def test_first_section_precedes_statistics_and_rest_follow(self):
        page = report(stats=self.STATS, sections=[section("Answer"), section("Detail")]).render()
        h1, first, stats, second = (self.pos(page, n) for n in ("<h1>", 'class="lede"', '<dl class="stats">', "Detail"))
        self.assertTrue(h1 < first < stats < second)

    def test_change_summary_between_first_and_second_section(self):
        first = dict(section("Answer"), change="new")
        page = report(stats=self.STATS, sections=[first, section("Detail")]).render()
        a, stats, bar, detail = (self.pos(page, n) for n in ('class="lede', '<dl class="stats">', 'class="chgbar"', "Detail"))
        self.assertTrue(a < stats < bar < detail)

    def test_change_summary_without_stats(self):
        page = report(sections=[dict(section("Answer"), change="new"), section("Detail")]).render()
        self.assertTrue(self.pos(page, 'class="lede') < self.pos(page, 'class="chgbar"') < self.pos(page, "Detail"))

    def test_since_without_marks_says_nothing_changed(self):
        page = report(since="r-v1", sections=[section("Answer"), section("Detail")]).render()
        self.assertIn('<div class="chgbar"><span>Changes since r-v1:</span><span class="cn">none</span></div>', page)

    def test_no_sections_header_then_statistics_and_change_summary(self):
        page = report(stats=self.STATS, sections=[]).render()
        self.assertTrue(self.pos(page, "</header>") < self.pos(page, '<dl class="stats">'))
        self.assertNotIn("<section", page)

    def test_numbering_and_anchors_survive_reordering(self):
        page = report(stats=self.STATS, sections=[dict(section("Answer"), id="ans"), dict(section("Detail"), id="det")]).render()
        self.assertIn('<section id="ans" class="lede" data-src="sections/0">', page)
        self.assertIn('<section id="det" aria-labelledby="det-t" data-src="sections/1"><h2 id="det-h" aria-labelledby="det-t"><span class="sn">1 </span><span id="det-t">Detail', page)


class Provenance(unittest.TestCase):
    def test_no_meta_no_disclosure(self):
        page = report().render()
        self.assertNotIn('class="provenance"', page)
        self.assertNotIn("prov-print", page.split("</style>")[-1])

    def test_english_disclosure_is_collapsed(self):
        page = report(meta=["Run: 1"]).render()
        self.assertIn('<details class="provenance"><summary>Sources and run details</summary><p>Run: 1</p></details>', page)
        self.assertNotIn("<details class=\"provenance\" open", page)

    def test_german_disclosure(self):
        page = report(lang="de", meta=["Lauf: 1"]).render()
        self.assertIn('<details class="provenance"><summary>Quellen und Laufdetails</summary>', page)

    def test_disclosure_keeps_citations_and_lines(self):
        page = report(meta=["A [@x.ts:1]", "B"]).render()
        self.assertIn(f"<p>A {src('x.ts:1')}<br>B</p></details>", page)

    def test_print_copy_carries_the_same_text(self):
        page = report(meta=["A [@x.ts:1]"]).render()
        self.assertIn(f'<p class="prov-print">A {src("x.ts:1")}</p>', page)

    def test_disclosure_sits_in_header_before_first_section(self):
        page = report(meta=["M"], sections=[section("Answer")]).render()
        self.assertTrue(page.index('<details class="provenance">') < page.index("</header>") < page.index("<section"))


class ChoiceCheck(unittest.TestCase):
    def check(self, features, data=None, **choice):
        with tempfile.NamedTemporaryFile("w", suffix=".choice.json", delete=False) as f:
            json.dump({"profile": "critique", "features": features, **choice}, f)
        return build.check_choice(data or {"sections": [section("Answer")]}, f.name)

    def questions(self, n):
        return [{"id": f"q{i}", "chapter": "c", "text": f"Question {i}?", "feature": "none"} for i in range(1, n + 1)]

    def answered(self, n):
        return {"sections": [section("Answer"), *({**section(f"S{i}"), "question": f"q{i}"} for i in range(1, n + 1))]}

    def test_none_is_a_known_feature(self):
        self.check(["none", "find"])

    def test_unknown_feature_still_fails(self):
        with self.assertRaises(SystemExit) as cm:
            self.check(["none", "sparkles"])
        self.assertIn("unknown feature keys sparkles", str(cm.exception))

    def test_missing_size_is_medium(self):
        self.assertEqual(self.check(["none"]), "medium")

    def test_unknown_size_fails(self):
        with self.assertRaises(SystemExit) as cm:
            self.check(["none"], size="huge")
        self.assertIn("size must be one of", str(cm.exception))

    def test_small_caps_questions(self):
        with self.assertRaises(SystemExit) as cm:
            self.check(["none"], self.answered(3), size="small", questions=self.questions(3))
        self.assertIn("size small allows at most 2 questions", str(cm.exception))
        self.assertEqual(self.check(["none"], self.answered(2), size="small", questions=self.questions(2)), "small")

    def test_medium_caps_six_questions(self):
        with self.assertRaises(SystemExit) as cm:
            self.check(["none"], self.answered(7), questions=self.questions(7))
        self.assertIn("size medium allows at most 6 questions", str(cm.exception))

    def test_small_rejects_feature_keys(self):
        with self.assertRaises(SystemExit) as cm:
            self.check(["none", "flow"], size="small")
        self.assertIn("size small does not allow flow", str(cm.exception))

    def test_small_rejects_vega(self):
        vega = {"sections": [{"title": "Answer", "blocks": [{"type": "vega", "id": "v", "spec": {}}]}]}
        with self.assertRaises(SystemExit) as cm:
            self.check(["charts"], vega, size="small")
        self.assertIn("allows bars, not vega", str(cm.exception))
        bars = {"sections": [{"title": "Answer", "blocks": [{"type": "bars", "items": [["a", 1]]}]}]}
        self.assertEqual(self.check(["charts"], bars, size="small"), "small")


class Sizes(unittest.TestCase):
    def sized(self, size, *secs):
        return report(size=size, sections=list(secs)).lint()

    def test_sentences(self):
        self.assertEqual(build.sentences("Runs at 4.38.0. Done [@a.py:1]."), 2)
        self.assertEqual(build.sentences("Call `x.y()` now"), 1)
        self.assertEqual(build.sentences(""), 0)
        self.assertEqual(build.sentences("Why? Because!"), 2)

    def test_small_opening_lint(self):
        out = self.sized("small", section("Answer", "One. Two. Three."))
        self.assertIn('size small: section "Answer" opens with 3 sentences (max 2)', out)
        out = self.sized("small", section("Answer", "One. Two."))
        self.assertFalse([line for line in out if line.startswith("size ")])

    def test_medium_allows_three_sentences(self):
        out = self.sized("medium", section("Answer", "One. Two. Three."))
        self.assertFalse([line for line in out if line.startswith("size ")])
        out = self.sized("medium", section("Answer", "One. Two. Three. Four."))
        self.assertIn('size medium: section "Answer" opens with 4 sentences (max 3)', out)

    def test_technical_requires_citation(self):
        gap = 'size technical: section "Next" has no [@…] citation and no at'
        out = self.sized("technical", section("Answer"), section("Next", "No source."))
        self.assertIn(gap, out)
        out = self.sized("technical", section("Answer"), section("Next", "Read [@a.py:1]."))
        self.assertNotIn(gap, out)
        at = {"title": "Next", "blocks": [{"type": "p", "text": "No source."},
                                          {"type": "mermaid", "id": "m", "label": "Order", "at": "a.py:1", "code": "graph TD; A-->B"}]}
        self.assertNotIn(gap, self.sized("technical", section("Answer"), at))

    def test_technical_requires_at_on_edges(self):
        flow = {"type": "flow", "id": "f", "nodes": [{"id": "a"}, {"id": "b"}], "edges": [{"from": "a", "to": "b"}]}
        data = {"title": "T", "lang": "en", "profile": "critique", "sections": [{"title": "Answer", "blocks": [flow]}]}
        with self.assertRaises(SystemExit) as cm:
            build.Report(data, size="technical")
        self.assertIn("without at", str(cm.exception))
        build.Report(data, size="medium")

    def test_unknown_size_fails_construction(self):
        with self.assertRaises(SystemExit) as cm:
            build.Report({"title": "T", "lang": "en", "sections": []}, size="huge")
        self.assertIn("size must be one of", str(cm.exception))


class VideoBlock(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        for name in ("v.mp4", "v.jpg", "v.vtt"):
            (self.dir / name).write_bytes(b"x")

    def video(self, lang="en", **extra):
        block = {"type": "video", "id": "demo", "src": "v.mp4"}
        block.update(extra)
        r = report(lang=lang)
        r.out_dir = self.dir
        return r.b_video(block)

    def fails(self, **extra):
        with self.assertRaises(SystemExit) as cm:
            self.video(**extra)
        return str(cm.exception)

    def test_chapters_render_as_seek_buttons(self):
        out = self.video(chapters=[{"t": 0, "label": "1. Answer"}, {"t": 75.5, "label": "2. <Flow> & more"}])
        self.assertEqual(out.count("<button type=\"button\" data-t="), 2)
        self.assertIn('<li><button type="button" data-t="0"><span class="t">0:00</span>1. Answer</button></li>', out)
        self.assertIn('data-t="75.5"><span class="t">1:15</span>2. &lt;Flow&gt; &amp; more</button>', out)

    def test_chapter_list_precedes_caption(self):
        out = self.video(chapters=[{"t": 0, "label": "A"}], caption="Cap.")
        self.assertTrue(out.index('<ol class="vch">') < out.index('<p class="mt">'))

    def test_no_chapters_no_list(self):
        self.assertNotIn("vch", self.video())

    def test_chapter_validation(self):
        bad = [
            [{"t": 5, "label": "x"}, {"t": 2, "label": "y"}],  # not ascending
            [{"t": 5, "label": "x"}, {"t": 5, "label": "y"}],  # not strictly ascending
            [{"t": -1, "label": "x"}],
            [{"t": "5", "label": "x"}],
            [{"t": True, "label": "x"}],
            [{"label": "x"}],
            [{"t": 1, "label": ""}],
            [{"t": 1, "label": "  "}],
            [{"t": 1}],
            ["x"],
        ]
        for chapters in bad:
            with self.subTest(chapters=chapters):
                self.assertIn("video demo: chapters[", self.fails(chapters=chapters))

    def test_chapter_error_names_the_index(self):
        msg = self.fails(chapters=[{"t": 5, "label": "x"}, {"t": 2, "label": "y"}])
        self.assertIn("video demo: chapters[1] needs numeric ascending t and a label", msg)

    def test_track_is_inlined_with_report_language(self):
        (self.dir / "v.vtt").write_text("WEBVTT\n\n00:00.000 --> 00:01.000\nHällo\n", encoding="utf-8")
        out = self.video(lang="de", track="v.vtt")
        m = re.search(r'<track kind="captions" src="data:text/vtt;base64,([A-Za-z0-9+/=]+)" srclang="de" label="DE" default>', out)
        self.assertIsNotNone(m)
        self.assertEqual(base64.b64decode(m.group(1)), (self.dir / "v.vtt").read_bytes())
        self.assertTrue(out.index("<track ") < out.index("</video>"))

    def test_track_found_next_to_report_json_is_inlined(self):
        src_dir = self.dir / "src"
        src_dir.mkdir()
        (src_dir / "r.json").write_text("{}")
        (src_dir / "c.vtt").write_bytes(b"WEBVTT\n")
        r = report()
        r.out_dir, r.src = self.dir, src_dir / "r.json"
        out = r.b_video({"type": "video", "id": "demo", "src": "v.mp4", "track": "c.vtt"})
        self.assertIn("base64," + base64.b64encode(b"WEBVTT\n").decode(), out)

    def test_no_track_no_element(self):
        self.assertNotIn("<track", self.video())

    def test_missing_track_file_fails(self):
        self.assertIn("video demo: file not found missing.vtt", self.fails(track="missing.vtt"))

    def test_src_is_required(self):
        r = report()
        r.out_dir = self.dir
        with self.assertRaises(SystemExit) as cm:
            r.b_video({"type": "video", "id": "demo"})
        self.assertIn("video demo: `src` is required", str(cm.exception))


READERS_CFG = {"default": "informed", "levels": [
    {"id": "general", "label": "Kurz", "description": "Das Wichtigste."},
    {"id": "informed", "label": "Mehr", "description": "Dazu die Gründe."},
    {"id": "professional", "label": {"de": "Fach", "en": "Pro"}, "description": "Dazu die Belege."}]}
SOURCES = [{"id": "S1", "title": "Leitlinie Knick-Senkfuß", "url": "https://example.org/a", "publisher": "AWMF", "year": 2023,
            "kind": "guideline", "read": "2026-10-19", "note": "Konsens."},
           {"id": "S2", "title": "Review", "url": "https://example.org/b"}]


def wr(sections=None, **extra):
    """A web-research report; the first section holds the answer paragraph."""
    secs = sections if sections is not None else [
        {"title": "Antwort", "blocks": [{"type": "p", "text": "Kurz gesagt: meist harmlos [@S1]."}]},
        {"title": "Details", "blocks": [{"type": "p", "text": "Mehr."}]}]
    return report(profile="web-research", lang="de", sources=SOURCES, readers=READERS_CFG, sections=secs, **extra)


def body(page):
    """The report markup: the page without the template's CSS and script."""
    return page[page.index("<body>"):]


def fails(fn, *args, **kw):
    with unittest.TestCase().assertRaises(SystemExit) as cm:
        fn(*args, **kw)
    return str(cm.exception)


class SourceLinks(unittest.TestCase):
    def test_exact_id_links_to_the_bibliography_record(self):
        out = wr().inline("Siehe [@S1] und [@S2].")
        self.assertEqual(out, 'Siehe <a class="src cite" href="#src-S1" title="Leitlinie Knick-Senkfuß">[S1]</a> und '
                              '<a class="src cite" href="#src-S2" title="Review">[S2]</a>.')

    def test_other_citation_text_stays_a_literal_span(self):
        r = wr()
        for text in ("a.ts:1", "S1.pdf", "S1 S2", " S1 ", "alpha"):
            with self.subTest(text=text):
                self.assertEqual(r.inline(f"[@{text}]"), src(text.strip()))

    def test_unknown_source_like_id_fails(self):
        self.assertIn("names no source id", fails(wr().inline, "Beleg [@S9]"))

    def test_without_sources_old_reports_keep_literal_ids(self):
        self.assertEqual(report().inline("[@S9]"), src("S9"))

    def test_source_records_are_validated(self):
        ok = {"id": "S1", "title": "T", "url": "https://example.org"}
        self.assertIn("duplicate source id S1", fails(report, sources=[ok, dict(ok)]))
        self.assertIn("`title` is required", fails(report, sources=[{"id": "S1", "url": "https://x.org"}]))
        self.assertIn("`url` is required", fails(report, sources=[{"id": "S1", "title": "T"}]))
        self.assertIn("`url` must start with http", fails(report, sources=[dict(ok, url="ftp://x")]))
        self.assertIn("`id` is required", fails(report, sources=[{"title": "T", "url": "https://x.org"}]))

    def test_bibliography_follows_the_sections_and_links_out(self):
        page = wr().render()
        self.assertTrue(page.index('<span id="s-1-t">Details</span>') < page.index('<section id="sources"'))
        self.assertIn('<li id="src-S1" class="bi">', page)
        self.assertIn('<a class="bi-t" href="https://example.org/a" rel="noopener noreferrer">Leitlinie Knick-Senkfuß</a>', page)
        self.assertIn("AWMF · 2023", page)
        self.assertIn("gelesen 2026-10-19", page)
        self.assertIn("example.org", page)

    def test_no_reader_depth_hides_the_bibliography(self):
        section = re.search(r'<section id="sources".*?</section>', wr().render(), re.S).group(0)
        self.assertNotIn("data-reader", section)

    def test_uncited_source_is_linted(self):
        lints = wr().lint()
        self.assertIn("source S2: never cited", lints)
        self.assertNotIn("source S1: never cited", lints)

    def test_web_research_without_sources_is_linted(self):
        r = report(profile="web-research", sections=[])
        self.assertIn("web-research: no top-level `sources`", r.lint())


class MediaBlock(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        (self.dir / "out").mkdir()
        (self.dir / "r.media").mkdir()
        (self.dir / "r.media" / "a.jpg").write_bytes(b"x")
        (self.dir / "r.media" / "b.png").write_bytes(b"x")

    def item(self, **extra):
        return {"src": "r.media/a.jpg", "alt": "Fuß von der Seite", "caption": "Längsgewölbe [@S1].", "credit": "Max Muster", **extra}

    def media(self, *items):
        r = wr()
        r.out_dir, r.src = self.dir / "out", self.dir / "r.json"
        return r.b_media({"type": "media", "items": list(items)})

    def test_figure_img_figcaption_with_credit_and_licence(self):
        out = self.media(self.item(href="https://commons.example/File:a", license="CC BY 4.0", license_url="https://cc.example/4.0"))
        self.assertIn('<figure class="mf"><img src="../r.media/a.jpg" alt="Fuß von der Seite" loading="lazy" decoding="async">', out)
        self.assertIn("<figcaption>", out)
        self.assertIn('<a href="https://commons.example/File:a" rel="noopener noreferrer">Max Muster</a>', out)
        self.assertIn('<a href="https://cc.example/4.0" rel="noopener noreferrer">CC BY 4.0</a>', out)
        self.assertIn('href="#src-S1"', out)  # captions use the inline grammar

    def test_path_is_rewritten_relative_to_the_output(self):
        self.assertIn('src="../r.media/b.png"', self.media(self.item(src="r.media/b.png")))
        (self.dir / "out" / "c.png").write_bytes(b"x")
        self.assertIn('src="c.png"', self.media(self.item(src="c.png")))  # next to the output: unchanged

    def test_gallery_has_one_or_two_columns(self):
        self.assertIn('class="gal" data-n="1"', self.media(self.item()))
        self.assertIn('class="gal" data-n="2"', self.media(self.item(), self.item(src="r.media/b.png"), self.item()))

    def test_missing_file_fails(self):
        self.assertIn("media item 1: file not found r.media/none.jpg", fails(self.media, self.item(src="r.media/none.jpg")))

    def test_alt_caption_credit_are_required(self):
        for key in ("alt", "caption", "credit", "src"):
            for bad in ("", "  "):
                with self.subTest(key=key, bad=bad):
                    self.assertIn(f"media item 1: `{key}` is required", fails(self.media, self.item(**{key: bad})))

    def test_remote_src_and_bad_links_fail(self):
        self.assertIn("local file", fails(self.media, self.item(src="https://x.org/a.jpg")))
        self.assertIn("`href` must be an http(s) URL", fails(self.media, self.item(href="javascript:1")))
        self.assertIn("`license_url` needs `license`", fails(self.media, self.item(license_url="https://cc.example")))

    def test_empty_items_fail(self):
        self.assertIn("`items` must be a non-empty list", fails(self.media))


class GalleryBlock(unittest.TestCase):
    BADGES = {"kind": {"label": "Kind", "values": {"list": {"color": "blue"}}}}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        (self.dir / "out").mkdir()
        (self.dir / "r.media").mkdir()
        for name in ("a.png", "b.png"):
            (self.dir / "r.media" / name).write_bytes(b"x")

    def item(self, **extra):
        return {"src": "r.media/a.png", "title": "Orders", "caption": "All orders.", **extra}

    def notes(self):
        return [{"x": 10, "y": 20, "text": "Two primary buttons.", "sev": 3, "ref": "alpha"},
                {"x": 50.5, "y": 60, "w": 20, "h": 10, "text": "Tiny targets."}]

    def gallery(self, *items, **extra):
        r = report(badges=self.BADGES)
        r.out_dir, r.src = self.dir / "out", self.dir / "r.json"
        return r.b_gallery({"type": "gallery", "items": list(items), **extra})

    def page(self, *items):
        data = {"title": "T", "lang": "en", "entities": [{"id": "alpha", "title": "Alpha", "label": "A", "tree": False}],
                "sections": [{"title": "Answer", "blocks": [{"type": "gallery", "items": list(items)}]}]}
        return body(build.Report(data, out_dir=self.dir / "out", src=self.dir / "r.json").render())

    def test_pins_one_per_note_with_box_and_note_list(self):
        out = self.gallery(self.item(notes=self.notes()))
        self.assertEqual(out.count('class="gl-p"'), 2)
        self.assertIn('<span class="gl-p" data-sev="3" style="left:10%;top:20%">1</span>', out)
        self.assertIn('<span class="gl-b" style="left:50.5%;top:60%;width:20%;height:10%"></span>', out)
        self.assertIn('<ol class="gl-n"><li data-n="1"><b class="gl-s" data-sev="3">S3</b> Two primary buttons. → '
                      '<a href="#e-alpha"', out)
        self.assertIn('<span class="gl-c">2 notes</span>', out)
        self.assertIn('<button type="button" class="gl-o" aria-label="Open Orders">', out)
        self.assertIn('alt="Orders"', out)  # alt defaults to title

    def test_src_and_before_are_rewritten_relative_to_the_output(self):
        out = self.gallery(self.item(before="r.media/b.png"))
        self.assertIn('<img src="../r.media/a.png"', out)
        self.assertIn('data-before="../r.media/b.png"', out)

    def test_entity_anchor_and_badges(self):
        out = self.gallery(self.item(entity="alpha", badges={"kind": ["list"]}))
        self.assertIn('<figure class="gl-i" id="e-alpha">', out)
        self.assertIn(">list</span>", out)
        self.assertNotIn(' id="', self.gallery(self.item()))

    def test_entity_anchor_is_a_link_target_on_the_page(self):
        out = self.page(self.item(entity="alpha", caption="See [[alpha]]."))
        self.assertIn('id="e-alpha"', out)

    def test_validation_messages(self):
        cases = [
            ((), "gallery: `items` must be a non-empty list"),
            ((self.item(src=""),), "gallery item 1: `src` is required and must not be empty"),
            ((self.item(title="  "),), "gallery item 1: `title` is required and must not be empty"),
            ((self.item(), self.item(src="https://x.org/a.png")),
             "gallery item 2: `src` must be a local file next to the report, not a URL"),
            ((self.item(before="//x.org/a.png"),), "gallery item 1: `before` must be a local file next to the report, not a URL"),
            ((self.item(notes=[{"x": 101, "y": 1, "text": "t"}]),), "gallery item 1 note 1: x and y must be numbers from 0 to 100"),
            ((self.item(notes=[{"x": 1, "text": "t"}]),), "gallery item 1 note 1: x and y must be numbers from 0 to 100"),
            ((self.item(notes=[{"x": 1, "y": 1, "w": -1, "text": "t"}]),), "gallery item 1 note 1: w and h must be numbers from 0 to 100"),
            ((self.item(notes=[{"x": 1, "y": 1, "text": "t"}, {"x": 1, "y": 1, "sev": 5, "text": "t"}]),),
             "gallery item 1 note 2: `sev` must be an integer 0-4"),
            ((self.item(notes=[{"x": 1, "y": 1, "sev": 2.5, "text": "t"}]),), "gallery item 1 note 1: `sev` must be an integer 0-4"),
            ((self.item(src="r.media/none.png"),), "gallery item 1: file not found r.media/none.png"),
        ]
        for items, msg in cases:
            with self.subTest(msg=msg):
                self.assertIn(msg, fails(self.gallery, *items))

    def test_unknown_refs_fail(self):
        self.assertIn("unknown ref zzz", fails(self.gallery, self.item(notes=[{"x": 1, "y": 1, "text": "t", "ref": "zzz"}])))
        self.assertIn("gallery item 1: unknown ref zzz", fails(self.gallery, self.item(entity="zzz")))

    def test_choice_check_fails_when_gallery_is_not_chosen(self):
        data = {"sections": [section("Answer"), {"title": "Screens", "blocks": [{"type": "gallery", "items": [self.item()]}]}]}
        with tempfile.NamedTemporaryFile("w", suffix=".choice.json", delete=False) as f:
            json.dump({"profile": "critique", "features": ["none"]}, f)
        self.assertIn("used but not chosen: gallery", fails(build.check_choice, data, f.name))
        with tempfile.NamedTemporaryFile("w", suffix=".choice.json", delete=False) as f:
            json.dump({"profile": "critique", "features": ["gallery"], "size": "small"}, f)
        self.assertEqual(build.check_choice(data, f.name), "small")


class ResourcesAndCallouts(unittest.TestCase):
    def test_resources_render_external_cards(self):
        out = wr().b_resources({"type": "resources", "items": [
            {"title": "NHS", "url": "https://www.nhs.uk/x", "description": "Überblick [@S1].", "audience": "Eltern", "kind": "Patienteninfo"}]})
        self.assertIn('<a class="rc-t" href="https://www.nhs.uk/x" rel="noopener noreferrer">NHS</a>', out)
        self.assertIn("Für Eltern", out)
        self.assertIn("Patienteninfo", out)
        self.assertIn("www.nhs.uk", out)
        self.assertIn('href="#src-S1"', out)

    def test_resources_validate(self):
        item = {"title": "T", "url": "https://x.org", "description": "D"}
        r = wr()
        self.assertIn("`url` must start with http", fails(r.b_resources, {"items": [dict(item, url="/local")]}))
        self.assertIn("`description` is required", fails(r.b_resources, {"items": [dict(item, description="")]}))
        self.assertIn("`title` is required", fails(r.b_resources, {"items": [{k: v for k, v in item.items() if k != "title"}]}))
        self.assertIn("non-empty list", fails(r.b_resources, {"items": []}))

    def test_callout_names_its_tone_and_labels_itself(self):
        out = wr().b_callout({"type": "callout", "tone": "safety", "title": "Arzt aufsuchen", "text": "Bei Schmerz.", "items": ["Fieber", "Rötung [@S1]"]})
        self.assertIn('class="co co-safety" role="group" aria-labelledby="co-1"', out)
        self.assertIn('<span class="co-k">Sicherheit</span> <strong id="co-1">Arzt aufsuchen</strong>', out)
        self.assertEqual(out.count("<li>"), 2)

    def test_callout_ids_are_unique(self):
        r = wr()
        a = r.b_callout({"tone": "note", "title": "A", "text": "x"})
        b = r.b_callout({"tone": "action", "title": "B", "text": "x"})
        self.assertIn('id="co-1"', a)
        self.assertIn('id="co-2"', b)

    def test_callout_validation(self):
        r = wr()
        self.assertIn("tone must be one of", fails(r.b_callout, {"tone": "loud", "title": "T", "text": "x"}))
        self.assertIn("`title` is required", fails(r.b_callout, {"tone": "note", "title": " ", "text": "x"}))
        self.assertIn("`text` is required", fails(r.b_callout, {"tone": "note", "title": "T"}))


class ReaderDepth(unittest.TestCase):
    def sections(self, *blocks, **sec):
        return [{"title": "Antwort", "blocks": [{"type": "p", "text": "Antwort."}]}, dict({"title": "Mehr", "blocks": list(blocks)}, **sec)]

    def test_block_wrapper_carries_the_minimum_depth(self):
        page = wr(self.sections({"type": "p", "text": "Allgemein."}, {"type": "p", "text": "Fach.", "reader": "professional"},
                                {"type": "p", "text": "Mehr.", "reader": "informed"})).render()
        self.assertIn('<div class="rd" data-reader="professional"><p data-src="sections/1/blocks/1">Fach.</p></div>', page)
        self.assertIn('<div class="rd" data-reader="informed"><p data-src="sections/1/blocks/2">Mehr.</p></div>', page)
        self.assertIn('<p data-src="sections/1/blocks/0">Allgemein.</p>', page)
        self.assertNotIn('data-reader="general"', page)

    def test_section_and_contents_entry_carry_the_depth(self):
        page = wr(self.sections({"type": "p", "text": "x"}, reader="professional")).render()
        self.assertIn('<section id="s-1" data-reader="professional" aria-labelledby="s-1-t" data-src="sections/1">', page)
        self.assertIn('<li data-reader="professional"><a href="#s-1">1 Mehr</a></li>', page)

    def test_control_is_three_toggle_buttons_with_json_labels(self):
        page = wr().render()
        ctl = re.search(r'<div class="rdc".*?</div>', page, re.S).group(0)
        self.assertIn('role="group" aria-labelledby="rdl"', ctl)
        self.assertIn('data-default="informed"', ctl)
        self.assertEqual(re.findall(r'<button type="button" data-depth="(\w+)" data-desc="[^"]*" aria-pressed="false">([^<]+)</button>', ctl),
                         [("general", "Kurz"), ("informed", "Mehr"), ("professional", "Fach")])
        self.assertIn('<span id="rdl" class="rdl">Lesetiefe</span>', ctl)

    def test_label_object_follows_the_report_language(self):
        page = report(profile="web-research", lang="en", sources=SOURCES, readers=READERS_CFG, sections=[]).render()
        self.assertIn(">Pro</button>", page)
        self.assertIn('<span id="rdl" class="rdl">Reading depth</span>', page)

    def test_screen_rule_hides_deeper_levels_and_print_is_untouched(self):
        css = Path(build.__file__).with_name("template.html").read_text()
        rule = re.search(r"@media screen\{([^{}]*\[data-reader[^{}]*)\{display:none!important\}\}", css)
        self.assertIsNotNone(rule)
        self.assertIn("html[data-depth=informed] [data-reader=professional]", rule.group(1))
        self.assertIn("html[data-depth=general] [data-reader=informed]", rule.group(1))
        self.assertNotIn("html[data-depth=professional]", rule.group(1))

    def test_answer_paragraph_never_hides(self):
        secs = [{"title": "Antwort", "blocks": [{"type": "p", "text": "A.", "reader": "professional"}]}]
        self.assertIn("answer paragraph stays visible", fails(wr, secs))
        secs = [{"title": "Antwort", "reader": "informed", "blocks": [{"type": "p", "text": "A."}]}]
        self.assertIn("first section", fails(wr, secs))

    def test_safety_and_action_callouts_never_hide(self):
        for tone in ("safety", "action"):
            callout = {"type": "callout", "tone": tone, "title": "T", "text": "x"}
            with self.subTest(tone=tone):
                self.assertIn("would hide a safety or action callout", fails(wr, self.sections(dict(callout, reader="professional"))))
                self.assertIn("would hide a safety or action callout", fails(wr, self.sections(callout, reader="professional")))
                tabs = {"type": "tabs", "reader": "informed", "tabs": [{"label": "t", "blocks": [callout]}]}
                self.assertIn("would hide a safety or action callout", fails(wr, self.sections(tabs)))
        note = {"type": "callout", "tone": "note", "title": "T", "text": "x", "reader": "professional"}
        self.assertIn('data-reader="professional"', wr(self.sections(note)).render())

    def test_reader_needs_config_and_a_known_level(self):
        secs = self.sections({"type": "p", "text": "x", "reader": "professional"})
        self.assertIn("needs a top-level `readers`", fails(report, sections=secs))
        self.assertIn("reader must be one of", fails(wr, self.sections({"type": "p", "text": "x", "reader": "expert"})))

    def test_readers_config_is_validated(self):
        cfg = lambda **kw: dict(READERS_CFG, **kw)
        self.assertIn("exactly one entry", fails(report, readers=cfg(levels=READERS_CFG["levels"][:2])))
        self.assertIn("default must be one of", fails(report, readers=cfg(default="expert")))
        levels = [dict(READERS_CFG["levels"][0], label=""), *READERS_CFG["levels"][1:]]
        self.assertIn("level general needs a `label`", fails(report, readers=cfg(levels=levels)))

    def test_no_config_no_control_for_old_reports(self):
        page = body(report(sections=[section("Answer")]).render())
        self.assertNotIn("rdc", page)
        self.assertNotIn("data-reader", page)


class WebResearchPage(unittest.TestCase):
    def test_landmarks_skip_link_and_contents(self):
        page = wr().render()
        self.assertTrue(page.index('<a class="skip" href="#main">Zum Inhalt springen</a>') < page.index("<header>"))
        self.assertIn('<main id="main" class="wr" tabindex="-1" data-find-scope>', page)
        self.assertIn('<nav class="toc" aria-label="Inhalt">', page)
        nav = re.search(r"<nav.*?</nav>", page, re.S).group(0)
        self.assertEqual(re.findall(r'<a href="#([^"]+)">', nav), ["s-1", "sources"])
        for target in ("s-1", "sources"):
            self.assertIn(f'id="{target}"', page)
        self.assertIn('<section id="s-1" aria-labelledby="s-1-t" data-src="sections/1"><h2 id="s-1-h" aria-labelledby="s-1-t"><span class="sn">1 </span><span id="s-1-t">Details', page)

    def test_contents_uses_author_section_ids(self):
        secs = [dict(section("Answer"), id="ans"), dict(section("Rest"), id="rest")]
        self.assertIn('<a href="#rest">1 Rest</a>', wr(secs).render())

    def test_find_box_has_live_count_clear_and_scope(self):
        page = body(wr().render())
        self.assertRegex(page, r'<input id="find" type="search" placeholder="[^"]+" aria-label="Im Bericht suchen" aria-controls="main" '
                               r'data-hit="Treffer" data-hits="Treffer" data-hidden="\+\{n\} in geschlossenen Teilen" data-row="Zeile" data-rows="Zeilen" '
                               r'data-pos="\{i\} von \{n\}">')
        self.assertIn('<button type="button" id="findx" class="fclr" hidden>Suche zurücksetzen</button>', page)
        self.assertIn('<span id="findn" role="status" aria-live="polite"></span>', page)
        self.assertTrue(page.index('id="find"') < page.index("<main"))
        # the sources are inside the searched region
        self.assertTrue(page.index("<main") < page.index('id="src-S1"') < page.index("</main>"))

    def test_other_profiles_keep_their_structure(self):
        page = body(report(sections=[section("Answer")]).render())
        for marker in ('<nav class="toc"', 'id="find"'):
            self.assertNotIn(marker, page)
        self.assertIn('<main id="main" tabindex="-1" data-find-scope>', page)
        self.assertIn('<section class="lede" data-src="sections/0">', page)

    def test_find_box_searches_the_whole_page_in_every_profile(self):
        r = report(badges={}, sections=[{"title": "S", "blocks": [{"type": "data", "id": "d", "columns": [{"key": "a"}], "rows": [{"a": "x"}]}]}])
        page = body(r.render())
        self.assertIn('<input id="find" type="search" placeholder="Find…" aria-label="Search the report" aria-controls="main" '
                      'data-hit="match" data-hits="matches" data-hidden="+{n} in closed parts" data-row="row" data-rows="rows" data-pos="{i} of {n}">', page)
        self.assertIn('<main id="main" tabindex="-1" data-find-scope>', page)
        self.assertIn('id="findx"', page)
        # a contents list alone (no tree, no table) brings the box too
        self.assertIn('id="find"', body(PageStructure.five()))

    def test_whole_page_with_every_new_block_builds(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        (d / "a.jpg").write_bytes(b"x")
        secs = [
            {"title": "Antwort", "blocks": [
                {"type": "p", "text": "Antwort [@S1]."},
                {"type": "callout", "tone": "answer", "title": "Kurz", "text": "Meist harmlos."},
                {"type": "argument", "claim": "Meist harmlos", "reasons": ["Weil A.", "Weil B."], "conclusion": "Also abwarten."},
                {"type": "example", "title": "Kind, 6", "setup": "Ein Fall.", "steps": ["Schritt 1."], "result": "Gut."},
                {"type": "compare", "title": "Einlage oder Übung", "columns": [{"label": "Einlage", "text": "Teuer."},
                 {"label": "Übung", "items": ["Billig.", "Wirksam."]}], "verdict": "Übung zuerst."}]},
            {"title": "Bilder", "blocks": [
                {"type": "media", "items": [{"src": "a.jpg", "alt": "A", "caption": "C", "credit": "X"}]},
                {"type": "resources", "items": [{"title": "T", "url": "https://x.org", "description": "D"}], "reader": "informed"},
                {"type": "flow", "id": "f", "dir": "down", "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
                 "edges": [{"from": "a", "to": "b"}]},
                {"type": "table", "columns": ["Übung", "Dosis"], "rows": [["Zehenstand", "3×10"]], "caption": "Plan", "reader": "professional"}]}]
        page = build.Report(wr(secs).d, out_dir=d, src=d / "r.json").render()
        self.assertIn("<main", page)
        for k in ('class="arg"', 'class="ex"', 'class="cmp"', '<span class="blk-l">Gründe</span>', '<span class="blk-l">Ergebnis</span>', '<span class="blk-l">Fazit</span>'):
            self.assertIn(k, page)


ARG = {"type": "argument", "claim": "Claim", "reasons": ["R1.", "R2."], "conclusion": "So this."}
EXAMPLE = {"type": "example", "title": "One row", "setup": "Setup.", "steps": ["S1.", "S2.", "S3."], "result": "Done."}
COMPARE = {"type": "compare", "title": "A or B", "columns": [{"label": "A", "text": "Cheap."}, {"label": "B", "items": ["Fast.", "Big."]}],
           "verdict": "Take A."}


class ExplainBlocks(unittest.TestCase):
    def page(self, b, **extra):
        extra.setdefault("profile", "explanation")
        return body(report(sections=[{"title": "S", "blocks": [{"type": "p", "text": "Lead."}, b]}], **extra).render())

    def test_argument_renders(self):
        out = report().b_argument(ARG)
        self.assertTrue(out.startswith('<div class="arg" role="group" aria-labelledby="ag-1"><p class="co-h">'
                                       '<strong id="ag-1">Claim</strong></p><p><span class="blk-l">Because</span></p><ol class="ste">'))
        self.assertIn('<p class="arg-s"><span class="blk-l">So</span> So this.</p></div>', out)
        self.assertEqual(out.count("<li>"), 2)
        self.assertIn('<span class="blk-l">Gründe</span>', self.page(ARG, lang="de"))

    def test_example_renders(self):
        out = report().b_example(EXAMPLE)
        self.assertIn('<p class="co-h"><strong id="ex-1">One row</strong>', out)
        self.assertIn('<p class="ex-r"><span class="blk-l">Result</span> Done.</p>', out)
        self.assertEqual(out.count("<li>"), 3)
        self.assertIn('class="ex"', self.page(EXAMPLE))

    def test_compare_renders(self):
        out = report().b_compare(COMPARE)
        self.assertIn('<p class="co-h"><strong id="cp-1">A or B</strong></p><div class="cmp-g">', out)
        self.assertIn('<p class="cmp-v"><span class="blk-l">Verdict</span> Take A.</p></div>', out)
        self.assertEqual(out.count('class="cmp-c"'), 2)
        self.assertEqual(out.count("<li>"), 2)
        self.assertIn('class="cmp"', self.page(COMPARE, profile="structure"))

    def test_argument_with_four_reasons_fails(self):
        self.assertIn("argument: `reasons` needs 1 to 3 non-empty items",
                      fails(report().b_argument, dict(ARG, reasons=["a", "b", "c", "d"])))

    def test_example_without_result_fails(self):
        b = {k: v for k, v in EXAMPLE.items() if k != "result"}
        self.assertIn("example: `result` is required and must not be empty", fails(report().b_example, b))

    def test_compare_with_three_columns_fails(self):
        self.assertIn("compare: `columns` needs exactly 2 columns",
                      fails(report().b_compare, dict(COMPARE, columns=COMPARE["columns"] + [{"label": "C", "text": "x"}])))

    def test_compare_with_empty_items_fails_even_with_text(self):
        cols = [dict(COMPARE["columns"][0], text="x", items=[""]), COMPARE["columns"][1]]
        self.assertIn("compare: column 1 needs `label` and `text` or `items`", fails(report().b_compare, dict(COMPARE, columns=cols)))


class ResponsiveTable(unittest.TestCase):
    def table(self, **extra):
        return report().b_table({"type": "table", "columns": ["Übung", "Dosis", "n"], "numeric": [2],
                                 "rows": [["Zehenstand", "3×10", 4], {"cells": ["Ball rollen", "2 min", 0], "anchor": "rowa"}], **extra})

    def test_every_cell_names_its_column(self):
        out = self.table()
        self.assertEqual(re.findall(r'<td role="cell" class="[^"]*" data-label="([^"]*)">', out), ["Übung", "Dosis", "n"] * 2)

    def test_semantics_stay_in_the_markup(self):
        out = self.table()
        self.assertIn('<table class="rsp" role="table">', out)
        self.assertIn('<thead role="rowgroup"><tr role="row"><th role="columnheader" class="">Übung</th>', out)
        self.assertIn('<tbody role="rowgroup">', out)
        self.assertIn('<tr role="row" id="e-rowa">', out)
        self.assertIn('class="n zero"', out)

    def test_caption_only_when_supplied(self):
        self.assertNotIn("<caption>", self.table())
        self.assertIn("<caption>Plan [@a.ts:1]</caption>".replace("[@a.ts:1]", src("a.ts:1")), self.table(caption="Plan [@a.ts:1]"))

    def test_narrow_screens_switch_rows_to_labelled_cards(self):
        css = Path(build.__file__).with_name("template.html").read_text()
        narrow = css[css.index("@media(max-width:640px){\n .tw:has(>table.rsp)"):]
        narrow = narrow[:narrow.index("\n}\n")]
        self.assertIn("table.rsp td::before{content:attr(data-label)", narrow)
        self.assertIn("table.rsp tr{", narrow)

    def test_code_column_is_capped_not_nowrap(self):
        out = report().b_table({"type": "table", "columns": ["Lint line", "Fix"],
                                "rows": [["`stat {label}: literal, source {src}`", "prefer `count` so the build counts it"], ["`source {id}: never cited`", ""]]})
        self.assertEqual(re.findall(r'<td role="cell" class="([^"]*)" data-label="Lint line">', out), ["cd", "cd"])
        self.assertEqual(re.findall(r'<td role="cell" class="([^"]*)" data-label="Fix">', out), ["", ""])
        self.assertEqual(re.findall(r'class="([^"]*)" data-label="Übung"', self.table()), ["nw", "nw"])
        css = Path(build.__file__).with_name("template.html").read_text()
        self.assertIn("table.rsp td.cd code{display:inline-block;max-width:40ch", css)

    def test_data_tables_stay_plain(self):
        data = {"type": "data", "id": "d", "columns": [{"key": "a"}], "rows": [{"a": "x"}]}
        self.assertNotIn("rsp", report().b_data(data))


class VerticalFlow(unittest.TestCase):
    def flow(self, **extra):
        b = {"type": "flow", "id": "f", "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], "edges": [{"from": "a", "to": "b"}], **extra}
        return report().b_flow(b)

    def test_down_flow_keeps_a_minimum_scale(self):
        svg = re.search(r'<svg [^>]*class="dg[ "][^>]*>', self.flow(dir="down")).group(0)
        self.assertIn('class="dg dgv"', svg)
        self.assertRegex(svg, r'style="width:clamp\(\d+px,100%,\d+px\);height:auto"')

    def test_right_flow_is_unchanged(self):
        svg = re.search(r'<svg [^>]*class="dg[ "][^>]*>', self.flow()).group(0)
        self.assertIn('class="dg"', svg)
        self.assertIn("width:clamp(", svg)


class BoardBlock(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        (self.dir / "out").mkdir()
        (self.dir / "r.media").mkdir()
        (self.dir / "r.media" / "a.jpg").write_bytes(b"x")

    def board(self, cards=None, changes=None, more=None):
        """A board with a today canvas (cards a, b + `changes`) and a proposed canvas (card c + `more` cards)."""
        return {"type": "board", "id": "mb", "label": "Screens", "canvases": [
            {"id": "today", "label": "Today", "lanes": [
                {"tone": "today", "cards": cards or [{"id": "a", "title": "List"}, {"id": "b", "title": "Preview"}],
                 "changes": changes or []}]},
            {"id": "next", "label": "Next", "lanes": [
                {"tone": "proposed", "cards": [{"id": "c", "title": "Editor"}] + (more or [])}]}]}

    def page(self, b):
        data = {"title": "T", "lang": "en", "entities": [{"id": "alpha", "title": "Alpha", "label": "A"}],
                "sections": [{"title": "Answer", "blocks": [{"type": "tree"}, b]}]}
        return build.Report(data, out_dir=self.dir / "out", src=self.dir / "r.json").render()

    def test_unknown_mark_kind_fails(self):
        msg = fails(self.page, self.board(cards=[{"id": "a", "title": "List", "marks": ["shuffle"]}]))
        self.assertIn("mark kind must be one of", msg)
        self.assertIn("shuffle", msg)

    def test_change_to_a_missing_card_fails(self):
        for key in ("from", "to"):
            msg = fails(self.page, self.board(changes=[{"mark": "move", "text": "Moves.", key: "zzz"}]))
            self.assertIn(f"`{key}` zzz is not a card id of board mb", msg)

    def test_duplicate_card_id_fails(self):
        self.assertIn("duplicate id a", fails(self.page, self.board(more=[{"id": "a", "title": "Again"}])))

    def test_missing_local_image_fails(self):
        card = {"id": "a", "title": "List", "image": {"src": "r.media/none.jpg", "alt": "List"}}
        self.assertIn("not found r.media/none.jpg", fails(self.page, self.board(cards=[card])))

    def test_image_is_rewritten_relative_to_the_output(self):
        card = {"id": "a", "title": "List", "image": {"src": "r.media/a.jpg", "alt": "List"}}
        self.assertIn('<img src="../r.media/a.jpg" alt="List"', self.page(self.board(cards=[card])))

    def test_mark_renders_kind_class_and_qualifier(self):
        out = body(self.page(self.board(cards=[{"id": "a", "title": "List", "marks": ["reuse picker", "new"]}])))
        self.assertRegex(out, r'<span class="bom bom-reuse">[^<]+ <span class="boq">picker</span></span>')
        self.assertRegex(out, r'<span class="bom bom-new">[^<]+</span>')

    def test_change_links_a_card_on_the_other_canvas(self):
        out = body(self.page(self.board(changes=[{"mark": "move", "text": "Moves.", "from": "a", "to": "c"}])))
        self.assertIn('<a href="#f-mb-a">List</a>', out)
        self.assertIn('<a href="#f-mb-c">Editor</a>', out)
        self.assertIn('id="f-mb-c"', out)
        self.assertIn('id="f-mb-next"', out)

    def test_card_ref_links_the_entity(self):
        out = body(self.page(self.board(cards=[{"id": "a", "title": "List", "ref": "alpha"}])))
        self.assertRegex(out, r'<p class="bok-e"><a [^>]*href="#e-alpha"')

    def test_choice_check_fails_when_board_is_not_chosen(self):
        data = {"sections": [section("Answer"), {"title": "Screens", "blocks": [self.board()]}]}
        with tempfile.NamedTemporaryFile("w", suffix=".choice.json", delete=False) as f:
            json.dump({"profile": "critique", "features": ["none"]}, f)
        self.assertIn("board", fails(build.check_choice, data, f.name))
        with tempfile.NamedTemporaryFile("w", suffix=".choice.json", delete=False) as f:
            json.dump({"profile": "critique", "features": ["board"]}, f)
        self.assertEqual(build.check_choice(data, f.name), "medium")


class SourcePointers(unittest.TestCase):
    def test_sections_and_blocks_carry_their_pointer(self):
        secs = [section("Answer"), {"title": "Detail", "blocks": [{"type": "p", "text": "One."}, {"type": "p", "text": "Two."}]}]
        page = body(report(sections=secs).render())
        self.assertIn('<section id="s-1" aria-labelledby="s-1-t" data-src="sections/1">', page)
        self.assertIn('<p data-src="sections/1/blocks/1">Two.</p>', page)

    def test_blocks_inside_tabs_extend_the_pointer(self):
        tabs = {"type": "tabs", "tabs": [{"label": "a", "blocks": [{"type": "p", "text": "First."}]},
                                         {"label": "b", "blocks": [{"type": "p", "text": "Second."}]}]}
        page = body(report(sections=[{"title": "S", "blocks": [tabs]}]).render())
        self.assertIn('data-src="sections/0/blocks/0"', page)
        self.assertIn('<p data-src="sections/0/blocks/0/tabs/1/blocks/0">Second.</p>', page)

    def test_reader_wrapper_holds_the_stamped_element(self):
        secs = [{"title": "Antwort", "blocks": [{"type": "p", "text": "Antwort."}]},
                {"title": "Mehr", "blocks": [{"type": "p", "text": "Fach.", "reader": "professional"}]}]
        page = body(wr(secs).render())
        self.assertIn('<div class="rd" data-reader="professional"><p data-src="sections/1/blocks/0">Fach.</p></div>', page)

    def test_html_without_a_root_tag_is_wrapped(self):
        page = body(report(sections=[{"title": "S", "blocks": [{"type": "html", "html": "plain"}]}]).render())
        self.assertIn('<div data-src="sections/0/blocks/0">plain</div>', page)

    def test_header_names_the_source_file(self):
        data = {"title": "T", "lang": "en", "sections": [section("Answer")]}
        self.assertIn('<header data-report="r.json">', build.Report(data, src=Path("x/r.json")).render())
        self.assertIn("<header>", build.Report(data).render())


class ChoiceMode(unittest.TestCase):
    QS = [{"id": "q1", "chapter": "c", "text": "Question?", "feature": "tree"}]
    DATA = {"sections": [section("Answer"), {**section("Tree"), "question": "q1"}]}

    def check(self, choice, data=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.choice.json"
            path.write_text(json.dumps({"profile": "structure", **choice}))
            return build.check_choice(data or self.DATA, path)

    def test_unknown_mode_fails(self):
        self.assertIn("mode must be ask or autopilot", fails(self.check, {"features": ["none"], "mode": "fast"}))

    def test_autopilot_rejects_extras(self):
        choice = {"features": ["tree", "crossfilter"], "mode": "autopilot", "questions": self.QS}
        self.assertIn("autopilot chooses no extras, found crossfilter", fails(self.check, choice))

    def test_autopilot_with_question_features_passes(self):
        self.assertEqual(self.check({"features": ["tree"], "mode": "autopilot", "questions": self.QS}), "medium")

    def test_no_mode_is_ask(self):
        self.assertEqual(self.check({"features": ["tree", "crossfilter"], "questions": self.QS}), "medium")


class LinkAndListLints(unittest.TestCase):
    ENTS = [{"id": k, "title": k.upper(), "label": k} for k in "abcd"]

    def lints(self, *blocks):
        return report(entities=self.ENTS, sections=[{"title": "S", "blocks": list(blocks)}]).lint()

    def has(self, lints, prefix):
        return [x for x in lints if x.startswith(prefix)]

    def test_links_in_code_spans_do_not_count(self):
        lints = self.lints({"type": "p", "text": "Write `[[a]]` or `[[a]]`, `[[b]]` and `[[c]]` to link."})
        self.assertEqual(self.has(lints, "links:"), [])

    def test_links_per_block(self):
        four = self.lints({"type": "p", "text": "See [[a]], [[b]], [[c]] and [[d]]."})
        self.assertIn('links: section "S": a p block has 4 links (max 3)', four)
        three = self.lints({"type": "p", "text": "See [[a]], [[b]] and [[c]]."})
        self.assertEqual(self.has(three, "links:"), [])

    def test_same_id_twice(self):
        twice = self.lints({"type": "p", "text": "See [[a]]."}, {"type": "p", "text": "Again [[a|A]]."})
        self.assertIn('links: section "S": [[a]] is linked 2 times (link once, then name it)', twice)
        once = self.lints({"type": "p", "text": "See [[a]]."}, {"type": "p", "text": "Again A."})
        self.assertEqual(self.has(once, "links:"), [])

    def test_list_without_lead(self):
        first = self.lints({"type": "bullets", "items": ["x", "y"]})
        self.assertIn('lists: section "S": a bullets block has no lead sentence (put a p before it)', first)
        led = self.lints({"type": "p", "text": "Two things."}, {"type": "bullets", "items": ["x", "y"]})
        self.assertEqual(self.has(led, "lists:"), [])

    def test_list_heavy_section(self):
        heavy = self.lints({"type": "p", "text": "Five things."}, {"type": "bullets", "items": list("vwxyz")})
        self.assertIn('lists: section "S" has 5 list items and 1 sentences of prose', heavy)
        light = self.lints({"type": "p", "text": "Three things."}, {"type": "bullets", "items": list("xyz")})
        self.assertEqual(self.has(light, "lists:"), [])

    def test_long_paragraph_without_link_is_fine(self):
        lints = self.lints({"type": "p", "text": " ".join(["word"] * 80) + "."})
        self.assertEqual([x for x in lints if "0 links" in x or x.startswith("orphan")], [])


def concepts(**extra):
    b = {"type": "concepts", "id": "c", "label": "Terms", "parts": ["views", "gloss"],
         "kinds": {"place": {"label": "Place", "color": "blue"}},
         "terms": [{"id": "space", "label": "Space", "kind": "place", "def": "A room."}],
         "presets": [{"id": "now", "label": "Now", "set": {"plan": False}}, {"id": "plan", "label": "Plan", "set": {"plan": True}}],
         "baseline": "now",
         "views": [{"label": "Sidebar", "layout": "tree", "items": [{"id": "s", "label": "Glass", "icon": "folder-kanban", "term": "space"}]}]}
    b.update(extra)
    return b


class Brand(unittest.TestCase):
    def page(self, **extra):
        return report(sections=[section("Answer")], **extra).render()

    def test_default_brand_is_skaile(self):
        page = self.page()
        self.assertIn("--acc:#7300ff", page)
        self.assertIn("family=Plus+Jakarta+Sans", page)
        self.assertIn('<img class="brand" src="data:image/svg+xml;base64,', page)
        self.assertIn('<link rel="icon" href="data:image/svg+xml;base64,', page)

    def test_builtin_brand_by_name_drops_the_logo(self):
        page = self.page(brand="github")
        self.assertIn("--acc:#0969da", page)
        self.assertNotIn('class="brand"', page)

    def test_brand_file_overrides_tokens_key_by_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "b.json").write_text(json.dumps({"page": {"acc": "#123456"}, "logo": None}))
            page = build.Report({"title": "T", "lang": "en", "brand": "b.json", "sections": [section("A")]}, src=Path(tmp, "r.json")).render()
        self.assertIn("--acc:#123456", page)
        self.assertIn("--paper:#ffffff", page)  # untouched tokens come from skaile

    def test_brand_rejects_a_value_that_is_no_colour(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "b.json").write_text(json.dumps({"page": {"acc": "red;}body{display:none"}}))
            with self.assertRaises(SystemExit) as cm:
                build.Report({"title": "T", "lang": "en", "brand": "b.json", "sections": [section("A")]}, src=Path(tmp, "r.json")).render()
        self.assertIn("page.acc must be a colour", str(cm.exception))

    def test_unknown_brand_name_fails(self):
        with self.assertRaises(SystemExit) as cm:
            self.page(brand="nope")
        self.assertIn("neither a built-in brand", str(cm.exception))


class ConceptsBlock(unittest.TestCase):
    def spec(self, b):
        out = report().b_concepts(b)
        return json.loads(re.search(r'<script type="application/json">(.*?)</script>', out).group(1))

    def test_icon_names_become_platform_svg(self):
        item = self.spec(concepts())["views"][0]["items"][0]
        self.assertNotIn("icon", item)
        self.assertIn("<path", item["svg"])

    def test_figure_carries_the_anchor(self):
        self.assertIn('<figure class="cm" data-concepts id="f-c">', report().b_concepts(concepts()))

    def test_when_with_an_unknown_state_key_fails(self):
        views = [{"label": "S", "layout": "tree", "items": [{"id": "s", "label": "x", "when": {"tabs": True}}]}]
        with self.assertRaises(SystemExit) as cm:
            report().b_concepts(concepts(views=views))
        self.assertIn("`when` maps state keys (plan)", str(cm.exception))

    def test_unknown_term_fails(self):
        views = [{"label": "S", "layout": "tree", "items": [{"id": "s", "label": "x", "term": "thread"}]}]
        with self.assertRaises(SystemExit) as cm:
            report().b_concepts(concepts(views=views))
        self.assertIn("unknown term 'thread'", str(cm.exception))

    def test_graph_needs_a_position_per_term(self):
        with self.assertRaises(SystemExit) as cm:
            report().b_concepts(concepts(parts=["graph"], graph={"pos": {}}))
        self.assertIn("graph.pos misses terms ['space']", str(cm.exception))

    def test_duplicate_item_id_in_a_view_fails(self):
        items = [{"id": "s", "label": "x", "when": {"plan": False}}, {"id": "s", "label": "x", "depth": 1, "when": {"plan": True}}]
        with self.assertRaises(SystemExit) as cm:
            report().b_concepts(concepts(views=[{"label": "S", "layout": "tree", "items": items}]))
        self.assertIn("item ids must be unique per view", str(cm.exception))

    def test_preset_vs_must_name_another_preset(self):
        presets = [{"id": "now", "label": "Now", "set": {"plan": False}}, {"id": "plan", "label": "Plan", "set": {"plan": True}, "vs": "plan"}]
        with self.assertRaises(SystemExit) as cm:
            report().b_concepts(concepts(presets=presets))
        self.assertIn("preset plan `vs` must name another preset", str(cm.exception))

    def test_runtime_ships_once_in_head(self):
        page = report(sections=[{"title": "A", "blocks": [{"type": "p", "text": "x."}, concepts(), concepts(id="d")]}]).render()
        self.assertEqual(page.count("figure[data-concepts]"), 1)


class MockBlock(unittest.TestCase):
    PANE = {"label": "Today", "title": "Create agent", "body": [{"label": "Name", "value": "Clerk", "n": 1}], "buttons": [{"label": "Save", "primary": True}]}

    def test_pins_point_at_notes(self):
        out = report().b_mock({"type": "mock", "id": "m", "panes": [self.PANE], "notes": ["Name twice."]})
        self.assertIn('<label>Name <span class="mk-n">1</span></label>', out)
        self.assertIn('<li><span class="mk-n">1</span>Name twice.</li>', out)

    def test_pin_without_note_fails(self):
        with self.assertRaises(SystemExit) as cm:
            report().b_mock({"type": "mock", "id": "m", "panes": [self.PANE]})
        self.assertIn("pin 1 has no note", str(cm.exception))


class CritiqueBuildFixes(unittest.TestCase):
    check = ChoiceCheck.check
    questions = ChoiceCheck.questions
    answered = ChoiceCheck.answered

    def run_check(self, features, blocks, capsys=None):
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.check(features, {"sections": [{"title": "S", "blocks": blocks}]})
        return buf.getvalue()

    DATA = {"type": "data", "id": "d", "listen": ["v"]}

    def test_crossfilter_used_when_data_listens(self):
        out = self.run_check(["data", "crossfilter"], [self.DATA])
        self.assertIn("choice: crossfilter chosen=yes used=yes", out)

    def test_crossfilter_used_but_not_chosen_fails(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_check(["data"], [self.DATA])
        self.assertIn("used but not chosen: crossfilter", str(cm.exception))

    def test_data_without_listen_does_not_use_crossfilter(self):
        out = self.run_check(["data", "crossfilter"], [{"type": "data", "id": "d"}])
        self.assertIn("choice: crossfilter chosen=yes used=no", out)

    def test_badge_chart_used_when_tree_drives_a_chart(self):
        blocks = [{"type": "bars", "id": "b1", "items": [["a", 1]]}, {"type": "tree", "drives": ["b1"]}]
        out = self.run_check(["tree", "charts", "badge-chart"], blocks)
        self.assertIn("choice: badge-chart chosen=yes used=yes", out)

    def test_tree_driving_a_flow_is_not_badge_chart(self):
        blocks = [{"type": "flow", "id": "f1"}, {"type": "tree", "drives": ["f1"]}]
        out = self.run_check(["tree", "flow"], blocks)
        self.assertIn("choice: badge-chart chosen=no used=no", out)

    def test_badge_chart_used_but_not_chosen_fails(self):
        blocks = [{"type": "bars", "id": "b1", "items": [["a", 1]]}, {"type": "tree", "drives": ["b1"]}]
        with self.assertRaises(SystemExit) as cm:
            self.run_check(["tree", "charts"], blocks)
        self.assertIn("used but not chosen: badge-chart", str(cm.exception))

    def test_detailed_caps_eight_questions(self):
        with self.assertRaises(SystemExit) as cm:
            self.check(["none"], self.answered(9), size="detailed", questions=self.questions(9))
        self.assertIn("size detailed allows at most 8 questions", str(cm.exception))
        self.assertEqual(self.check(["none"], self.answered(8), size="detailed", questions=self.questions(8)), "detailed")

    def test_help_prints_the_lint_catalogue(self):
        import subprocess, sys
        for flag in ("--help", "-h"):
            r = subprocess.run([sys.executable, str(Path(__file__).with_name("build.py")), flag], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            self.assertIn("prose: section", r.stdout)
            self.assertIn("badge colour", r.stdout)

    def test_mock_pane_label_is_h3(self):
        out = report().b_mock({"type": "mock", "id": "m", "panes": [MockBlock.PANE], "notes": ["Name twice."]})
        self.assertIn("<h3>Today</h3>", out)
        self.assertNotIn("<h5", out)


class RedundancyLints(unittest.TestCase):
    FLOW = {"type": "flow", "id": "f", "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], "edges": [{"from": "a", "to": "b"}]}

    def lints(self, *blocks, **extra):
        return report(sections=[{"title": "S", "blocks": list(blocks)}], **extra).lint()

    def has(self, lints, prefix):
        return [x for x in lints if x.startswith(prefix)]

    def test_narrated_figure(self):
        out = self.has(self.lints({"type": "p", "text": "The chart shows the counts."}), "prose: section")
        self.assertEqual(out, ['prose: section "S": "The chart shows the counts.…" narrates the figure; say what it means'])
        self.assertEqual(self.has(self.lints({"type": "p", "text": "Most sites sit in the board renderer."}), "prose: section"), [])

    def test_so_recap_after_figure(self):
        out = self.has(self.lints({"type": "p", "text": "Lead."}, self.FLOW, {"type": "p", "text": "So the page waits."}), "prose: section")
        self.assertEqual(out, ['prose: section "S" ends on a "So …" recap of its figure'])
        self.assertEqual(self.has(self.lints({"type": "p", "text": "So the page waits."}), "prose: section"), [])

    def test_repeated_numbers(self):
        three = [{"type": "p", "text": f"Block {w} has 199 files."} for w in "abc"]
        self.assertEqual(self.has(self.lints(*three), "numbers:"), ['numbers: "199" appears in 3 prose blocks (state it once, then refer to it)'])
        self.assertEqual(self.has(self.lints(*three[:2]), "numbers:"), [])

    def test_orphan_stat(self):
        stats = [["Files", {"value": 42, "source": "x.txt"}]]
        out = self.has(self.lints({"type": "p", "text": "Nothing here."}, stats=stats), 'stat "Files"')
        self.assertIn('stat "Files": 42 is never discussed in the prose', out)
        self.assertEqual(self.has(self.lints({"type": "p", "text": "There are 42 files."}, stats=stats), 'stat "Files": 42 is never'), [])


class PageStructure(unittest.TestCase):
    @staticmethod
    def five(**sub):
        secs = [dict(section(f"S{i}"), **sub) if i > 1 else section("Answer") for i in range(1, 6)]
        return report(profile="explanation", sections=secs).render()

    def test_toc_main_and_skip_link_for_every_profile(self):
        page = self.five()
        self.assertIn('<nav class="toc"', page)
        self.assertIn('<main id="main" tabindex="-1" data-find-scope>', page)
        self.assertIn('<a class="skip" href="#main">', page)

    def test_toc_needs_four_sections_after_the_lede(self):
        four = report(profile="explanation", sections=[section(f"S{i}") for i in range(1, 5)]).render()
        self.assertNotIn('<nav class="toc"', four)

    def test_first_section_is_the_lede(self):
        page = self.five()
        lede = re.search(r"<section[^>]*>.*?</section>", page, re.S).group(0)
        self.assertIn('class="lede"', lede)
        self.assertNotIn("<h2", lede)
        nav = re.search(r"<nav.*?</nav>", page, re.S).group(0)
        self.assertEqual(re.findall(r'<a href="#([^"]+)">', nav), ["s-1", "s-2", "s-3", "s-4"])

    def test_second_section_heading(self):
        page = self.five()
        self.assertIn('<section id="s-1" aria-labelledby="s-1-t" data-src="sections/1"><h2 id="s-1-h" aria-labelledby="s-1-t"><span class="sn">1 </span><span id="s-1-t">S2</span><a class="ha" href="#s-1"', page)

    def test_chapter_label_shows_once_per_sub(self):
        page = self.five(sub="How it runs")
        self.assertEqual(page.count('<p class="chap">How it runs</p>'), 1)
        self.assertNotIn("<span>How it runs</span></h2>", page)

    def test_chapter_label_changes_with_sub(self):
        secs = [section("Answer"), dict(section("A"), sub="One"), dict(section("B"), sub="Two"), dict(section("C"), sub="Two")]
        page = report(sections=secs).render()
        self.assertEqual(re.findall(r'<p class="chap">([^<]*)</p>', page), ["One", "Two"])

    def test_toc_groups_entries_by_sub(self):
        secs = [section("Answer"), dict(section("A"), sub="One"), dict(section("B"), sub="One"), section("C"), section("D")]
        nav = re.search(r"<nav.*?</nav>", report(sections=secs).render(), re.S).group(0)
        self.assertEqual(nav.count('<li class="toc-g"><span>One</span>'), 1)
        self.assertIn('<li><a href="#s-3">3 C</a></li>', nav)


class ColourRoles(unittest.TestCase):
    def test_explanation_blocks_use_blk_l_not_co_k(self):
        r = report()
        for out in (r.b_argument(ARG), r.b_example(EXAMPLE), r.b_compare(COMPARE)):
            self.assertIn('class="blk-l"', out)
            self.assertNotIn("co-k", out)
            self.assertNotIn("arg-l", out)

    def badges(self, second_colour):
        return {"c1": {"label": "C1", "values": {"a": {"color": "green"}, "b": {"color": "blue"}}},
                "c2": {"label": "C2", "values": {"x": {"color": second_colour}}}}

    def test_shared_colour_across_categories_lints(self):
        lines = report(badges=self.badges("green")).lint()
        hit = [x for x in lines if x.startswith("badge colour green:")]
        self.assertEqual(len(hit), 1)
        self.assertIn("c1=a", hit[0])
        self.assertIn("c2=x", hit[0])
        self.assertIn("(one colour, one meaning)", hit[0])

    def test_distinct_colours_or_one_category_give_no_line(self):
        self.assertFalse([x for x in report(badges=self.badges("teal")).lint() if x.startswith("badge colour")])
        one = {"c1": {"label": "C1", "values": {"a": {"color": "green"}, "b": {"color": "green"}}}}
        self.assertFalse([x for x in report(badges=one).lint() if x.startswith("badge colour")])


class RepeatedChrome(unittest.TestCase):
    @staticmethod
    def flow(gid):
        return {"type": "flow", "id": gid, "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], "edges": [{"from": "a", "to": "b"}]}

    def test_repeated_legend_collapses(self):
        page = report(sections=[{"title": "S", "blocks": [self.flow("f"), self.flow("g")]}]).render()
        self.assertEqual(page.count('<details class="lgx"><summary>Legend</summary>'), 1)
        self.assertLess(page.index('id="f-g"'), page.index('<details class="lgx">'))

    def test_single_general_note_renders_inline(self):
        page = report(sections=[section("S", "A [@a.py:1].")]).render()
        self.assertIn('class="notes notes-1"', page)
        self.assertIn(f'<span id="n-1-1">{src("a.py:1")}</span>', page)
        self.assertIn('href="#n-1-1"', page)
        self.assertNotIn('<details class="notes"', page)

    def test_two_notes_keep_the_list(self):
        page = report(sections=[section("S", "A [@a.py:1]. B [@b.py:2].")]).render()
        self.assertIn('<details class="notes">', page)
        self.assertNotIn('class="notes notes-1"', page)

    @staticmethod
    def badged(**default):
        cats = {"kind": {"values": {"k": {"label": "Kindly"}}},
                "st": {"values": {"ok": {"label": "Fine"}, "bad": {"label": "Broken"}}, **default}}
        ents = [{"id": f"e{i}", "title": f"E{i}", "badges": {"kind": ["k"], "st": ["ok" if i < 7 else "bad"]}} for i in range(10)]
        return report(badges=cats, entities=ents, sections=[{"title": "S", "blocks": [{"type": "tree"}]}])

    def test_dominant_value_lint_and_default(self):
        out = [x for x in self.badged().lint() if x.startswith("badge st=ok")]
        self.assertEqual(out, ['badge st=ok: 7 of 10 entities (70 %): set "default": "ok" so only the exceptions show'])
        r = self.badged(default="ok")
        self.assertEqual([x for x in r.lint() if x.startswith("badge st=ok")], [])

    def test_default_chip_is_hidden_on_rows_but_listed_in_legend(self):
        self.assertEqual(self.badged().b_tree({"type": "tree"}).count(">Fine</span>"), 8)
        tree = self.badged(default="ok").b_tree({"type": "tree"})
        self.assertEqual(tree.count(">Fine</span>"), 1)
        self.assertEqual(tree.count(">Broken</span>"), 4)
        self.assertIn('data-b="{&quot;kind&quot;: [&quot;k&quot;], &quot;st&quot;: [&quot;ok&quot;]}"', tree)

    def test_filter_chip_names_its_row_or_category(self):
        tree = self.badged().b_tree({"type": "tree"})
        self.assertIn('aria-label="filter: Broken (E8)"', tree)  # a row chip: value and row title
        self.assertIn('aria-label="filter: Kindly (E0)"', tree)  # the kind chip too
        self.assertIn('aria-label="filter: Fine (st)"', tree)  # the legend: value and category

    def test_unknown_default_fails(self):
        self.assertIn("badge st: default nope is not one of its values", fails(self.badged, default="nope"))

    def test_tab_card_omits_title_equal_to_label(self):
        r = report()
        same = r.b_tabs({"type": "tabs", "tabs": [{"entity": "alpha", "label": "Alpha", "blocks": []}]})
        self.assertNotIn('class="tt"', same)
        other = r.b_tabs({"type": "tabs", "tabs": [{"entity": "alpha", "label": "First", "blocks": []}]})
        self.assertIn('<span class="tt">Alpha</span>', other)


class NarrowScreens(unittest.TestCase):
    def test_diagrams_keep_three_quarter_scale(self):
        b = {"type": "flow", "id": "f", "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], "edges": [{"from": "a", "to": "b"}]}
        for extra in ({}, {"dir": "down"}):
            svg = re.search(r'<svg [^>]*class="dg[ "][^>]*>', report().b_flow(dict(b, **extra))).group(0)
            wd = int(re.search(r'width="(\d+)"', svg).group(1))
            self.assertIn(f"width:clamp({int(wd * .75)}px,100%,{wd}px)", svg)

    def test_zoom_button_and_scroll_hint_sit_under_the_frame(self):
        b = {"type": "flow", "id": "f", "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], "edges": [{"from": "a", "to": "b"}]}
        out = report().b_flow(b)
        self.assertIn('</svg></div><div class="fgb"><span class="dwh" hidden>Scroll sideways →</span><button type="button" class="zb"', out)
        self.assertIn('<span class="zbt">Enlarge</span></button>', out)  # a word beside ⤢ on touch screens
        self.assertNotIn('class="zb"', out[:out.index("</figcaption>")])

    def test_level_chips_and_drill_marker_are_explained_in_the_legend(self):
        top = {"type": "flow", "id": "f", "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], "edges": [{"from": "a", "to": "b"}]}
        kid = {"type": "flow", "id": "g", "parent": "f:a", "nodes": [{"id": "x", "label": "X"}, {"id": "b", "label": "B"}],
               "edges": [{"from": "x", "to": "b"}]}
        page = body(report(sections=[{"title": "S", "blocks": [top, kid]}]).render())
        self.assertIn('<span class="lvl" title="overview">L0</span>', page)
        self.assertIn('<span class="lvl" title="Level 1: detail of A">L1</span>', page)
        self.assertIn('<span><span class="lvl">L0</span>overview</span>', page)
        self.assertIn('<span><span class="lvl">L1</span>detail of a ⊞ box on L0</span>', page)
        self.assertIn("opens a detailed diagram</span>", page)

    def test_tree_filters_sit_in_an_open_details(self):
        cats = {"st": {"values": {"ok": {"label": "Fine"}}}}
        ents = [{"id": "e1", "title": "E1", "badges": {"st": ["ok"]}}]
        tree = report(badges=cats, entities=ents).b_tree({"type": "tree"})
        self.assertIn('<details class="flt" open><summary>Filters</summary><dl class="legend">', tree)
        self.assertLess(tree.index('<div class="ctl">'), tree.index("</details>"))
        self.assertLess(tree.index("</details>"), tree.index('<div class="tree"'))

    def test_titles_share_one_leading_cell_width(self):
        cats = {"sev": {"values": {"hi": {"label": "S3-4"}, "lo": {"label": "S1 cosmetic"}}}}
        ents = [{"id": "a", "title": "A", "badges": {"sev": ["hi"]}}, {"id": "b", "title": "B", "badges": {"sev": ["lo"]}},
                {"id": "c", "title": "C"}]
        tree = report(badges=cats, entities=ents).b_tree({"type": "tree"})
        # the widest row sets the width; a row without a badge still keeps the (empty) cell, so its title lines up
        self.assertIn('<div class="tree" style="--kbn:11;--kbc:1">', tree)
        self.assertEqual(tree.count('<span class="kb">'), 3)
        self.assertIn('<span class="kb"></span><span class="bd"><span class="tt">C</span>', tree)


class EdgeLabels(unittest.TestCase):
    # the sample page's L0 pipeline: "dead link" (render → abort) turns right just above render → lint
    NODES = [("json", 1, 0, "report.json", "", "store"), ("choice", 0, 0, "<stem>.choice.json", "", "store"),
             ("check", 1, 1, "Choice check", "features, questions, size", "process"),
             ("init", 1, 2, "Validate", "entities, badges, diagrams", "process"), ("tpl", 0, 1, "template.html", "", "store"),
             ("dump", 0, 2, "<stem>.data/", "", "store"), ("render", 1, 3, "Render", "sections to HTML", "process"),
             ("lint", 1, 4, "Lint", "prose, badges, stats", "process"), ("gate", 1, 5, "--strict with findings?", "", "decision"),
             ("out", 1, 6, "<out>.html", "", "store"), ("abort", 2, 4, "Abort", "exit, no page", "process")]
    EDGES = [("json", "check", "report data", "flow"), ("choice", "check", "features, questions", "opt"),
             ("check", "init", "size", "flow"), ("init", "render", "validated report", "flow"),
             ("tpl", "render", "page shell", "flow"), ("dump", "render", "rows for stats", "flow"),
             ("render", "lint", "stat lint lines", "flow"), ("lint", "gate", "lint lines", "flow"),
             ("render", "gate", "page HTML", "flow"), ("gate", "out", "no: page", "flow"), ("gate", "abort", "yes", "error"),
             ("check", "abort", "unchosen feature", "error"), ("init", "abort", "unknown ref", "error"),
             ("render", "abort", "dead link", "error")]

    def svg(self):
        b = {"type": "flow", "id": "p", "dir": "down",
             "nodes": [{"id": i, "col": c, "row": r, "label": lab, "shape": s, **({"sub": sub} if sub else {})}
                       for i, c, r, lab, sub, s in self.NODES],
             "edges": [{"from": f, "to": t, "label": lab, "kind": k} for f, t, lab, k in self.EDGES]}
        return report().b_flow(b)

    @staticmethod
    def boxes(svg):
        out = {}
        for x, y, anc, text in re.findall(r'<text class="el[^"]*"[^>]* x="([\d.-]+)" y="([\d.-]+)" text-anchor="(\w+)">([^<]+)</text>', svg):
            x, y, w = float(x), float(y), len(text) * build.CH[12]
            x0 = {"start": x, "end": x - w, "middle": x - w / 2}[anc]
            out[text] = (x0, y - 10, x0 + w, y + 3)
        return out

    def test_labels_never_overlap(self):
        bx = list(self.boxes(self.svg()).items())
        self.assertEqual(len(bx), len(self.EDGES))
        for i, (a, p) in enumerate(bx):
            for b, q in bx[i + 1:]:
                self.assertFalse(p[0] < q[2] and q[0] < p[2] and p[1] < q[3] and q[1] < p[3], f"{a} overlaps {b}")

    def test_label_keeps_clear_of_another_edges_line(self):
        svg = self.svg()
        lab = self.boxes(svg)["stat lint lines"]
        d = re.search(r'<path class="ln error"[^>]*data-f="render" data-t="abort"[^>]* d="([^"]+)"', svg).group(1)
        pts = [tuple(map(float, p.split())) for p in d[1:].split(" L")]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):  # no segment of the dead-link edge within 4 px of the label
            seg = (min(x1, x2) - 4, min(y1, y2) - 4, max(x1, x2) + 4, max(y1, y2) + 4)
            self.assertFalse(lab[0] < seg[2] and seg[0] < lab[2] and lab[1] < seg[3] and seg[1] < lab[3])


class InlinePolish(unittest.TestCase):
    def test_short_hyphenated_code_does_not_break(self):
        r = report()
        self.assertIn('<code class="nw">--strict</code>', r.inline("run `--strict` now"))
        self.assertIn("<code>fail</code>", r.inline("`fail`"))
        self.assertIn("<code>a-very-long-hyphenated-identifier-name</code>", r.inline("`a-very-long-hyphenated-identifier-name`"))

    def test_all_default_badges_leave_no_empty_group(self):
        cats = {"net": {"default": "off", "values": {"off": {"label": "Off"}, "cdn": {"label": "CDN"}}}}
        ents = [{"id": "e1", "title": "E1", "meta": ["40 lines"], "badges": {"net": ["off"]}}]
        tree = report(badges=cats, entities=ents).b_tree({"type": "tree"})
        self.assertNotIn('<span class="grp"></span>', tree)

    def test_compare_column_labels_render_code(self):
        cols = [{"label": "Abort (`fail`)", "text": "a"}, {"label": "Lint", "text": "b"}]
        out = report().b_compare({"type": "compare", "title": "T", "columns": cols, "verdict": "v"})
        self.assertIn('<p class="cmp-h">Abort (<code>fail</code>)</p>', out)


class TreeColumns(unittest.TestCase):
    @staticmethod
    def tree(metas):
        ents = [{"id": f"e{i}", "title": f"E{i}", "meta": m} for i, m in enumerate(metas)]
        return report(entities=ents).b_tree({"type": "tree"})

    def test_shared_meta_keys_become_aligned_columns_under_one_header(self):
        out = self.tree([["40 lines of code", "abort checks: 1", "only here"], ["7 lines of code", "abort checks: 12"]])
        self.assertIn('<span class="tc n">Lines of code</span><span class="tc n">Abort checks</span>', out)
        self.assertIn('<span class="tc n"><span class="tcl">Abort checks: </span>12</span>', out)
        self.assertIn('<span class="mt">only here</span>', out)  # a key one row has stays inline
        self.assertNotIn('<span class="mt">40 lines of code</span>', out)

    def test_row_without_a_column_value_keeps_its_cell(self):
        out = self.tree([["2 lines of code"], ["3 lines of code"], []])
        e2 = out[out.index('id="e-e2"'):]
        self.assertIn('<span class="tcv"><span class="tc"></span></span>', e2[:e2.index("</li>")])

    def test_shared_key_without_common_words_gets_no_header(self):
        out = self.tree([["3 files, 2 dirs"], ["5 files, 1 dirs"]])
        self.assertIn('class="tree tcs"', out)
        self.assertNotIn('class="row th"', out)

    def test_no_shared_meta_keeps_the_plain_tree(self):
        out = self.tree([["a: 1"], ["b: 2"]])
        self.assertIn('<div class="tree"><ul', out)


if __name__ == "__main__":
    unittest.main()
