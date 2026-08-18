---
name: obsidian-knowledge-manager
description: Manage, automate, and sync Obsidian vaults, Markdown notes, YAML properties, tasks, links, tags, attachments, daily notes, templates, and Bases databases. Use for structured knowledge-base migrations, `.base` creation or queries, bulk property changes, vault audits, backlink or unresolved-link analysis, desktop Obsidian CLI workflows, and official Headless Sync or Publish on servers without the desktop app. Work with the desktop CLI, the `ob` headless client, or vault files alone.
---

# Obsidian Knowledge Manager

Treat the vault files as the source of truth. Use the desktop CLI for Obsidian runtime behavior, the official `ob` client for headless Sync and Publish, and direct file operations for Markdown, YAML frontmatter, `.base`, JSON settings, and attachments.

## Select the backend

1. Locate the vault from the user, current directory, `.obsidian/`, or Obsidian's vault registry.
2. Detect the desktop CLI with `command -v obsidian`. On macOS also check `/Applications/Obsidian.app/Contents/MacOS/obsidian-cli`. Treat it as connected only when `obsidian version` succeeds.
3. Detect the official headless client with `command -v ob`. Treat Sync as configured only when `ob sync-status --path <vault> --json` succeeds.
4. Select one or more backends:
   - **Desktop runtime:** use connected `obsidian` commands for exact Base queries, plugin behavior, history, and UI-dependent operations.
   - **Headless transport:** use `ob` for Sync or Publish without the desktop app. Continue to edit and query Bases with the file backend.
   - **File backend:** use vault files and `scripts/vault_tool.py` when neither program is available or no remote operation is needed.
5. Do not block local work on installing or launching Obsidian. Do not log in, link a remote vault, start continuous Sync, or change Sync configuration unless the user authorizes that remote state change.

Read [references/cli-and-offline.md](references/cli-and-offline.md) when mapping operations between backends. Read [references/headless-sync.md](references/headless-sync.md) before configuring or running `ob`. Read [references/bases.md](references/bases.md) before creating, restructuring, or troubleshooting a Base.

## Core workflow

1. Inspect `.obsidian/app.json`, enabled core plugins, templates, daily-note settings, existing property conventions, and representative notes.
2. Preserve existing user changes and naming conventions. Prefer targeted edits over whole-vault rewrites.
3. Model database rows as Markdown notes with typed top-level YAML properties. Model the database UI as a separate `.base` file.
4. Apply changes with the narrowest suitable mechanism:
   - Use normal file editing for note bodies, tasks, links, settings, and `.base` definitions.
   - Use `scripts/vault_tool.py property-set` for repeatable typed property edits without Obsidian.
   - Use `scripts/vault_tool.py base-render` when generating a Base deterministically from JSON.
   - Use `scripts/vault_tool.py base-query` for common headless Base filters.
5. Validate the exact failure that matters. For migrations, verify expected record counts and required properties. For link work, audit unresolved targets. For Bases, parse and query every changed view.
6. If the desktop CLI is connected, finish with `bases`, `base:query`, `properties`, or another relevant runtime check. Otherwise report that validation used the file backend and note any unsupported runtime-only semantics.
7. When a linked Headless Sync backend is in scope, complete a one-time sync before editing, apply and validate local changes, then sync again. Stop on a failed sync rather than editing an uncertain local snapshot.

## Use Headless Sync with Base operations

`ob` transports vault files; it does not expose `base:*` commands or evaluate Bases. Compose it with the file backend:

```bash
ob sync --path /path/to/vault
python3 scripts/vault_tool.py base-query /path/to/vault path/to/research.base --view All --format json
# Apply and validate the requested file or Base changes.
ob sync --path /path/to/vault
```

Use `ob sync --continuous` only for an explicitly requested long-running service. Avoid concurrent edits to the same note while an agent performs a pull-edit-push cycle. Keep account and end-to-end encryption secrets outside the vault, prompts, command history, and logs.

## Use the offline tool

The bundled tool uses only the Python standard library.

```bash
python3 scripts/vault_tool.py property-set note.md status --value-json '"active"'
python3 scripts/vault_tool.py property-set note.md tags --value-json '["research", "active"]'
python3 scripts/vault_tool.py property-get note.md status
python3 scripts/vault_tool.py property-remove note.md obsolete_field

python3 scripts/vault_tool.py query /path/to/vault --property status --equals-json '"active"'
python3 scripts/vault_tool.py query /path/to/vault --tag research --format json
python3 scripts/vault_tool.py audit /path/to/vault --format summary

python3 scripts/vault_tool.py base-render base-spec.json path/to/research.base --force
python3 scripts/vault_tool.py base-query /path/to/vault path/to/research.base --view All --format json
```

Pass values as JSON to retain booleans, numbers, nulls, strings, lists, and mappings. Property edits preserve unrelated frontmatter and note content. Reject malformed delimiters, duplicate target keys, tabs in Base YAML, and unsupported filter expressions instead of guessing.

## Manage Bases correctly

- Keep one Markdown file per record. Put filterable fields in YAML frontmatter, not only in prose.
- Keep stable machine property names such as `status`, `priority`, and `record_type`; use Base `properties` display names for localization.
- Scope each Base with a folder filter plus a discriminating property when the folder can contain indexes or supporting notes.
- Create a small set of purposeful views. Put common constraints in top-level `filters` and view-specific constraints inside the view.
- Keep prose, citations, and long notes in the Markdown body. Do not force all content into properties.
- Do not replace notes with a proprietary database file. Obsidian Bases intentionally uses Markdown rows plus `.base` view definitions.
- Treat formulas or plugin-specific view behavior as runtime-only unless the offline tool explicitly supports the expression.

## Manage other knowledge features

- Use YAML `tags`, `aliases`, typed dates, checkboxes, and links consistently.
- Edit tasks as Markdown checkboxes and preserve custom status characters.
- Read daily-note and template locations from vault settings before creating files.
- Keep imported attachments under a dedicated subtree and set `attachmentFolderPath` for new local attachments. Remove unreferenced imports only when the user authorizes it.
- Use wikilinks for vault-local concepts and Markdown links for external URLs. After bulk moves or renames, check unresolved links.
- Distinguish structural quality signals from defects: an orphan or dead-end note can be intentional. Report it as a finding only when the vault's organization requires connectivity.

## Boundaries

The Headless Sync client cannot execute Base queries, plugins, or UI actions. The file backend cannot reproduce workspace state, command-palette actions, Sync/File Recovery history restoration, plugin execution, or every formula/plugin view. Use the desktop CLI or app for those runtime features. Never silently approximate unsupported Base formulas; preserve them and state that only syntax/structure was checked. Sync is transport, not a substitute for an independent backup.
