import os
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

# ==========================================
# 🎯 SkillPointer
# Infinite Context. Zero Token Tax.
# ==========================================


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


# Global configuration state (populated by apply_agent_profile before use)
CONFIG = {}

AGENT_PROFILES = {
    "opencode": {
        "label": "OpenCode",
        "active_skills_dir": Path.home() / ".config" / "opencode" / "skills",
        "hidden_library_dir": Path.home() / ".opencode-skill-libraries",
        "template_key": "opencode",
        "bootstrap_skills_dir": False,
    },
    "claude": {
        "label": "Claude Code",
        "active_skills_dir": Path.home() / ".claude" / "skills",
        "hidden_library_dir": Path.home() / ".skillpointer-vault",
        "template_key": "opencode",
        "bootstrap_skills_dir": False,
    },
    "cursor": {
        "label": "Cursor",
        "active_skills_dir": Path.home() / ".cursor" / "skills",
        "hidden_library_dir": Path.home() / ".cursor-skill-libraries",
        "template_key": "cursor",
        "bootstrap_skills_dir": True,
    },
}

POINTER_TEMPLATES = {
    "opencode": """---
name: {category_name}-category-pointer
description: Triggers when encountering any task related to {category_name}. This is a pointer to a library of specialized skills.
---

# {category_title} Capability Library 🎯

You do not have all {category_title} skills loaded immediately in your background context. Instead, you have access to a rich library of {count} highly-specialized skills on your local filesystem.

## Instructions
1. When you need to perform a task related to {category_name}, you MUST use your file reading tools (like `list_dir` and `view_file` or `read_file`) to browse the hidden library directory: `{library_path}`
2. Locate the specific Markdown files related to the exact sub-task you need.
3. Read the relevant Markdown file(s) into your context.
4. Follow the specific instructions and best practices found within those files to complete the user's request.

## Available Knowledge
This library contains {count} specialized skills covering various aspects of {category_title}.

**Hidden Library Path:** `{library_path}`

*Reminder: Do not guess best practices or blindly search GitHub. Always consult your local library files first.*
""",
    "cursor": """---
name: {category_name}-category-pointer
description: Indexes {count} specialized skills for {category_name}. Use when the task involves {category_name} topics and you need domain-specific workflow guidance from the local skill library.
---

# {category_title} Capability Library 🎯

You do not have all {category_title} skills loaded immediately in your background context. Instead, you have access to a rich library of {count} highly-specialized skills on your local filesystem.

## Instructions
1. When you need to perform a task related to {category_name}, use `Glob` to browse the hidden library (e.g. `{library_path}/**/SKILL.md`) and `Read` to load the specific skill file you need.
2. Use `Grep` if you need to search skill names or content within the library directory.
3. Read the relevant `SKILL.md` file(s) into your context.
4. Follow the specific instructions and best practices found within those files to complete the user's request.

## Available Knowledge
This library contains {count} specialized skills covering various aspects of {category_title}.

**Hidden Library Path:** `{library_path}`

*Reminder: Do not guess best practices or blindly search GitHub. Always consult your local library files first.*
""",
}

