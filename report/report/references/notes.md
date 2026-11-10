# Reader notes

Every page lets the reader comment on it. Select text and press **Comment**, or press the pencil next to a section title to comment on the whole section (the lede has no pencil). The **Comments** button (German **Kommentare**; not "Notes", which names the citation list of a section) opens the panel: notes in page order, each with Edit and Delete; a click on a note jumps to its text. On a phone the button is a 44 px circle that hides while the reader scrolls down; the page keeps 72 px free at its end so the button and the location pill never cover the last lines. **Copy for agent** copies all notes as one Markdown block starting `# Notes on report`; **Clear** deletes them. Notes live in the browser per file (`localStorage`); nothing is uploaded. Every section and block carries `data-src`, its JSON pointer into `report.json`, so each note names the node to edit.

## Revising from pasted notes

When the user pastes a block starting `# Notes on report`:

1. Open the `Source` file next to the HTML named under `File`.
2. Per note, resolve `Where`: a JSON pointer `/sections/<i>/blocks/<j>[/tabs/<k>/blocks/<m>]`; `/sections/<i>` means the whole section; `entity <id>` names the entity in top-level `entities`. `Marked` and `Context` locate the words inside the node.
3. Apply the comment under `skill://report-prose`. A note that needs data the dump lacks re-runs the dump.
4. Write the next version `<topic>-<date>-v<N+1>` (workflow step 10: earlier versions stay untouched). Its choice file copies the previous one, including its `mode`; a note that asks for a new question or ability adds it there, and the chat names the addition. Build with step 8, verify with step 9.
5. Answer in chat one line per note: its number, what changed, or why it was not done. Tell the user to press **Clear** on the old page.

## Verify

Add to workflow step 9:

- Select words in a paragraph → `Comment` appears → save → the Comments button counts 1 and the words are highlighted.
- A reload keeps the note.
- The copied text's `Where` pointer resolves in `report.json`.
- `Clear` empties the list.
- At 390 px the open panel keeps `scrollWidth == 390`.
