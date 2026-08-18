# Obsidian desktop, headless, and file backends

## Backend rule

The `obsidian` CLI connects to a running desktop process. The separate `ob` client runs Obsidian Sync and Publish without the desktop app. Neither replaces direct vault-file editing.

Use this priority:

1. Desktop CLI connected: use it for discovery, exact queries, and runtime validation; use files for controlled bulk edits.
2. Headless Sync configured: pull with `ob`, operate on files with `vault_tool.py`, validate, then push with `ob`.
3. No connected program: use the vault filesystem and `vault_tool.py` locally.
4. Desktop-only behavior required: explain the boundary and avoid fabricating an offline result.

## Operation mapping

| Intent | Desktop `obsidian` | Headless/file execution |
|---|---|---|
| List/read notes | `files`, `read`, `folder` | `rg --files`, ordinary file reads |
| Create/append/move/rename | `create`, `append`, `move`, `rename` | Targeted filesystem edits; update affected wikilinks after moves |
| Search text | `search`, `search:context` | `rg` with the same folder/case constraints |
| Read/set/remove properties | `properties`, `property:*` | `vault_tool.py property-*` |
| Query property/tag records | `base:query`, `tag`, `tags` | `vault_tool.py query` or `base-query` |
| List/query Bases | `bases`, `base:views`, `base:query` | Find `.base`; parse/query supported filters with `base-query` |
| Create a Base item | `base:create` | Create a Markdown record with the view's required properties |
| Backlinks/unresolved/orphans/deadends | matching CLI commands | `vault_tool.py audit` |
| Tasks | `tasks`, `task` | Read/edit exact `- [ ]` lines; preserve custom statuses |
| Daily note | `daily:*` | Read `.obsidian/daily-notes.json`, expand the configured format/folder/template |
| Templates | `templates`, `template:*` | Read `.obsidian/templates.json`; copy and resolve supported placeholders |
| Tags and aliases | `tags`, `aliases` | Parse YAML plus inline tags/wikilinks |
| Plugins/themes/workspace | CLI runtime commands | Inspect settings only; do not claim runtime state without the app |
| Sync current files | desktop Sync commands | `ob sync`; `ob` does not interpret Base contents |
| Sync/File Recovery history | desktop history commands | No headless restore command; do not claim history was checked |

## Headless pull-edit-push

For a linked remote vault, use a bounded cycle rather than continuous Sync during agent edits:

```bash
ob sync-status --path /path/to/vault --json
ob sync --path /path/to/vault
# Edit/query Markdown, YAML, and .base files here.
ob sync --path /path/to/vault
```

If the initial sync fails, stop before editing. If the final sync fails, preserve the validated local files and report that they remain unsynced. Read [headless-sync.md](headless-sync.md) for setup, secrets, and continuous-operation guidance.

## Valuable CLI checks

Use only checks tied to a concrete failure:

```bash
obsidian version
obsidian vault info=path
obsidian bases
obsidian base:query path="area/research.base" view="All" format=paths
obsidian properties name=status counts
obsidian unresolved counts
obsidian tasks todo
```

`base:views` reads the active Base in current CLI versions. Open the Base first or use `base:query` with an explicit path.

## File conventions

- `.obsidian/app.json`: attachment path and link behavior.
- `.obsidian/core-plugins.json`: enabled core plugins, including `bases`.
- `.obsidian/daily-notes.json`: daily-note folder, date format, template.
- `.obsidian/templates.json`: template folder.
- `.obsidian/types.json`: property type assignments when present.
- `*.md`: record data and prose.
- `*.base`: database filters, formulas, properties, and views.

Read JSON settings before changing them. Do not assume a conventional folder name when the vault already declares one.

## Official references

- Obsidian CLI: https://help.obsidian.md/cli
- CLI command reference: https://help.obsidian.md/cli/commands
- Obsidian Headless: https://github.com/obsidianmd/obsidian-headless