# Advanced Heuristic Engine for Universal Categorization
DOMAIN_HEURISTICS = {
    "security": [
        "attack",
        "injection",
        "vulnerability",
        "xss",
        "penetration",
        "privilege",
        "fuzzing",
        "auth",
        "jwt",
        "oauth",
        "bypass",
        "malware",
        "forensics",
        "hacker",
        "wireshark",
        "nmap",
        "security",
        "exploit",
        "encryption",
    ],
    "code-review": [
        "code-review",
        "requesting-code-review",
        "code-review-excellence",
        "pr-review",
        "review-agent",
        "reviewer",
        "review-bot",
        "static-analysis",
        "quality-gate",
        "sonarqube",
        "doubt-driven-development",
    ],
    "git": [
        "git",
        "github",
        "gitlab",
        "pull-request",
        "merge-request",
        "commit",
        "branch",
        "rebase",
        "cherry-pick",
        "stash",
        "tag",
        "release",
        "conventional-commits",
        "babysit",
        "split-to-prs",
    ],
    "ai-ml": [
        "ai-",
        "ml-",
        "llm",
        "agent",
        "gpt",
        "claude",
        "gemini",
        "openai",
        "anthropic",
        "cursor",
        "prompt",
        "rag",
        "diffusion",
        "huggingface",
        "pytorch",
        "tensorflow",
        "comfy",
        "flux",
        "machine-learning",
        "deep-learning",
        "vision",
        "nlp",
    ],
    "web-dev": [
        "angular",
        "react",
        "vue",
        "tailwind",
        "frontend",
        "css",
        "html",
        "nextjs",
        "svelte",
        "astro",
        "web",
        "dom",
        "ui-patterns",
        "vercel",
        "shopify",
        "styles",
        "sass",
        "less",
        "bootstrap",
    ],
    "backend-dev": [
        "api",
        "nestjs",
        "express",
        "django",
        "flask",
        "fastapi",
        "spring",
        "laravel",
        "node",
        "graphql",
        "rest",
        "grpc",
        "backend",
        "server",
        "microservice",
        "go-",
        "rust-",
    ],
    "devops": [
        "aws",
        "azure",
        "docker",
        "kubernetes",
        "ci-cd",
        "terraform",
        "ansible",
        "github-actions",
        "jenkins",
        "devops",
        "cloud",
        "linux",
        "ubuntu",
        "k8s",
        "bash",
        "deploy",
        "nginx",
        "local-stack",
        "shipping-and-launch",
    ],
    "database": [
        "sql",
        "mysql",
        "postgres",
        "mongo",
        "redis",
        "database",
        "schema",
        "prisma",
        "orm",
        "nosql",
        "supabase",
        "neon",
        "db-",
        "sqlite",
    ],
    "design": [
        "ui",
        "ux",
        "design",
        "figma",
        "avatar",
        "background-removal",
        "svg",
        "animation",
        "motion",
        "framer",
        "photoshop",
        "illustrator",
        "creative",
        "canvas",
        "image-enhancer",
    ],
    "automation": [
        "automation",
        "zapier",
        "make",
        "n8n",
        "selenium",
        "playwright",
        "puppeteer",
        "bot",
        "workflow",
        "scraper",
        "cron",
        "automate",
        "bulk-scripting",
        "file-organizer",
        "loop",
    ],
    "mobile": [
        "ios",
        "android",
        "react-native",
        "flutter",
        "swift",
        "mobile",
        "xcode",
        "mobile-",
    ],
    "game-dev": [
        "game",
        "unity",
        "unreal",
        "godot",
        "phaser",
        "3d",
        "vr",
        "ar",
        "raylib",
        "pygame",
    ],
    "business": [
        "business",
        "founder",
        "sales",
        "marketing",
        "seo",
        "growth",
        "product",
        "agile",
        "scrum",
        "jira",
        "b2b",
        "crm",
        "idea-refine",
        "meeting-insights-analyzer",
    ],
    "writing": [
        "writing",
        "copywriting",
        "blog",
        "documentation",
        "docs",
        "readme",
        "study",
        "teardown",
        "content",
        "journalism",
        "text-extraction",
        "concise-engineering-docs",
        "communication",
        "internal-comms",
    ],
    "3d-graphics": [
        "blender",
        "threejs",
        "webgl",
        "rendering",
        "3d-",
        "mesh",
        "texture",
        "shader",
    ],
    "aerospace": [
        "satellite",
        "orbit",
        "space",
        "aerodynamics",
        "avionic",
        "spacecraft",
    ],
    "agents": [
        "multi-agent",
        "swarm",
        "autonomous",
        "orchestration",
        "chain",
        "autogen",
        "crewai",
    ],
    "animation": [
        "gsap",
        "lottie",
        "keyframe",
        "transition",
        "tween",
        "rigging",
    ],
    "architecture": [
        "pattern",
        "clean-code",
        "system-design",
        "solid-",
        "ddd",
        "-driven-development",
        "architect",
        "code-simplification",
        "deprecation-and-migration",
        "incremental-implementation",
        "planning-and-task-breakdown",
        "source-driven-development",
        "spec-driven-development",
    ],
    "biomedical": [
        "dna",
        "protein",
        "medical",
        "health",
        "genomics",
        "bioinfo",
        "clinical",
    ],
    "blockchain": [
        "crypto",
        "web3",
        "solidity",
        "smart-contract",
        "ethereum",
        "bitcoin",
        "nft",
        "staking",
    ],
    "compliance": [
        "gdpr",
        "hipaa",
        "soc2",
        "audit",
        "policy",
        "legal",
        "privacy",
        "remediation",
    ],
    "data-science": [
        "pandas",
        "numpy",
        "matplotlib",
        "scikit",
        "jupyter",
        "visualization",
        "data-",
        "etl",
    ],
    "education": [
        "learning",
        "course",
        "tutor",
        "student",
        "curriculum",
        "teaching",
        "university",
    ],
    "finance": [
        "trading",
        "stock",
        "portfolio",
        "banking",
        "ledger",
        "investment",
        "fintech",
    ],
    "marketing": [
        "ads",
        "campaign",
        "social-media",
        "brand",
        "analytics",
        "funnel",
        "email-marketing",
    ],
    "mcp": [
        "mcp-",
        "model-context-protocol",
        "server-",
        "client-",
        "-mcp",
    ],
    "media-production": [
        "video",
        "audio",
        "podcast",
        "editing",
        "streaming",
        "ffmpeg",
        "obs",
    ],
    "programming": [
        "python",
        "javascript",
        "typescript",
        "java",
        "cpp",
        "ruby",
        "php",
        "csharp",
        "kotlin",
        "algorithm",
        "data-structure",
    ],
    "prompt-engineering": [
        "system-prompt",
        "few-shot",
        "chain-of-thought",
        "prompt-",
        "meta-prompt",
        "context-engineering",
        "create-hook",
        "create-rule",
        "create-skill",
        "migrate-to-skills",
        "skill-creator",
        "cursor-settings",
    ],
    "quantum": [
        "qubit",
        "qiskit",
        "quantum-",
        "superposition",
        "entanglement",
    ],
    "robotics": [
        "ros",
        "arduino",
        "raspberry",
        "hardware",
        "sensor",
        "firmware",
        "robot",
    ],
    "simulation": [
        "physics",
        "modeling",
        "sim-",
        "digital-twin",
        "solver",
    ],
    "testing": [
        "test-",
        "unit-test",
        "testing",
        "jest",
        "pytest",
        "cypress",
        "quality",
        "qa-",
        "debug",
        "devtools",
        "browser-testing-with-devtools",
        "debugging-and-error-recovery",
    ],
    "tooling": [
        "cli",
        "prettier",
        "eslint",
        "bundler",
        "npm",
        "pip",
        "extension",
        "plugin",
        "patcher",
        "version-sync",
        "-sync",
        "just",
        "meta-layer-",
        "sdk",
        "shell",
        "statusline",
    ],
}


