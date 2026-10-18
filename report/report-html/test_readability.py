"""Behavioural tests for readable source citations: `[@source text]` in prose and structured `at` values.

Run from the reporting source root:  python3 -m unittest discover -s report-html -p 'test_readability.py'
The tests assert on rendered HTML fragments, not on the renderer's source text.
"""
import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location("report_build", Path(__file__).with_name("build.py"))
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)


def src(text):
    """The markup of one citation, written out independently of the renderer's helper."""
    return f'<span class="src">[{text}]</span>'


def report(**extra):
    data = {"title": "T", "lang": "en", "entities": [{"id": "alpha", "title": "Alpha", "label": "A"}], "sections": []}
    data.update(extra)
    return build.Report(data)


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
        r = report(sections=[{"title": "S", "blocks": [
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

    def test_missing_at_validation_unchanged(self):
        with self.assertRaises(SystemExit) as cm:
            report(profile="explanation", sections=[{"title": "S", "blocks": [
                {"type": "flow", "id": "f", "nodes": [{"id": "a"}, {"id": "b"}], "edges": [{"from": "a", "to": "b"}]}]}])
        self.assertIn("without at", str(cm.exception))


class HeaderMeta(unittest.TestCase):
    def test_header_meta_renders_citations(self):
        page = report(meta=["Source: [@a/b.ts:3]", "Date: 2026-10-18"]).render()
        self.assertIn(f"Source: {src('a/b.ts:3')}<br>Date: 2026-10-18", page)

    def test_header_meta_escapes_html(self):
        page = report(meta=["<script>x</script>"]).render()
        self.assertNotIn("<script>x</script>", page)
        self.assertIn("&lt;script&gt;x&lt;/script&gt;", page)


if __name__ == "__main__":
    unittest.main()
