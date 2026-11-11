# Reader notes and decisions

The reader talks back to the agent from the page: **comments** on any text and answers to **`decision`** blocks. Both travel through the agent channel. Without it the page has neither: on `file://`, without the URL's token, or once `report-serve` stops, the Comments button, the pencils and the Comment button are gone and every decision form is disabled with the line "Answering works only when the agent opened this report through report-serve." The page asks `GET /__annotations/access` every 10 s and switches both ways.

## The channel

`report-serve.ts` (next to `build.py`, run with Bun) serves the report's folder on `127.0.0.1` and mounts the annotation inbox of `@skaile/forge-annotation-inbox` on `/__annotations`. The inbox lives in `<project>/.data/annotations`, the store that `annotations_list` / `annotations_resolve` read (omp extension, or the `annotation-inbox-mcp` server in Claude Code). The server accepts inbox requests only with the bearer token it printed in the URL (`#k=<token>`; the page moves it to `sessionStorage` and out of the address bar), only with its own `Host` (DNS rebinding) and only from its own `Origin`. The port is stable per project and folder (47000-47999), so the page's `localStorage` survives a restart.

```sh
bun -i <skill-dir>/report-serve.ts <out>.html [--root <project>] [--port <n>]   # prints report: http://127.0.0.1:<port>/<file>#k=<token>
bun -i <skill-dir>/report-serve.ts wait [--root <project>]                      # blocks until the reader sends, prints the items, exits
```

`--root` defaults to the working directory: run both from the project root the agent session works in. `-i` lets Bun fetch the pinned inbox package when no `node_modules` has it.

## Reader side

- **Comments.** Select text and press **Comment**, or press the pencil next to a section title (the lede has no pencil). The **Comments** button (German **Kommentare**; not "Notes", which names the citation list of a section) opens the panel: comments in page order, each with Edit and Delete and its state (`not sent yet`, `sent · waiting for the agent`, or the agent's answer); a click jumps to the text. **Send to agent** publishes them; **Clear** deletes them. On a phone the button is a 44 px circle that hides while the reader scrolls down; the page keeps 72 px free at its end.
- **Decisions.** Pick an option, optionally write a comment, press **Send answer**. A changed answer says "Changed: send again". The agent's resolution shows under the form.
- Every send publishes the whole page session: all comments and every sent decision. An edited comment or a changed answer becomes a new inbox item; one the reader deletes leaves the inbox while still open. Comments and answers stay in the browser per file (`localStorage`). Every section and block carries `data-src`, its JSON pointer into `report.json`, so each item names the node to edit.

## Agent side

After building (workflow step 10):

1. Start the server as a named background service from the project root (omp: `bash` with `name: "report-<stem>"` and `ready.log: "inbox:"`; Claude Code: a background Bash). `open` the printed `report:` URL, not the file.
2. Start `report-serve.ts wait` as a background job with no deadline (omp: `async: true`, `timeout: 0`; Claude Code: background Bash or the Monitor tool). Its exit wakes the session with the new items as Markdown. It records what it printed in `.data/annotations/.watch-seen`, shared with omp's `/annotations watch`, so no item arrives twice.
3. Per item:
   - `Path` is `<report.json>#/<pointer>`: `/sections/<i>/blocks/<j>[/tabs/<k>/blocks/<m>]`; `/sections/<i>` means the whole section; a trailing `entity <id>` names the entity in top-level `entities`. `Context` holds the section, the marked words and the sentences around them.
   - A comment: apply it under `skill://report-prose`. A note that needs data the dump lacks re-runs the dump.
   - A decision (`Decision <id>: <label> [<option id>]`, with the reader's comment on the next line): act on the choice; `Context` lists the question and all options.
4. Write the next version `<topic>-<date>-v<N+1>` (workflow step 10: earlier versions stay untouched). Its choice file copies the previous one, including its `mode`. Build with step 8, verify with step 9.
5. Answer every item with `annotations_resolve` (`implemented`, or `rejected` with the reason), in the reader's language. The page shows the answer under the comment or decision within 10 s.
6. Restart `wait` while the reader keeps working. A new version gets its own server (stop the old service first, or serve the folder and open the new file name). Stop the services when the user is done.

## Verify

Add to workflow step 9:

- Opened as `file://`: no Comments button, no pencils; decision forms disabled with the report-serve line visible.
- Opened through the printed URL: the address bar loses `#k=…`; the Comments button appears and decision forms are enabled.
- Select words → `Comment` → save → the button counts 1, the words are highlighted, the panel says `not sent yet`; **Send to agent** → `sent · waiting for the agent`, and `report-serve.ts wait` exits with the item.
- A decision answer → **Send answer** → `wait` prints `Decision <id>: …`; after `annotations_resolve` the answer shows under the form.
- Stopping the server turns the page back to the `file://` state within 10 s.
- At 390 px the open panel keeps `scrollWidth == 390`.