def standardize_heuristic_text(text: str) -> str:
    return text.strip().lower().replace("_", "-").replace(" ", "-")


def is_phrase_heuristic(text: str) -> bool:
    parts = text.split("-")
    return len(parts) > 1 and all(parts)


def normalize_heuristic_term(term: str) -> str:
    standardized_term = standardize_heuristic_text(term)
    if is_phrase_heuristic(standardized_term):
        return standardized_term.replace("-", "")
    return standardized_term


def compile_domain_heuristics():
    compiled_heuristics = {}
    for category, keywords in DOMAIN_HEURISTICS.items():
        compiled_heuristics[category] = [
            (
                normalize_heuristic_term(keyword),
                is_phrase_heuristic(standardize_heuristic_text(keyword)),
            )
            for keyword in keywords
        ]
    return compiled_heuristics


COMPILED_DOMAIN_HEURISTICS = compile_domain_heuristics()
PR_REVIEW_TERMS = tuple(
    (
        normalize_heuristic_term(term),
        is_phrase_heuristic(standardize_heuristic_text(term)),
    )
    for term in ("pr-review", "pull-request", "merge-request")
)


def matches_heuristic(
    name_standardized: str,
    name_collapsed: str,
    heuristic_term: str,
    use_collapsed_name: bool,
    exact_match: bool,
) -> bool:
    target_name = name_collapsed if use_collapsed_name else name_standardized
    if exact_match:
        return target_name == heuristic_term
    return heuristic_term in target_name


