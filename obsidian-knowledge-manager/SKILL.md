---
name: obsidian-knowledge-manager
description: Manage and automate Obsidian vaults, Markdown notes, YAML properties, tasks, links, tags, attachments, daily notes, templates, and Bases databases. Use for creating or migrating structured knowledge bases, editing or querying `.base` files, bulk property changes, vault audits, backlink or unresolved-link analysis, and Obsidian CLI workflows. Work both with the official desktop-dependent Obsidian CLI and on headless servers where only the vault files are available.
---

# Obsidian Knowledge Manager

Treat the vault files as the source of truth. Use the official CLI when it is available and connected to a running Obsidian instance; otherwise operate directly on Markdown, YAML frontmatter, `.base`, JSON settings, and attachments.

## Select the backend

1. Locate the vault from the user, current directory, `.obsidian/`, or Obsidian's vault registry.
2. Detect the CLI with `command -v obsidian`. On macOS also check `/Applications/Obsidian.app/Contents/MacOS/obsidian-cli`.
3. Run `obsidian version`. If it cannot connect, continue with the file backend; do not block on installing or launching the desktop app.
4. Use CLI results as runtime validation, not as the only way to edit the vault.

Read [references/cli-and-offline.md](references/cli-and-offline.md) when mapping a CLI operation to a headless equivalent. Read [references/bases.md](references/bases.md) before creating, restructuring, or troubleshooting a Base.

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
6. If the CLI is available, finish with `bases`, `base:query`, `properties`, or another relevant command. Otherwise report that validation used the file backend and note any unsupported runtime-only semantics.

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

The file backend cannot reproduce workspace UI state, command-palette actions, Sync history, File Recovery history, plugin execution, or every formula/plugin view. Use the official CLI or desktop app for those runtime features. Never silently approximate unsupported Base formulas; preserve them and state that only syntax/structure was checked.
