# Data flows

A change that carries data across layers (a list, a detail read, a create, an update, an import) is easier to judge when the reviewer can see the shapes the data passes through, not only the diff of each shape. The `data_flows` section of `review.json` describes one operation per flow as a chain of typed stages with field-level mappings, and the page renders it on the データの流れ (Data flow) tab: one column per stage, one row per field, a line between a field and the field it becomes in the next stage, and a marker on every field that starts or stops on the way. The reviewer hovers a field and sees its whole path from storage to the screen (or back) highlighted.

Flows explain; they are not approved. They do not enter the snapshot id, so adding or correcting one does not invalidate approvals already given for the same snapshot.

## When to write one

Write a flow for every operation the change adds or reshapes whose data crosses at least two of these: table, entity, read model or command, API contract, generated client type, screen type, screen. A read flow (list, detail, export) and a write flow (create, update, delete, import) are separate flows even when they share the entity. A change that touches one shape only (a rename inside one DTO, a column width) needs no flow; say so in the group instead.

When the reviewed change is a read path, one write flow that shows where the data comes from is often worth including even though the change does not touch it (mark its stages `unchanged` and say so in the flow title), because the reviewer's question "what can be in these rows" is answered by the write side.

## Shape

```json
"data_flows": [
  {
    "slug": "list-read",
    "title": "一覧取得 GET /api/optimizer-assets",
    "direction": "read",
    "summary": ["Overall path in two sentences.", "What is dropped or born on the way."],
    "stages": [
      {
        "id": "entity", "kind": "entity", "layer": "domain", "status": "modified", "group": "list-query-handler",
        "label": "OptimizerAsset（集約ルート）",
        "path": "App/.../OptimizerAsset.cs", "excerpt": {"start": 7, "end": 45},
        "note": "How this stage is produced or consumed, in one or two sentences.",
        "fields": [
          {"name": "AssetKeyName", "type": "string", "status": "modified", "note": "[SortableColumn(IsDefault = true)] を追加"},
          {"name": "SupportedMarkets", "type": "ICollection<OptimizerAssetSupportedMarket>", "collection": true, "fields": [
            {"name": "SupportedMarket", "type": "SupportedMarket"}
          ]}
        ]
      }
    ],
    "mappings": [
      {"from": "entity.AssetKeyName", "to": "dto.Items.AssetKeyName", "kind": "copy"},
      {"from": "entity.SupportedMarkets.SupportedMarket", "to": "dto.Items.SupportedMarkets.SupportedMarket", "kind": "convert", "note": "m.SupportedMarket.Name"}
    ]
  }
]
```

| Field | Content |
|---|---|
| `slug` | Unique id matching `^[a-z0-9]+(?:-[a-z0-9]+)*$` |
| `title` | The operation as the reviewer names it: verb plus route or job name |
| `direction` | `read` (stages run from storage to the screen) or `write` (from the screen to storage). The build warns when a stage's layer moves the other way |
| `summary` | One string or paragraphs: the path in prose, then what is dropped or born on the way |
| `stages[]` | In the order the data moves. At least two |
| `stages[].id` | Unique within the flow; the first segment of every mapping reference |
| `stages[].kind` | `table`, `entity`, `dto` (read model or handler result), `response`, `request`, `command`, `client_type` (generated client), `view_model` (hand-written screen type), `screen` (what the user sees), `other` |
| `stages[].layer` | Layer key from the layer reference; drawn as a pill |
| `stages[].status` | `added`, `modified`, `deleted`, `renamed`, `unchanged` (default): the state of the stage's file in the snapshot |
| `stages[].group` | Slug of the group whose diff changes this stage; renders a 差分を開く button that switches to the diff tab and focuses that group |
| `stages[].path`, `excerpt` | Repository-relative file and `{start, end}` lines of the type definition (up to 120 lines, read from the working tree at build time). The stage shows a 定義を表示 fold with that code and an open-in-editor link |
| `stages[].note` | How the stage is produced or consumed: the spec that loads it, the mapper that fills it, the serializer that shapes it |
| `stages[].fields[]` | `{name, type?, status?, note?, collection?, fields?}`. `name` has no dots. `type` is the declared type or column type as text. `status` is per field (`added`, `modified`, `deleted`, `unchanged`). `collection: true` appends `[]` to the name. `fields` nests one level per element type |
| `mappings[]` | `{from, to, kind, note?}`. `from` and `to` are `stageId.field` or `stageId.field.subfield`, and `to` must be in the stage right after `from` |
| `mappings[].kind` | `copy` (same value, same name), `rename` (same value, other name: camelCase, a column alias), `convert` (same information, other type or representation: SmartEnum to its name, `T \| null` to `T` with a default, a date to its parts), `compute` (derived from one or more fields, or assembled: a count, a lookup by id, a display label decided by several fields) |

## Authoring rules

- Fields are the stage's own members, read from its definition: the columns of the table (from the migration or the schema), the properties of the entity, the properties of the DTO, the JSON members, the generated interface members, the hand-written type members, the visible columns or inputs of the screen. Do not invent a member to make a line continuous; a value with no member at a stage is born or stops there.
- Every line is a fact you verified in code: a mapper line, a serializer convention, a `HasConversion`, a `?? default`. Write the expression or the rule in the mapping `note` when it is not obvious from the kinds.
- A field with no incoming line (except in the first stage) gets a `+` marker: it is born at that stage. A field with no outgoing line (except in the last stage) gets a `×` marker: it stops there. Both are computed; explain the notable ones in the flow `summary` or the field `note` (a count computed by the handler, a shadow tenant column, an audit column set by an interceptor, an entity property the read model does not expose). A field whose descendants are mapped counts as mapped.
- Nest a collection's element members under the collection field and map member to member. Map the collection field itself with `convert` when the element type changes.
- Keep a stage's field list complete for the members that carry data; omit what the flow never loads (a navigation the spec does not include, a child table the query does not join) and say so in the stage `note`. Audit columns of child tables may be omitted with a note.
- Prefer many small `note`s on mappings over prose in `summary`; the reviewer reads a note next to the line it explains.
- Language follows `locale` like every other prose field; identifiers, types, and expressions stay as they are.

## Reading the tab

The tab lists the flows as buttons when there is more than one. Under the title and summary, the stages sit left to right; the board scrolls sideways when the flow is wider than the pane. Each stage card carries its kind, layer, and status pills, the label, the path with an open-in-editor link, the note, the 差分を開く button when it has a group, the field rows, and the 定義を表示 fold. Hovering or focusing a field highlights every line and field on its path in both directions and lists the hops under the board; a click keeps the selection, Escape or 選択を解除 clears it. The legend explains the four line kinds and the two markers.
