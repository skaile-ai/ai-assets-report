# Reader notes and decisions

The reader talks back to the agent from the page: **comments** on any text and answers to **`decision`** blocks; the agent talks back with its answers and with new questions it adds to the open page (`ask`). All of it travels through the agent channel. Without it the page has neither: on `file://`, without the URL's token, or once `report-serve` stops, the Comments button, the pencils and the Comment button are gone and every decision form is disabled with the line "Answering works only when the agent opened this report through report-serve." The page holds a pushed event stream and also asks `GET /__annotations/access` every 10 s; it switches both ways, at once when the stream drops.

## The channel

`report-serve.ts` (next to `build.py`, run with Bun) serves the report's folder on `127.0.0.1` and mounts the annotation inbox of `@skaile/forge-annotation-inbox` on `/__annotations`. The inbox lives in `<project>/.data/annotations`, the store that `annotations_list` / `annotations_resolve` read (omp extension, or the `annotation-inbox-mcp` server in Claude Code). The server accepts inbox requests only with the bearer token it printed in the URL (`#k=<token>`; the page moves it to `sessionStorage` and out of the address bar), only with its own `Host` (DNS rebinding) and only from its own `Origin`. The port is stable per project and folder (47000-47999).

Comments and decision answers are stored **on the report**, in `<stem>.comments.json` next to `<stem>.html`. The page reads and changes it through `/__comments?page=<path>` (same token, Host and Origin checks); the server never serves the file itself. Every reader of the report sees the same comments, and all of them publish into one inbox session named after the report, so the agent's answer shows for everyone. The file travels with the report and can be committed; a new version (`-v<N+1>`) starts with no comments, and the old version keeps its own.

```json
{"report": "<stem>.html",
 "comments": [{"id", "src": "sections/<i>/blocks/<j>", "sec", "quote", "before", "after", "anchor", "comment", "at", "edited"?}],
 "decisions": {"<decision id>": {"opt", "text", "at"}},
 "questions": [{"id", "question", "options": [{"id", "label", "text"?}], "recommended"?, "other", "at"}]}
```

The file holds what readers said and the questions the agent added (`ask`); whether the agent answered lives in the inbox (`annotations_list` with `status: "all"`).

Delivery is pushed both ways. An open page holds `GET /__events` (same token): the server watches the report folder and the inbox store, and every change (a reader saved, `ask`, a send, `annotations_resolve` from any process) reaches every open page as one event, so it reloads its state within about a second; a 10 s tick stays as the fallback. `wait` watches the inbox store the same way and exits within about half a second of a send.

```sh
bun -i <skill-dir>/report-serve.ts <out>.html [--root <project>] [--port <n>]   # prints report: http://127.0.0.1:<port>/<file>#k=<token>
bun -i <skill-dir>/report-serve.ts wait [--root <project>]                      # blocks until the reader sends, prints the items, exits
bun -i <skill-dir>/report-serve.ts ask <out>.html <question.json | ->            # adds a decision to the open page (needs the running server)
```

`--root` defaults to the working directory: run both from the project root the agent session works in. `-i` lets Bun fetch the pinned inbox package when no `node_modules` has it.

## Reader side

