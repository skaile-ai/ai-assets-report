---
name: report-asd-ste100
description: "Write or rewrite technical prose in ASD-STE100 Simplified Technical English: one statement per sentence, active voice, fixed terms. Use for report prose, 'STE', 'simplified English', 'make this unambiguous'."
metadata:
  version: 0.1.0
  publisher: mortegro
---

# report-asd-ste100

Rules for report prose, based on ASD-STE100 Issue 9 ([PDF](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf), [rule overview](https://asdste-100.com/writing-rules)). The numbers below are this skill's own numbers, not the standard's.

**Scope.** The rules apply to every `p`, `bullets`, `steps`, `summary`, `sub`, caption, badge `desc` and the chat answer of a report. Write in the language of the user. The STE rules carry over to every language. The STE dictionary does not: "approved word" becomes "one word per thing, the word from the data".

## Rules

Check each rule against one sentence or one paragraph.

1. **One statement per sentence.** A procedural sentence has at most 20 words. A descriptive sentence has at most 25 words. A paragraph has at most 6 sentences and one topic.
   - Before: "The importer reads the file, validates the rows and, if they pass, writes them, which triggers the index."
   - After: "The importer reads the file. It validates each row. It writes the valid rows. The write starts the index."
2. **Active voice, fixed tenses.** Use present tense for behaviour. Use past tense for events with a date. Start an instruction with its verb. Put the condition before the action.
   - Before: "The run is stopped if the import fails."
   - After: "If the import fails, the run stops."
3. **One term per thing.** Take the term from the data or the code. Set it in `` `code` ``. Never use a synonym later.
   - Before: "The `collection` holds rows. Each table has a key."
   - After: "The `collection` holds rows. Each `collection` has a key."
4. **Noun clusters have at most 3 words.** Break a longer cluster with prepositions.
   - Before: "the import job failure log path"
   - After: "the path of the log for failed import jobs"
5. **No -ing form as a verb. No verb-noun.** Use the plain verb.
   - Before: "The tool is running the check. Do an inspection of the file."
   - After: "The tool runs the check. Examine the file."
6. **Keep the articles. No semicolons.** A colon introduces a list. Use a list for more than two items.
   - Before: "Run starts; reads input, validates rows, writes output."
   - After: "The run does three things:" followed by a list of the three.
7. **Numbers come from the dump or the code.** Label each estimate with the word "estimate". Never type a number you did not read.
   - After: "The `ingest` step handles 1,204 rows (dump `rows.json`). The run takes about 5 minutes (estimate)."
8. **Say each fact once.** The second mention is a `[[id]]` link. A `stats` entry is a count only. The breakdown of that count lives in one section.
   - Before: "The `import` step fails on bad dates. The `import` step rejects rows with bad dates."
   - After: "The `import` step rejects rows with bad dates. See [[import]]."
9. **Warnings: command first, then the risk.**
   - After: "Do not rebuild while the import runs. The import loses rows."
10. **One `lang` per report.** Identifiers stay as in the code, wrapped in `` `code` ``. Enum values stay as in the data and are not translated.
    - Before (English report): "Der Status ist `pending`, also `wartend`."
    - After: "The status is `pending`."
11. **Define every term the reader cannot find.** A term that is absent from the dump and the code gets a definition at its first use, or an entry in a `glossary` entity list in the last section.
    - After: "The `slots_json` field holds the layout of one page (a slot is one block position)."

## Alone

1. Take the text or the markdown file the user names. Read all of it before you change a word.
2. Rewrite it in place, one sentence at a time. Apply rules 1 to 11 to each sentence, then to each paragraph.
3. Keep facts, numbers, code spans and links unchanged. Do not add facts. Where a number has no source, label it "estimate" or ask the user for the source.
4. End the chat answer with the list of rule numbers you applied, for example: "Rules applied: 1, 2, 5, 8."

Done when no sentence breaks a rule.

## Under report-html

1. Apply the rules to every text field of `report.json` before you run `build.py`.
2. Do not ask the user about it. STE prose is always on and is not an option in the `ask` call.
3. Check the stat labels and prose against rule 8 and rule 11 before the build. The lint lines of `build.py` cover orphans and prose without links. They do not check sentence length.
4. Write the chat answer with the same rules.
