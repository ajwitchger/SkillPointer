#!/usr/bin/env just --justfile

python := "python"

[private]
@default:
    just --justfile {{ justfile() }} --list --unsorted

# Run setup.py; omit agent to get the interactive menu (same as the CLI)
_run subcommand extra="" agent="":
    #!/bin/sh
    set -eu
    if [ -n "{{ agent }}" ]; then
        if [ -n "{{ extra }}" ]; then
            {{ python }} setup.py {{ subcommand }} {{ extra }} --agent "{{ agent }}"
        else
            {{ python }} setup.py {{ subcommand }} --agent "{{ agent }}"
        fi
    else
        if [ -n "{{ extra }}" ]; then
            {{ python }} setup.py {{ subcommand }} {{ extra }}
        else
            {{ python }} setup.py {{ subcommand }}
        fi
    fi

# Full setup: migrate active skills to vault, then refresh pointers
install agent="":
    @just _run install "" "{{ agent }}"

# Regenerate pointers from vault (no migration); removes stale pointers
refresh-pointers agent="":
    @just _run refresh-pointers "" "{{ agent }}"

# Ingest new skills from active dir, then refresh pointers
migrate agent="":
    @just _run migrate "" "{{ agent }}"

# Ingest only; run `just refresh-pointers` afterward for bulk vault edits
migrate-only agent="":
    @just _run migrate --no-refresh-pointers "{{ agent }}"

_check:
    {{ python }} -m py_compile setup.py setup_core.py

# Developer checks (no home-dir side effects except --help)
verify: _check
    {{ python }} setup.py --help
    {{ python }} setup.py --agent codex --help
    @just _verify-no-agent
    {{ python }} -m unittest

# Non-interactive runs without --agent must exit 1
_verify-no-agent:
    #!/bin/sh
    set +e
    output=$({{ python }} setup.py < /dev/null 2>&1)
    code=$?
    if [ "$code" -ne 1 ]; then
        printf '%s\n' "$output" >&2
        echo "expected exit 1, got $code" >&2
        exit 1
    fi
