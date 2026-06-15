# SkillPointer — agent guide

Python-only repo. One script (`setup.py`) migrates personal agent skills into a hidden vault and generates category pointer skills to cut Level 1 startup token cost.

## Layout

| Path | Role |
|------|------|
| `setup.py` | CLI, heuristic categorization, migration, pointer generation |
| `justfile` | Shortcuts for `install`, `refresh-pointers`, `migrate` (`just --list`); omits `--agent` by default so the interactive menu matches the CLI — pass `agent=cursor` (etc.) for non-interactive runs |
| `README.md` | User-facing docs and install flow |
| `Install.bat` / `Install.vbs` | Windows launchers (`python setup.py install`) |
| `assets/` | SVG diagrams for README |

## Supported agents

Configured in `AGENT_PROFILES` inside `setup.py`:

| `--agent` | Active skills dir | Vault |
|-----------|-------------------|-------|
| `opencode` | `~/.config/opencode/skills` | `~/.opencode-skill-libraries` |
| `claude` | `~/.claude/skills` | `~/.skillpointer-vault` |
| `cursor` | `~/.cursor/skills` | `~/.cursor-skill-libraries` |

There is **no default agent**. Interactive runs show a menu; non-interactive runs must pass `--agent`.

## Editing `setup.py`

- **`AGENT_PROFILES`** — paths, labels, `template_key`, `bootstrap_skills_dir`
- **`POINTER_TEMPLATES`** — agent-specific pointer bodies (`opencode` vs `cursor` tool names)
- **`DOMAIN_HEURISTICS`** — keyword → category mapping; run `audit_domain_heuristics()` after edits
- **`migrate_skills()`** — only moves folders containing `SKILL.md`; skips `*-category-pointer`
- **`generate_pointers()`** — scans vault, creates/updates pointers, removes stale `*-category-pointer` dirs when vault category is missing or empty
- **`setup_directories()`** — creates `~/.cursor/skills` when missing (`bootstrap_skills_dir`); other agents require an existing dir

## CLI commands

| Command | Behavior |
|---------|----------|
| `install` (default) | `migrate_skills()` then `generate_pointers()` |
| `refresh-pointers` | Vault → pointers only; removes stale pointers |
| `migrate` | Ingest from active dir; refreshes pointers unless `--no-refresh-pointers` |

```bash
python setup.py install --agent cursor       # full run (Install.bat uses this)
python setup.py --agent cursor               # default command = install
python setup.py refresh-pointers --agent cursor
python setup.py migrate --agent cursor
python setup.py migrate --agent cursor --no-refresh-pointers
```

Keep changes small. Do not refactor unrelated heuristics or formatting when fixing a single agent path.

## Verification

No test suite. Before finishing a change:

```bash
just verify
# or manually:
python3 -m py_compile setup.py
python3 setup.py < /dev/null          # must exit 1 (non-interactive, no --agent)
python3 setup.py --help               # lists opencode, claude, cursor and subcommands
```

For behavior checks, use a temp skills/vault pair by setting `setup.CONFIG` in a short script — **do not** run `setup.py --agent cursor` (or others) against a real home skills dir unless the user asks. Exercise `refresh-pointers`, stale-pointer removal, and `migrate` ingest in the temp harness.

## Scope

- **In scope:** OpenCode, Claude Code, Cursor personal skills (`~/.cursor/skills`); post-setup `refresh-pointers` and `migrate` workflows
- **Out of scope (v1):** project `.cursor/skills/`, built-in `~/.cursor/skills-cursor/`, plugin cache skills, rules, restore/dry-run subcommands

## Commits

Only commit when the user asks. Use conventional commits with subject prefix `cursor - ` when committing from Cursor agent sessions.