- **Comments.** Select text and press **Comment**, or press the pencil next to a section title (the lede has no pencil). The **Comments** button (German **Kommentare**; not "Notes", which names the citation list of a section) opens the panel: comments in page order, each with Edit and Delete and its state (`not sent yet`, `sent · waiting for the agent`, or the agent's answer); a click jumps to the text. **Send to agent** publishes them; **Clear** deletes them. On a phone the button is a 44 px circle that hides while the reader scrolls down; the page keeps 72 px free at its end.
- **Decisions.** Pick an option, optionally write a comment, press **Send answer**. A changed answer says "Changed: send again". The agent's resolution shows under the form. Questions the agent asks while the page is open appear at the end of the decisions section (a "Questions from the agent" section after the summary when the report has none) and answer the same way.
- Every save, edit and delete is written to `<stem>.comments.json` at once; every send publishes the whole report state, meaning all comments and every answered decision. A comment or answer reads `not sent yet` until the inbox holds that exact text: an edited comment or a changed answer becomes a new inbox item, and one a reader deletes leaves the inbox while still open. Open pages reload the stored state on every pushed change, so a second reader's comment shows up without a reload. Every section and block carries `data-src`, its JSON pointer into `report.json`, so each item names the node to edit.

## Environments

`report-serve.ts` detects where it runs and prints `env:` on start; `--env local|platform|container` (or `REPORT_SERVE_ENV`) overrides it.

| env | detected by | what happens |
|---|---|---|
| `local` | none of the below | as described above |
| `platform` (skaile workspace session or preview container) | `SKAILE_PREVIEW_BASE`, or `SKAILE_SESSION_ID` together with `/.dockerenv`, `/run/.containerenv` or `KUBERNETES_SERVICE_HOST` | exits with code 2 and no URL: the Preview proxy cannot reach `127.0.0.1`, drops the `#k=` fragment and the `Authorization` header and rewrites `Host`/`Origin`, so the page would never see the channel. Show the report as a static preview; it keeps comments and decision forms disabled. Ask each decision with `platform.request_decision` (its outcome arrives as a new turn); comments go through chat |
| `container` (other Docker, devcontainer, Codespaces) | a container marker, `REMOTE_CONTAINERS` or `CODESPACES` | serves, with a warning: it works only when the editor forwards the same port to `localhost` on the host (VS Code devcontainers); any other forward fails the Host check and the page stays disabled |

## Agent side

After building (workflow step 10):

1. Run `report-serve.ts <out>.html` from the project root. One server serves a whole folder: every report in it, all versions, one inbox. If a server for that folder already runs, the call prints the new report's URL on it (`served by the running report-serve (pid …)`) and exits. Otherwise it starts one; run it as a named background service (omp: `bash` with `name: "report-serve"` and `ready.log: "inbox:"`; Claude Code: a background Bash). `open` the printed `report:` URL, not the file. Port and token persist in `.data/annotations/.report-serve.json` (mode 600), so a restarted server keeps both and open tabs reconnect.
2. Start `report-serve.ts wait` as a background job with no deadline (omp: `async: true`, `timeout: 0`; Claude Code: background Bash or the Monitor tool). Its exit wakes the session with the new items as Markdown. It records what it printed in `.data/annotations/.watch-seen`, shared with omp's `/annotations watch`, so no item arrives twice.
3. Per item:
   - `Path` is `<report.json>#/<pointer>`: `/sections/<i>/blocks/<j>[/tabs/<k>/blocks/<m>]`; `/sections/<i>` means the whole section; a trailing `entity <id>` names the entity in top-level `entities`. `Context` holds the section, the marked words and the sentences around them.
   - A comment: apply it under `skill://report-prose`. A note that needs data the dump lacks re-runs the dump.
   - A decision (`Decision <id>: <label> [<option id>]`, with the reader's comment on the next line): act on the choice; `Context` lists the question and all options. A question asked with `ask` has the `Path` `<stem>.comments.json#/questions (id <id>, asked live)`.
   - Everything readers left on this version, including what was never sent: `<stem>.comments.json` (format above).
4. Write the next version `<topic>-<date>-v<N+1>` (workflow step 10: earlier versions stay untouched). Its choice file copies the previous one, including its `mode`. Build with step 8, verify with step 9. Comments stay on the version they were made on.
5. Answer every item with `annotations_resolve` (`implemented`, or `rejected` with the reason), in the reader's language. The page shows the answer under the comment or decision within a second.
6. **Ask back** instead of writing a new version when you need a choice from the reader: write one decision object (the `decision` block's fields: `id`, `question`, 2-6 `options` with `id` (lowercase letters, digits, dashes) and `label`, optional `text`, `recommended`, `other`) or an array of them to a file and run `report-serve.ts ask <out>.html <file>` (or pipe it to `-`). Every open page of that report shows the form within a second; its answer arrives through `wait` like any decision. The same `id` again replaces the question (an answer whose option is gone is dropped); an `id` the report's own decision blocks use is refused. A declined answer plus a follow-up question is the usual back-and-forth.
7. Restart `wait` while the reader keeps working. A new version in the same folder needs no new server: run step 1 again for its file and open the URL it prints. Stop the service when the user is done.

## Verify

Add to workflow step 9:

- Opened as `file://`: no Comments button, no pencils; decision forms disabled with the report-serve line visible.
- Opened through the printed URL: the address bar loses `#k=…`; the Comments button appears and decision forms are enabled.
- Select words → `Comment` → save → the button counts 1, the words are highlighted, `<stem>.comments.json` holds the comment, the panel says `not sent yet`; **Send to agent** → `sent · waiting for the agent`, and `report-serve.ts wait` exits with the item.
- A second tab on the same URL shows the same comments and the stored decision answer; an edit in one tab shows in the other within a second.
- A decision answer → **Send answer** → `wait` prints `Decision <id>: …`; after `annotations_resolve` the answer shows under the form within a second.
- `report-serve.ts ask` with a new question: the form appears at the end of the decisions section without a reload, and answers like the others.
- Stopping the server turns the page back to the `file://` state within a second.
- At 390 px the open panel keeps `scrollWidth == 390`.
