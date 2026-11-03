---
name: report-prose
description: "Write report prose people read front to back: an argued answer (claim, reason, consequence), the reader's words before code names, few links, lists only after a lead sentence, examples and contrasts where they explain. Use for report prose, 'make this readable', 'too technical', 'rewrite for people'."
license: MIT
metadata:
  version: 0.1.0
  publisher: skaile-ai
---

# report-prose

Rules for report prose that a person reads front to back. The page argues its answer; tables, trees and diagrams support it.

**Scope.** The rules apply to every `p`, `bullets`, `steps`, `callout`, `argument`, `example`, `compare`, `summary`, `sub`, caption, badge `desc` and the chat answer of a report. Write in the language of the user. The rules carry over to every language.

## Rules

Check each rule against one sentence or one paragraph.

1. **Argue the answer.** A section opens with a claim, its main reason and what follows for the reader (`because`, `so`; de `weil`, `deshalb`). Example: "Ordering ready-made DTF transfers fits best, because the club prints only ten times a year. So it needs no machine of its own."
   - Before: "There are three options: screen printing, DTF transfers and an own press."
   - After: "Ordering ready-made DTF transfers fits best, because the club prints only ten times a year. So it needs no machine of its own."
   - Before (de): "Es gibt drei Optionen: Siebdruck, DTF-Transfers und eine eigene Presse."
   - After (de): "Fertige DTF-Transfers passen am besten, weil der Verein nur zehnmal im Jahr druckt. Deshalb braucht er keine eigene Maschine."
2. **Sentences carry one idea and its reason.** Aim for 20 words or fewer; the limit is 30. Use one subordinate clause at most. A paragraph has 3–6 sentences and one topic, and its first sentence names the topic. Connectives are wanted: because, so, therefore, but, although, if … then.
   - Before: "The importer reads the file, validates the rows and, if they pass, writes them, which triggers the index, so that search finds them."
   - After: "The importer checks each row before it writes. It skips bad rows, because one bad row breaks the search index. The write then updates the index."
3. **Lists supplement, never replace, the argument.** A `bullets`/`steps` block follows a `p` that says what the list shows and why it matters. Use a list only for parallel items the reader scans, compares or follows: steps, options, criteria, open items. Keep it to 3–7 items, each a full phrase. Reasons, cause chains and recommendations go into sentences or into an `argument`. (Lint: `lists:`.)
   - Before: a section that opens with `bullets`: "cheap per shirt", "no machine", "ten runs a year".
   - After: a `p` "DTF transfers fit best, because the club prints rarely and has no machine. The list below gives the cost per shirt of each option:", then a `bullets` block with one full phrase per option.
4. **The reader's word first.** Name a thing with the word the reader uses. Give the code or data name once, at the first mention, in parentheses as `code`, and only if the reader needs it to find the thing ("the import check (`validate_rows`)"). After that, use the plain word. Translate enum values and give the original value once in parentheses. Under size `technical`, an identifier may stay the subject, in `code`.
   - Before: "`validate_rows` drops rows with `status` `pending_review`. `validate_rows` logs each drop."
   - After: "The import check (`validate_rows`) drops rows that still wait for review (`pending_review`). The import check logs each drop."
   - Before (de): "`validate_rows` verwirft Zeilen mit `status` `pending_review`."
   - After (de): "Die Importprüfung (`validate_rows`) verwirft Zeilen, die noch auf Freigabe warten (`pending_review`)."
5. **One term per thing.** Keep the word from rule 4 throughout. No synonyms.
   - Before: "The import check rejects bad dates. The validator also flags duplicates."
   - After: "The import check rejects bad dates. The import check also flags duplicates."
6. **Link sparingly.** Link a thing at most once per section, at its first mention, and only when its detail (a tree row, table row or tab) adds something the sentence does not say. Use at most 3 links per paragraph or list. A repeated mention is plain text. Never write link lists ("[[a]], [[b]], [[c]] and [[d]]"): name the group and point to the table or tab instead. (Lint: `links:`.)
   - Before: "The import uses [[reader]], [[check]], [[writer]] and [[index]]. [[check]] rejects bad dates."
   - After: "The import runs in four steps, listed in the table below. The [[check|import check]] rejects bad dates."
