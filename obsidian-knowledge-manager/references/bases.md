# Obsidian Bases reference

## Data model

A Base is a YAML document stored as `.base`. It selects and presents Markdown files. Each record remains a normal note; its frontmatter provides typed properties and its body holds long-form content.

Typical Base structure:

```yaml
filters:
  and:
    - file.inFolder("application/research")
    - record_type == "research-contact"
formulas:
  next_label: 'if(next_action, next_action, "—")'
properties:
  file.name:
    displayName: Record
  note.status:
    displayName: Status
views:
  - type: table
    name: All
    order:
      - file.name
      - note.status
  - type: table
    name: Pending
    filters:
      and:
        - status != "done"
```

Common view types are `table`, `list`, and `cards`. Other view types may require a newer Obsidian version or a plugin. Preserve unknown view-specific keys.

## Properties

- Refer to frontmatter as `note.<key>` in property display/order declarations.
- Simple filters commonly allow the bare property key, such as `status == "active"`.
- Useful file properties include `file.name`, `file.path`, `file.folder`, `file.ext`, and file methods such as `file.inFolder()` and `file.hasTag()`.
- Put human labels under `properties.<field>.displayName`; do not localize the stored machine key solely for presentation.
- Prefer YAML booleans and numbers over string lookalikes when the field is typed.

## Filters

Filters may be a string expression or nested `and`, `or`, and `not` collections. Put constraints shared by every view at the top level. Add per-view filters only for the difference.

The bundled offline evaluator supports:

- `and`, `or`, and `not` filter trees.
- `==`, `!=`, `<`, `<=`, `>`, and `>=`.
- `file.inFolder("...")` and `file.hasTag("...")`.
- `contains(property, value)` and `property.contains(value)`.
- Simple `&&`, `||`, and unary `!` combinations.

It does not evaluate formulas, date arithmetic, arbitrary functions, or plugin-defined behavior. Unsupported expressions must fail explicitly.

## Deterministic Base generation

`base-render` accepts JSON whose shape mirrors the Base YAML:

```json
{
  "filters": {
    "and": [
      "file.inFolder(\"application/research\")",
      "record_type == \"research-contact\""
    ]
  },
  "properties": {
    "file.name": {"displayName": "Record"},
    "note.status": {"displayName": "Status"}
  },
  "views": [
    {
      "type": "table",
      "name": "All",
      "order": ["file.name", "note.status"]
    }
  ]
}
```

Render it with:

```bash
python3 scripts/vault_tool.py base-render spec.json application/research/research.base --force
```

The JSON input makes automation deterministic without requiring a YAML package. The output remains readable YAML.

## Migration pattern

1. Decide which source rows become records and choose a destination folder.
2. Define stable property names and types before writing notes.
3. Preserve the source identifier only when it is useful for provenance or repeat imports.
4. Write one Markdown record per row.
5. Create the `.base` with global scope, display names, and useful views.
6. Query each view and compare expected counts.
7. Embed the Base in an index note with `![[name.base]]` when a landing page is useful.

Do not delete source-system records unless the user explicitly requests it.

## Official references

- Bases overview: https://help.obsidian.md/bases
- Bases syntax: https://help.obsidian.md/bases/syntax
- Create a Base: https://help.obsidian.md/bases/create-base
- Bases views: https://help.obsidian.md/bases/views