def audit_domain_heuristics():
    intra_category_duplicates = []
    cross_category_terms = defaultdict(lambda: defaultdict(list))

    for category, keywords in DOMAIN_HEURISTICS.items():
        normalized_terms = defaultdict(list)
        for keyword in keywords:
            normalized_keyword = normalize_heuristic_term(keyword)
            normalized_terms[normalized_keyword].append(keyword)
            cross_category_terms[normalized_keyword][category].append(keyword)

        duplicates = {
            normalized_keyword: spellings
            for normalized_keyword, spellings in normalized_terms.items()
            if len(spellings) > 1
        }
        if duplicates:
            intra_category_duplicates.append((category, duplicates))

    cross_category_collisions = {
        normalized_keyword: categories
        for normalized_keyword, categories in cross_category_terms.items()
        if len(categories) > 1
    }

    if not intra_category_duplicates and not cross_category_collisions:
        return

    print(f"{Colors.WARNING}⚠ Heuristic audit found normalized collisions:{Colors.ENDC}")

    for category, duplicates in intra_category_duplicates:
        rendered_duplicates = "; ".join(
            f"{normalized_keyword}: {', '.join(spellings)}"
            for normalized_keyword, spellings in sorted(duplicates.items())
        )
        print(f"  within {category}: {rendered_duplicates}")

    for normalized_keyword, categories in sorted(cross_category_collisions.items()):
        rendered_categories = ", ".join(
            f"{category} ({', '.join(spellings)})"
            for category, spellings in sorted(categories.items())
        )
        print(f"  cross-category {normalized_keyword}: {rendered_categories}")


def print_banner():
    print(f"\n{Colors.BOLD}{Colors.CYAN}    🎯 SkillPointer {Colors.ENDC}")
    print(f"{Colors.BLUE}    Infinite Context. Zero Token Tax.\n{Colors.ENDC}")


def apply_agent_profile(agent_key: str) -> None:
    profile = AGENT_PROFILES[agent_key]
    CONFIG["agent_key"] = agent_key
    CONFIG["agent_name"] = profile["label"]
    CONFIG["active_skills_dir"] = profile["active_skills_dir"]
    CONFIG["hidden_library_dir"] = profile["hidden_library_dir"]
    CONFIG["template_key"] = profile["template_key"]
    CONFIG["bootstrap_skills_dir"] = profile["bootstrap_skills_dir"]


def prompt_for_agent() -> str:
    print(f"{Colors.BOLD}Select your AI agent:{Colors.ENDC}\n")
    agent_keys = list(AGENT_PROFILES.keys())
    for index, key in enumerate(agent_keys, start=1):
        profile = AGENT_PROFILES[key]
        print(f"  {index}) {profile['label']} → {profile['active_skills_dir']}")
    print()

    while True:
        try:
            choice = input("Enter choice (number or agent name): ").strip()
        except EOFError:
            print(f"\n{Colors.WARNING}No input received. Exiting.{Colors.ENDC}")
            sys.exit(1)

        if not choice:
            print(f"{Colors.WARNING}Please enter a choice.{Colors.ENDC}")
            continue

        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(agent_keys):
                return agent_keys[index - 1]
        elif choice in AGENT_PROFILES:
            return choice

        print(
            f"{Colors.WARNING}Invalid choice. Enter 1-{len(agent_keys)} or: {', '.join(agent_keys)}{Colors.ENDC}"
        )


def resolve_agent(agent_arg: Optional[str]) -> str:
    if agent_arg:
        return agent_arg
    if not sys.stdin.isatty():
        print(
            f"{Colors.FAIL}Error: --agent is required in non-interactive mode. "
            f"Choose: {', '.join(AGENT_PROFILES.keys())}{Colors.ENDC}"
        )
        sys.exit(1)
    return prompt_for_agent()


def get_category_for_skill(skill_name: str) -> str:
    # Detect exact search within quotes
    exact_match = False
    if skill_name.startswith('"') and skill_name.endswith('"'):
        exact_match = True
        name_standardized = standardize_heuristic_text(skill_name[1:-1])
    else:
        name_standardized = standardize_heuristic_text(skill_name)
    name_collapsed = name_standardized.replace("-", "")

    has_pr_term = any(
        matches_heuristic(
            name_standardized,
            name_collapsed,
            term,
            use_collapsed_name,
            False,
        )
        for term, use_collapsed_name in PR_REVIEW_TERMS
    )
    if "review" in name_collapsed and has_pr_term:
        return "code-review"

    for category, keywords in COMPILED_DOMAIN_HEURISTICS.items():
        if any(
            matches_heuristic(
                name_standardized,
                name_collapsed,
                heuristic_term,
                use_collapsed_name,
                exact_match,
            )
            for heuristic_term, use_collapsed_name in keywords
        ):
            return category
    return "_uncategorized"


