# Official Headless Sync and Publish

## Purpose and requirements

Use the official `obsidian-headless` package when a machine must synchronize or publish a vault without the desktop app. It installs the `ob` command and requires Node.js 22 or later. Sync requires an active Obsidian Sync subscription.

Do not confuse the clients:

- `obsidian`: desktop-connected CLI with Base and application runtime commands.
- `ob`: headless client for Sync and Publish only.
- `vault_tool.py`: offline file engine for Markdown, YAML properties, links, audits, and supported Base operations.

## Detect without changing state

```bash
command -v ob
ob sync-list-local --json
ob sync-status --path /path/to/vault --json
```

Detection does not authorize installation, login, remote-vault creation, linking, configuration changes, Publish, or a persistent service. Ask before performing those actions.

## Setup commands

Use only after authorization:

```bash
npm install -g obsidian-headless
ob login
ob sync-list-remote --json
ob sync-setup --vault "Remote Vault" --path /path/to/vault --device-name "server-agent" --json
```

For end-to-end encrypted vaults, allow the client to prompt interactively when possible. Never store account passwords or encryption passwords in the vault, skill files, shell history, logs, or chat output. Use the operator's existing secret manager for unattended services.

## Agent workflow

Use this sequence for edits, migrations, and Base operations:

1. Confirm that the intended local and remote vaults are linked with `ob sync-status`.
2. Run one-time `ob sync` and require success before editing.
3. Perform targeted file or `vault_tool.py` operations.
4. Validate the failure relevant to the task, such as Base parsing, query results, required properties, or unresolved links.
5. Run one-time `ob sync` again.
6. Report separately whether local validation and remote synchronization succeeded.

Do not run two agent writers against the same notes. Prefer a bounded pull-edit-push cycle over `--continuous` while making a batch of changes.

## Base operations

`ob` synchronizes `.base` and Markdown files but does not list, create, parse, or query Bases. In a headless workflow:

- Create and edit `.base` YAML with normal file edits or `vault_tool.py base-render`.
- Query supported filters with `vault_tool.py base-query`.
- Modify a row by changing the YAML properties or body of its Markdown note.
- Preserve unsupported formulas and plugin view keys without pretending to evaluate them.
- Use the desktop `obsidian base:query` command when exact runtime evaluation is required.

## Continuous operation

Use `ob sync --continuous --path /path/to/vault` only when the user explicitly requests a long-running server process. Place it under the machine's existing service supervisor. Do not invent a service account, secrets location, restart policy, or excluded-folder policy without inspecting the server conventions.

Use `ob sync-config` to inspect before changing mode, conflict strategy, attachment types, configuration categories, or excluded folders. Sync is not an independent backup; retain the user's existing backup system or recommend one separately.

## Publish

Treat Publish as an external write. Use `ob publish --dry-run --json` for preview when available, and require user authorization before the final publish. Respect frontmatter `publish` values and configured include/exclude folders.

## Official references

- Headless client and command reference: https://github.com/obsidianmd/obsidian-headless
- Headless release announcement: https://obsidian.md/changelog/2026-02-27-sync/
- Obsidian Sync: https://obsidian.md/sync
