# Profile web-research

A report researched from the web for patients, the public or professionals: an answer with safety and action callouts, licensed images, curated resources and a linked bibliography. The skeleton is in `skill://report`, workflow step 2.

## Blocks and keys

- `media` (`items: [{src, alt, caption, credit, href?, license?, license_url?}]`): `src` is a local file next to the output HTML or the `report.json`, rewritten relative to the output; a missing file fails. `alt`, `caption`, `credit` are required; `href` links the credit to the image page, `license_url` needs `license`. One or two columns on a wide page, one on a phone.
- `resources` (`items: [{title, url, description, audience?, kind?}]`, optional `label`): every `url` is an external http(s) link and opens as a compact card.
- `sources`: ids are unique (letters, digits, `.`, `_`, `-`), `title` and an http(s) `url` are required, `publisher`, `year`, `kind`, `read` (date read) and `note` are optional and shown under the linked title. The bibliography renders after the last authored section with `id="sources"` and is listed in the table of contents.
- The page always gets the table of contents and the skip link. The report-wide find box is shared with every profile (report-json.md, Page order and sections).

## Sources

With a top-level `sources` list, an inline `[@S1]` whose text is exactly a source id renders in every size as a link to the bibliography record `#src-S1`, shown as a grey bracket, and adds no note. Any other `[@…]` text renders as `report-json.md` describes: a numbered note outside `technical`, an inline grey bracket under `technical`. A citation whose text looks like a source id (letters, then digits: `S1`, `R12`) but is in no `sources` record fails the build (in profile `web-research` also when `sources` is empty). Cite the record that backs the claim; do not paste URLs into prose.

## Reader depth

Three cumulative depths: `general` sees `general` and unmarked blocks; `informed` adds `informed`; `professional` adds `professional`. A block or section with `reader: "<id>"` shows from that depth on; no `reader` means every depth. Put the short, safe, practical statement at `general`, the reasons at `informed`, the evidence detail at `professional`.

The build refuses `reader` on the first section, on the answer paragraph (the first `p` of the first section) and on anything that holds a `safety` or `action` callout; the bibliography is never hidden. A note cited only from deeper blocks hides with them; the notes list keeps the marker numbers and counts only the notes the depth shows. Print shows every depth.

Top-level `readers` holds the segmented-control labels (`label`, `description` as a string or `{de, en}`); all three ids are required, `default` is `informed` unless set.

## Verify

Add to workflow step 9:

- At 390 px no horizontal scroll with all three reader depths.
- Each depth button changes what shows: `informed` is the default, `general` hides `informed` and `professional` blocks, `professional` shows all.
- Safety and action callouts, the first answer paragraph and the sources stay visible at every depth.
- Every `[@S1]` link jumps to its `#src-S1` record.
- The find box shows a live count, and `Suche zurücksetzen`/reset restores the page.
- A `table` shows labelled cards under 640 px.
- Every `media` image loads and shows its credit and licence.
- A vertical flow scrolls inside its frame at ≥75 % scale; the page keeps `scrollWidth == 390`.