def setup_directories():
    agent_name = CONFIG["agent_name"]
    active_skills_dir = CONFIG["active_skills_dir"]
    hidden_library_dir = CONFIG["hidden_library_dir"]

    if not active_skills_dir.exists():
        if CONFIG.get("bootstrap_skills_dir"):
            active_skills_dir.mkdir(parents=True, exist_ok=True)
            print(
                f"{Colors.BLUE}✔ Created skills directory at {active_skills_dir}{Colors.ENDC}"
            )
        else:
            print(
                f"{Colors.FAIL}✖ Error: {agent_name} skills directory not found at {active_skills_dir}{Colors.ENDC}"
            )
            print(
                f"{Colors.WARNING}Please ensure {agent_name} is installed and configured.{Colors.ENDC}"
            )
            return False

    if not os.access(active_skills_dir, os.W_OK):
        print(
            f"{Colors.FAIL}✖ Error: Skills directory is not writable: {active_skills_dir}{Colors.ENDC}"
        )
        return False

    hidden_library_dir.mkdir(parents=True, exist_ok=True)
    return True


def migrate_skills():
    active_skills_dir = CONFIG["active_skills_dir"]
    hidden_library_dir = CONFIG["hidden_library_dir"]

    print(f"{Colors.BOLD}📦 Phase 1: Analyzing and Migrating Skills...{Colors.ENDC}\n")

    category_counts = {}
    moved_count = 0
    pointer_count = 0

    for folder in list(active_skills_dir.iterdir()):
        if not folder.is_dir():
            continue

        # Ignore existing pointers
        if folder.name.endswith("-category-pointer"):
            pointer_count += 1
            continue

        # Only migrate valid skill folders
        if not (folder / "SKILL.md").is_file():
            continue

        # Ignore empty folders
        if not any(folder.iterdir()):
            continue

        category = get_category_for_skill(folder.name)
        cat_dir = hidden_library_dir / category
        cat_dir.mkdir(parents=True, exist_ok=True)

        dest = cat_dir / folder.name
        if dest.exists():
            shutil.rmtree(dest)

        shutil.move(str(folder), str(cat_dir))

        category_counts[category] = category_counts.get(category, 0) + 1
        moved_count += 1

        # Visually print a few for effect, but not all to avoid spam
        if moved_count <= 5 or moved_count % 50 == 0:
            print(
                f"{Colors.GREEN}  ↳ Mapped '{folder.name}' ➔ {category}/{Colors.ENDC}"
            )

    if moved_count > 5:
        print(
            f"{Colors.GREEN}  ...and {moved_count - 5} more skills safely migrated.{Colors.ENDC}"
        )

    print(
        f"\n{Colors.BLUE}✔ Successfully migrated {moved_count} raw skills into the hidden vault at {hidden_library_dir}{Colors.ENDC}\n"
    )
    if moved_count == 0:
        print(
            f"{Colors.WARNING}  No new skills in active dir; run `refresh-pointers` if you edited the vault manually.{Colors.ENDC}\n"
        )
    return category_counts


