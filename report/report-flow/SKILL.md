---
name: report-flow
description: "Capture how code or a pipeline works from the source (trigger, steps, stores, error paths, file:line evidence) and draw levelled DFD `flow`, `lineage` and `states` diagrams. Use for 'how does X work', 'what becomes what', 'which states'."
license: MIT
metadata:
  version: 0.1.1
  publisher: skaile-ai
---

# report-flow <question>

Answer `<question>` about how code or a pipeline works with levelled diagrams. Collect facts from the code first, draw second. Every edge carries a `path:line`.

Read [`NOTATION.md`](NOTATION.md) before you write a `flow`, `lineage` or `states` block. It holds the schema, the layout rules and the sources for the notation choice.

Reading contract: follow `skill://report-html` (citations, labels, answer-first).

## Which block

| Question | Block | Notation |
|---|---|---|
| How does pipeline or feature X work | `flow` L0, then one `flow` per stage with `parent` (L1, L2 if needed) | DFD levels, C4 zoom |
| What happens inside one stage | `flow` with `parent`, decisions and `error` edges | balanced DFD child, UML activity |
| What becomes what (types, entities) | `lineage` | dataset → job → dataset (OpenLineage) |
| Which states a record or run goes through | `states`, one per status field | UML state machine |
| Who does which step | `flow`, one column per actor | BPMN lanes |

Dependency webs with more than ~15 nodes and mermaid notations: `skill://report-diagram`. Quantities: `skill://report-charts`.

## Capture the flow

For more than two stages, give each stage to one `scout` subagent and ask for this list, every fact as `path:line`:

1. **Trigger**: npm script (`package.json`), HTTP route (`server/api/**`), UI call, hook, cron. One trigger is one entry node.
2. **Steps**: the functions in call order, with their real names.
3. **Input and output**: the type or collection that goes in and comes out of each step.
4. **Stores**: every collection, table or directory that a step reads or writes.
5. **Error paths**: condition → effect (`throw`, exit code, HTTP state, rollback, status set).
6. **Hand-off**: which later stage reads the output.

Done when every node and every edge you draw maps to one line of this list.

## Draw

- Draw an edge only if you read it in the code: a call, or a write that a later read consumes.
- Put `path:line` in `at` on every edge (every transition, every `lineage` step). The build warns about each edge without `at` as soon as one edge has it. In the `explanation` and `structure` profiles the build fails without it.
- Name a process with a verb and an object, or with the real function name. Name a store with its collection or path. Name an edge with the data it carries (`source_chapter`, `ImportDoc`), never "uses" or "calls".
- Keep source paths in `at`, not in node, store or edge labels. Exception: a path that is itself the object the diagram explains (a store that is a directory, a file that a step writes).
- Mark an error path `kind: "error"` to a node with `color: "red"` whose `sub` states the effect (`exit 1`, `409 conflict`).
- Mark a conditional or optional path `kind: "opt"`.
- Write a decision as `shape: "decision"` with a question as label and the answers as edge labels.
- Leave a gap you cannot read in the code. Say so in a `p` block.

## Levels

| Level | Block | Contains |
|---|---|---|
| L0 | `flow` without `parent` | the stages (processes with `ref` to their entity), stores shared by two or more stages, external parties. About 6-12 nodes. |
| L1 | `flow` with `parent: "<L0 id>:<node id>"` | the steps of one stage: functions, decisions, error ends, the stores only this stage uses. |
| L2 | `flow` with `parent: "<L1 id>:<node id>"` | only a step whose branching is worth its own diagram. |

- The build marks the parent node with ⊞ and links it to the child. The child caption links back ("↑ Part of").
- **Balancing (DFD)**: every parent neighbour of the node is a node in the child with the same `id` and the same edge direction. The build fails otherwise. These boundary nodes are dashed and link to that neighbour's own detail diagram.
- An external party that appears first in a child also goes into the parent (warning).
- Three or more blocks of one kind (one L1 per stage, one `states` per field) go into one `tabs` block, one tab per stage. Set the tab's `entity` to the entity that the L0 node `ref`s. Its card carries trigger, code and guard (the stage's `meta`), so the caption and the section text do not repeat them. Put the stage's `states` diagrams in the same tab.
- `lineage`: types are nodes, the step function labels the edge. A step with several inputs or outputs becomes a job node.
- `states`: one block per status field. Read the enum (`z.enum([...])`) and every write of that field. `[*]` as `from` is the initial state, as `to` the final state. A transition is `trigger [guard] / action`. A self-transition shows a write that keeps the state. The build warns about a state no path reaches from `[*]`.

## Alone

1. Collect the facts (Capture the flow). Define one entity per stage and one per source you cite, with `badges` and `meta` (`trigger`, `code`, `guard`).
2. Write `report.json` with only these blocks: the L0 `flow`, one L1 `flow` per stage in `tabs`, the `states` and `lineage` blocks the question needs, and one `p` that states the answer. Copy the shape from `example.json`.
3. Build: `python3 <skill-dir>/../report-html/build.py report.json <out>.html`. Fix every `report.json:` line.
4. Verify (list below), then `open <out>.html` and state the answer in chat.

## Under report-html

1. Do steps 1 and 2 of Alone for the selected blocks only (the L0/L1 `tabs` suite in step 2 applies only when the plan selected it); hand the blocks and entities back to the orchestrator's section plan instead of building.
2. Return only the flow, lineage and states blocks the section plan selected. Do not add an L0/L1 suite or a `tree` of stages when the plan did not select them; the standalone recipe keeps them. A single selected `flow` needs no L0 parent. Add the `tree` of the stages only when the plan selected it.
3. Size: under `technical` every edge, transition and lineage step carries `path:line` in `at` in every profile (the build fails without it), and a question that names state or data gets its `states` or `lineage` block. `small` never reaches this skill.
4. Order inside a section: the prose that explains first, then the selected `tree` (if any), then the diagrams it drives, then the `lineage`. When a `tree` is selected, set `drives: [<flow id>]` on it and `ref` on every node that is one of its entities.
5. The orchestrator builds and runs the full checks. Run the Verify list for your blocks.

## Verify

- 1280 px and 390 px: `scrollWidth == 390`, no console errors.
- Click ⊞ on a parent node: the page jumps to its detail diagram. The child's "↑ Part of" link jumps back.
- Hover a node: everything but its edges and neighbours fades. A legend edge kind hides its edges. ⤢ opens the zoom view.
- A link into a closed tab opens that tab.
- Screenshot every diagram. If lines bundle or cross boxes, set `col`/`row` (see NOTATION.md, Layout).
