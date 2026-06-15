# SkillPointer — public agent guide

Python-only repo. `setup.py` migrates personal agent skills into a hidden vault and generates category pointer skills.

## Layout

| Path | Role |
|------|------|
| `setup.py` | CLI, heuristic categorization, migration, pointer generation |
| `justfile` | Shortcuts for `install`, `refresh-pointers`, `migrate`, `verify` |
| `README.md` | User-facing docs and install flow |
| `Install.bat` / `Install.vbs` | Windows launchers |
| `assets/` | README diagrams and icons |
| `tests/` | stdlib `unittest` regression coverage |

## Supported agents

Configured in `AGENT_PROFILES` inside `setup.py`:

| `--agent` | Active skills dir | Vault |
|-----------|-------------------|-------|
| `opencode` | `~/.config/opencode/skills` | `~/.opencode-skill-libraries` |
| `claude` | `~/.claude/skills` | `~/.skillpointer-vault` |
| `cursor` | `~/.cursor/skills` | `~/.cursor-skill-libraries` |

There is no default agent. Interactive runs show a menu; non-interactive runs must pass `--agent`.

## Commands

```bash
python setup.py install --agent cursor
python setup.py refresh-pointers --agent cursor
python setup.py migrate --agent cursor
python setup.py migrate --agent cursor --no-refresh-pointers
just verify
```

## Validation

`just verify` runs:

- `python3 -m py_compile setup.py`
- `python3 setup.py --help`
- the non-interactive no-agent exit check
- `python3 -m unittest`

## Local overrides

If you need machine-local or private agent instructions, keep them in `AGENTS.local.md`. That file is intentionally untracked.