def generate_pointers():
    active_skills_dir = CONFIG["active_skills_dir"]
    hidden_library_dir = CONFIG["hidden_library_dir"]

    print(
        f"{Colors.BOLD}⚡ Phase 2: Generating Dynamic Category Pointers...{Colors.ENDC}\n"
    )

    template_key = CONFIG["template_key"]
    pointer_template = POINTER_TEMPLATES[template_key]

    created = 0
    updated = 0
    removed = 0
    total_indexed = 0

    # Scan the vault to index categories with at least one SKILL.md
    vault_counts = {}
    for cat_dir in hidden_library_dir.iterdir():
        if not cat_dir.is_dir():
            continue

        count = sum(1 for p in cat_dir.rglob("SKILL.md"))
        if count > 0:
            vault_counts[cat_dir.name] = count

    for cat, count in vault_counts.items():
        total_indexed += count

        pointer_name = f"{cat}-category-pointer"
        pointer_dir = active_skills_dir / pointer_name
        existed = (pointer_dir / "SKILL.md").is_file()
        pointer_dir.mkdir(parents=True, exist_ok=True)

        cat_title = cat.replace("-", " ").title()
        library_path = str((hidden_library_dir / cat).absolute()).replace(
            "\\", "/"
        )

        content = pointer_template.format(
            category_name=cat,
            category_title=cat_title,
            count=count,
            library_path=library_path,
        )

        with open(pointer_dir / "SKILL.md", "w", encoding="utf-8") as f:
            f.write(content)

        if existed:
            updated += 1
            print(
                f"{Colors.CYAN}  ⊕ Updated {pointer_name} ➔ Indexes {count} skills.{Colors.ENDC}"
            )
        else:
            created += 1
            print(
                f"{Colors.CYAN}  ⊕ Created {pointer_name} ➔ Indexes {count} skills.{Colors.ENDC}"
            )

    for folder in list(active_skills_dir.iterdir()):
        if not folder.is_dir():
            continue
        if not folder.name.endswith("-category-pointer"):
            continue
        if not (folder / "SKILL.md").is_file():
            continue

        cat = folder.name.removesuffix("-category-pointer")
        if cat not in vault_counts:
            shutil.rmtree(folder)
            removed += 1
            print(
                f"{Colors.WARNING}  ⊖ Removed stale pointer {folder.name} (vault category missing or empty).{Colors.ENDC}"
            )

    pointer_total = created + updated
    print(
        f"\n{Colors.BLUE}✔ Pointers: {created} created, {updated} updated, {removed} removed — "
        f"{pointer_total} active pointers indexing {total_indexed} total skills.{Colors.ENDC}"
    )
    return {
        "created": created,
        "updated": updated,
        "removed": removed,
        "total_indexed": total_indexed,
    }


def run_install():
    migrate_skills()
    time.sleep(1)
    generate_pointers()


def run_refresh_pointers():
    generate_pointers()


def run_migrate(refresh: bool = True):
    migrate_skills()
    if refresh:
        time.sleep(1)
        generate_pointers()


def print_complete_message():
    print(
        f"\n{Colors.BOLD}{Colors.GREEN}=========================================={Colors.ENDC}"
    )
    print(
        f"{Colors.BOLD}{Colors.GREEN}✨ Setup Complete! Your AI is now optimized. ✨{Colors.ENDC}"
    )
    print(
        f"{Colors.BOLD}{Colors.GREEN}=========================================={Colors.ENDC}"
    )
    print(f"Your active skills directory now only contains optimized Pointers.")
    print(
        "When you prompt your AI, its context window will be completely empty, but it will dynamically fetch from your massive library exactly when needed."
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="SkillPointer Setup - Infinite Context. Zero Token Tax."
    )
    parser.add_argument(
        "--agent",
        choices=list(AGENT_PROFILES.keys()),
        help="Target AI agent (skips interactive prompt when provided)",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser(
        "install",
        help="Migrate skills from active dir to vault, then refresh pointers (default)",
    )
    subparsers.add_parser(
        "refresh-pointers",
        help="Regenerate category pointers from vault (no migration)",
    )
    migrate_parser = subparsers.add_parser(
        "migrate",
        help="Ingest new skills from active dir into vault",
    )
    migrate_parser.add_argument(
        "--no-refresh-pointers",
        action="store_true",
        help="Skip pointer refresh after migration",
    )

    args = parser.parse_args()
    command = args.command or "install"

    agent_key = resolve_agent(args.agent)
    apply_agent_profile(agent_key)

    print_banner()
    audit_domain_heuristics()
    if not setup_directories():
        return

    if command == "install":
        time.sleep(1)
        run_install()
    elif command == "refresh-pointers":
        run_refresh_pointers()
    elif command == "migrate":
        time.sleep(1)
        run_migrate(refresh=not args.no_refresh_pointers)
    else:
        parser.error(f"unknown command: {command}")

    print_complete_message()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Setup cancelled by user.{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}An unexpected error occurred: {e}{Colors.ENDC}")
