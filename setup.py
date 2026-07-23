"""Public setup entrypoint with agent-profile extensions.

The original implementation lives in setup_core.py. Keep this wrapper small so
agent-specific profile additions can remain reviewable without rewriting the
large migration engine.
"""

import re
from pathlib import Path

import setup_core as _core
from setup_core import *  # noqa: F401,F403


_CODEX_AGENT_KEY = "codex"
_CODEX_TEMPLATE_KEY = "codex"

_core.AGENT_PROFILES[_CODEX_AGENT_KEY] = {
    "label": "Codex",
    "active_skills_dir": Path.home() / ".agents" / "skills",
    "hidden_library_dir": Path.home() / ".codex-skill-libraries",
    "template_key": _CODEX_TEMPLATE_KEY,
    "bootstrap_skills_dir": True,
}

_core.POINTER_TEMPLATES[_CODEX_TEMPLATE_KEY] = """---
name: {category_name}-category-pointer
description: Use for {category_name} tasks. Indexes {count} local skills stored outside Codex's active skill scan path; inspect the vault and load the exact matching skill before acting.
---

# {category_title} Capability Library 🎯

You have a pointer to {count} specialized skills for {category_title}. The full skills are stored outside Codex's active skill directory to avoid crowding or truncating the initial skills list.

## Instructions
1. Inspect this local vault path: `{library_path}`
2. Find candidate `SKILL.md` files relevant to the user's exact task.
3. Read the most relevant skill file before proposing or editing anything.
4. Follow that skill's instructions, constraints, and validation steps.
5. If no relevant skill exists, say so and proceed without inventing one.

## Available Knowledge
This library contains {count} specialized skills covering various aspects of {category_title}.

**Hidden Library Path:** `{library_path}`

*Reminder: Do not guess best practices or blindly search GitHub. Always consult your local library files first.*
"""


def looks_like_legacy_managed_pointer(pointer_dir: Path, category: str) -> bool:
    """Detect SkillPointer-managed pointers generated before metadata existed.

    This overrides setup_core's two-template detector so agent-specific pointer
    templates can be adopted safely instead of being treated as unmanaged user
    content.
    """
    skill_path = pointer_dir / "SKILL.md"
    if not skill_path.is_file():
        return False

    try:
        content = skill_path.read_text(encoding="utf-8")
    except OSError:
        return False

    category_title = category.replace("-", " ").title()
    library_path = str((_core.CONFIG["hidden_library_dir"] / category).absolute()).replace(
        "\\", "/"
    )

    required_substrings = [
        f"name: {category}-category-pointer",
        f"# {category_title} Capability Library",
        f"**Hidden Library Path:** `{library_path}`",
        "*Reminder: Do not guess best practices or blindly search GitHub. Always consult your local library files first.*",
    ]

    template_key = _core.CONFIG["template_key"]
    if template_key == "cursor":
        required_substrings.extend(
            [
                "use `Glob` to browse the hidden library",
                "`Grep` if you need to search skill names or content",
            ]
        )
        count_pattern = re.compile(
            rf"Indexes \d+ specialized skills for {re.escape(category)}\."
        )
    elif template_key == _CODEX_TEMPLATE_KEY:
        required_substrings.extend(
            [
                "Inspect this local vault path:",
                "Find candidate `SKILL.md` files relevant to the user's exact task.",
                "If no relevant skill exists, say so and proceed without inventing one.",
            ]
        )
        count_pattern = re.compile(
            rf"You have a pointer to \d+ specialized skills for {re.escape(category_title)}\."
        )
    else:
        required_substrings.extend(
            [
                "you MUST use your file reading tools",
                "`list_dir` and `view_file` or `read_file`",
            ]
        )
        count_pattern = re.compile(
            rf"This library contains \d+ specialized skills covering various aspects of {re.escape(category_title)}\."
        )

    if not all(snippet in content for snippet in required_substrings):
        return False

    return bool(count_pattern.search(content))


_core.looks_like_legacy_managed_pointer = looks_like_legacy_managed_pointer

# Re-export patched mutable registries for tests and callers that import setup.
AGENT_PROFILES = _core.AGENT_PROFILES
POINTER_TEMPLATES = _core.POINTER_TEMPLATES
CONFIG = _core.CONFIG


def main(argv=None):
    return _core.main(argv)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{_core.Colors.WARNING}Setup cancelled by user.{_core.Colors.ENDC}")
    except Exception as e:
        print(f"\n{_core.Colors.FAIL}An unexpected error occurred: {e}{_core.Colors.ENDC}")
