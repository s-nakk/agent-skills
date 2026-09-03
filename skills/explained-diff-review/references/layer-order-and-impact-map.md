# Layer order and impact map

Reviewers understand a change the way a request travels: from the screen the user touches, through the API boundary and the application logic, down to storage and external systems. Present groups, files, hunks, and the impact map in that order so the reader always knows what calls what and how far the change reaches.

## Layer taxonomy

The taxonomy is generic. Map the project's own structure onto it; do not invent project-specific layers.

| Key | Rank | Label (ja / en) | Typical members |
|---|---|---|---|
| `presentation` | 10 | 画面 / UI | Pages, routes, screens, components, view models, templates, styles that change behavior |
| `client_data` | 15 | 画面のデータ取得 / Client data access | API clients, hooks, stores, query definitions, generated client types, client-side validation schemas |
| `api` | 20 | API 境界 / API boundary | Endpoints, controllers, route handlers, request and response DTOs, OpenAPI, GraphQL resolvers, authorization at the boundary |
| `application` | 30 | アプリケーション / Application | Services, use cases, command and query handlers, orchestration, transactions, mappers between boundary and domain |
| `domain` | 40 | ドメイン / Domain | Entities, aggregates, value objects, domain rules, specifications, domain events |
| `persistence` | 50 | 永続化 / Persistence | Repositories, data access objects, ORM mappings, migrations, SQL, stored procedures, indexes |
| `infrastructure` | 60 | 基盤・外部連携 / Infrastructure | External service clients, messaging, email, storage, dependency registration, middleware, background jobs |
| `config` | 70 | 設定・ビルド / Configuration and build | Settings files, environment files, CI and build definitions, package manifests, containers |
| `tests` | 80 | テスト / Tests | Unit, integration, and end-to-end tests, fixtures, test helpers |
| `docs` | 90 | ドキュメント / Documentation | Design documents, ADRs, READMEs, changelogs, images used by documents |
| `other` | 100 | その他 / Other | Anything that does not fit; use sparingly and explain in the group |

Assignment rules:

- Assign by the role the file plays in this change, not by its folder name alone. A shared helper edited so that a repository can filter rows belongs to `persistence` for this review.
- Every changed file gets exactly one layer. When the role is unclear, choose `other` and explain in the group text; never omit a file.
- Generated code follows the layer of its consumer. A generated API client is `client_data`; a generated migration is `persistence`.
- Tests are `tests` even when they sit next to production code. Documentation and images used by documentation are `docs`. Build, CI, and settings are `config`.
- Use `order` on a file when call order inside one layer matters, for example page before component, or repository before the migration that supports it. Without `order`, files in the same layer sort by path.

## Ordering rules

The build script enforces these; author the review knowing they apply.

- Groups are ordered by the smallest layer rank among their hunks. Ties keep the authored order.
- Hunks inside a group are ordered by layer rank, then `order`, then path, then hunk position.
- The file list inside a group follows the same order.
- Lanes in the impact map follow layer rank from top to bottom.

If the natural reading order of a change differs from this order, adjust the grouping rather than the order: split a group that mixes a screen change with a storage change into two groups, or merge two groups that only make sense together. The top-down order is the story.

## Impact map

The map shows the edit scope and the important connections at a glance: the path a request follows, where the change touches that path, and what unchanged code or data the change reaches.

### Nodes

- Include every changed file or symbol that carries behavior. Use the symbol name when one symbol is the point of the change, otherwise the file name.
- Keep the path continuous. From each entry point (screen, job, endpoint) down to the sink (table, external system), every hop on the way must be a node, including unchanged pass-through code such as an endpoint that forwards a new parameter or a service that calls the changed repository. A reader following the map top-down must never meet a gap where the call chain jumps a layer. The build warns when an edge skips intermediate layers.
- Give each unchanged pass-through node an `excerpt`: `{"path": "<repo-relative file>", "start": <line>, "end": <line>}` covering the method or block that carries the call (read from the working tree at build time; up to 120 lines). The reader can then open that code from the map without leaving the review. Also include unchanged nodes that receive different behavior, tables and columns the change reads or alters, external systems, and screens that render the result; give them an excerpt when code exists for them.
- Status values: `modified`, `added`, `deleted`, `renamed`, `unchanged`. Unchanged nodes render dashed and gray; unchanged nodes with an excerpt are clickable.
- Every changed node carries the `group` slug of the group that explains it. The node shows an approval marker for that group, and selecting the node focuses the group below the map. Selecting an unchanged node with an excerpt shows that code below the map instead.
- `note` is at most five words and states what changed at that node, for example "アーカイブ除外" or "Status 列が増える".
- Budget: at most 16 nodes and 24 edges. When the change is larger, keep the main path from entry point to storage plus the riskiest neighbors, and fold the rest into one node per layer with a note such as "他 3 ファイル". List the folded files in the group text.

### Edges

- Direction follows the call or data flow from upstream to downstream: page → hook → endpoint → service → repository → table. Tests point at what they verify. Migrations point at the table they alter.
- `kind` is a short verb or protocol: `calls`, `reads`, `writes`, `alters`, `renders`, `verifies`, `emits`, `HTTP GET /orders`. It appears as a tooltip, not as a label on the line.
- Every edge must be supported by the diff or by unchanged code you actually read. Do not infer relations from names.
- Do not draw edges that are implied transitively, or framework plumbing such as dependency injection wiring unless the change is about that wiring. Edges between two unchanged nodes are expected when they lie on the path between changed nodes; do not draw them elsewhere.

### Layout

The widget lays the map out automatically: one lane per layer, nodes packed left to right and wrapped into rows, downward edges drawn as curves, and edges that would cross a node routed through the row gaps and the right gutter. You never compute coordinates. If the rendered map is crowded, reduce nodes rather than accept overlaps.
