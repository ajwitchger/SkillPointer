# SkillPointer — public agent guide

Python-only repo. `setup.py` is the public CLI entrypoint; `setup_core.py` contains the preserved migration engine. The setup flow migrates personal agent skills into a hidden vault and generates category pointer skills.

## Layout

| Path | Role |
|------|------|
| `setup.py` | Public CLI wrapper, agent profile extensions, compatibility entrypoint |
| `setup_core.py` | Core CLI, heuristic categorization, migration, pointer generation |
| `justfile` | Shortcuts for `install`, `refresh-pointers`, `migrate`, `verify` |
| `README.md` | User-facing docs and install flow |
| `Install.bat` / `Install.vbs` | Windows launchers |
| `assets/` | README diagrams and icons |
| `tests/` | stdlib `unittest` regression coverage |

## Supported agents

Configured in `AGENT_PROFILES` inside `setup.py` / `setup_core.py`:

| `--agent` | Active skills dir | Vault |
|-----------|-------------------|-------|
| `opencode` | `~/.config/opencode/skills` | `~/.opencode-skill-libraries` |
| `claude` | `~/.claude/skills` | `~/.skillpointer-vault` |
| `cursor` | `~/.cursor/skills` | `~/.cursor-skill-libraries` |
| `codex` | `~/.agents/skills` | `~/.codex-skill-libraries` |

There is no default agent. Interactive runs show a menu; non-interactive runs must pass `--agent`.

Codex support is scoped to user-level skills in `~/.agents/skills`. Do not migrate repo-scoped `.agents/skills` or admin `/etc/codex/skills` content unless this repo explicitly adds that behavior.

## Commands

```bash
python setup.py install --agent cursor
python setup.py install --agent codex
python setup.py refresh-pointers --agent cursor
python setup.py migrate --agent cursor
python setup.py migrate --agent cursor --no-refresh-pointers
just verify
```

## Validation

`just verify` runs:

- `python -m py_compile setup.py setup_core.py`
- `python setup.py --help`
- `python setup.py --agent codex --help`
- the non-interactive no-agent exit check
- `python -m unittest`

Codex command-path tests patch `AGENT_PROFILES["codex"]` to temporary active/vault paths, so verification does not mutate `~/.agents/skills` or `~/.codex-skill-libraries`.

## Local overrides

If you need machine-local or private agent instructions, keep them in `AGENTS.local.md`. That file is intentionally untracked.

Codex review state is also local runtime state. Keep `.codex/review-state.md` and related scratch files untracked unless this repo explicitly documents them as committed source material.