7. **Evidence as notes.** Put at most one `[@…]` per sentence, at the end, before the full stop, and only for claims a reader may want to check. Outside `technical` it renders as a numbered note with a collapsed "Notes/Belege" list at the end of the section. Under `technical` it renders as an inline grey bracket. Never put a path in running text.
   - Before: "The check in `src/import.py` rejects bad dates [@src/import.py:88] [@tests/test_import.py:12]."
   - After: "The import check rejects bad dates [@src/import.py:88]."
8. **Numbers for reading.** Every number comes from the dump or the code. Label estimates "estimate". Round when exactness does not matter ("about 1,200"). Use at most 3 numbers per sentence. Give a comparison point ("twice as many as in May").
   - Before: "The import handled 1,204 rows, 37 failed, 12 were duplicates and 3 timed out in 312 seconds."
   - After: "The import handled about 1,200 rows. 37 of them failed, twice as many as in May. A full rebuild takes about an hour (estimate)."
9. **Explain before you show.** A `p` precedes every table, tree, chart and diagram and says what to look at and what it shows. After a complex block, one sentence leads to the conclusion.
   - Before: a heading, then the table of failed rows.
   - After: "The table lists each failed row with its reason. Look at the date column: it holds most failures." Then the table, then "So the date format causes most of the losses."
10. **Make the abstract concrete.** When a section explains a mechanism or a rule, add an `example` or one concrete case in a sentence.
    - Before: "The import check rejects dates that do not exist."
    - After: "The import check rejects dates that do not exist. For example, `2026-13-01` fails, because there is no month 13."
11. **Contrast for decisions.** Option A vs B, today vs proposed, assumption vs finding: use `compare`, ending in a verdict.
    - Before: "Today the club orders transfers. A press would cost more at first but less per shirt, and it needs space."
    - After: a `compare` block with the columns "Order transfers" and "Own press", each with its cost and effort, and the verdict "Keep ordering transfers, because ten runs a year do not pay for a press."
12. **Define what the reader cannot know** at first use, in the same or the next sentence. No glossary block.
    - Before: "The page has three slots."
    - After: "The page has three slots. A slot is one position for a block."
13. **Active voice, present tense** for behaviour. Put the condition before the action. In a warning, the command comes first, then the risk.
    - Before: "The run is stopped by the scheduler if the import fails."
    - After: "If the import fails, the scheduler stops the run."
    - Before (warning): "Rows get lost if a rebuild happens during the import."
    - After (warning): "Do not rebuild while the import runs. The import loses rows."
14. **One `lang` per report. Say each fact once.** Refer back in words ("the import check above"), not with a link.
    - Before (English report): "The status is pending, also called *wartend*. As said in [[check]], the [[check]] rejects these rows."
    - After: "The status is pending. The import check above rejects these rows."

## Choose the element

| The reader needs | Block |
|---|---|
| the answer and why | `p`: claim, reason, consequence |
| to accept an important or contested conclusion | `argument` |
| to understand a mechanism or rule | `example` |
| to decide between two options, or see before vs after | `compare` |
| to remember one answer, act, or avoid harm | `callout` (`answer`, `action`, `safety`, `note`) |
| to scan parallel items | `bullets` after a lead `p` |
| to follow an order | `steps` after a lead `p` |
| to look up many rows | `table`/`data` (`skill://report-table`) after a lead `p` |

Each block's schema is in `skill://report-html`, section "report.json".

## Alone

1. Read the text in full.
2. Rewrite it in place, sentence by sentence, then paragraph by paragraph.
3. Keep facts, numbers and sources. Add no facts.
4. End the chat with "Rules applied: …".

## Under report-html

1. Always on; never asked about.
2. Before the build, check each section's opening for claim + reason, check that every list has a lead `p`, check links per rule 6, check code names per rule 4.
3. The build lints cover link density, lists without a lead, list-heavy sections and opening-sentence budgets. They do not judge the argument. Reread every opening paragraph and ask: does it say why?
4. Write the chat answer by the same rules.
