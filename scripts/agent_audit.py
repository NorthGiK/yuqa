#!/usr/bin/env python3
"""Emit a compact repository map and validate layer boundaries."""

import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "yuqa"
TESTS_ROOT = ROOT / "tests"
DOCS_ROOT = ROOT / "docs"

DOMAIN_PACKAGES = (
    "banners",
    "battle_pass",
    "battles",
    "cards",
    "clans",
    "ideas",
    "players",
    "quests",
    "shop",
)
LAYER_GROUPS = {
    "domain": {f"yuqa.{name}" for name in DOMAIN_PACKAGES},
    "telegram": {"yuqa.telegram"},
    "infrastructure": {"yuqa.infrastructure"},
    "shared": {"yuqa.shared"},
    "application": {"yuqa.application"},
}
HOTSPOT_THRESHOLD = 800
FEATURE_NAME_ALIASES = {
    "banners": ("banners", "banner"),
    "battle_pass": ("battle_pass", "battlepass"),
    "battles": ("battles", "battle"),
    "cards": ("cards", "card"),
    "clans": ("clans", "clan"),
    "ideas": ("ideas", "idea"),
    "players": ("players", "player"),
    "quests": ("quests", "quest"),
    "shop": ("shop",),
}


@dataclass(slots=True)
class PythonModule:
    """Minimal static metadata for one Python module."""

    path: Path
    module: str
    imports: set[str]
    lines: int
    functions: int
    classes: int


def _module_name(path: Path) -> str:
    relative = path.relative_to(ROOT).with_suffix("")
    return ".".join(relative.parts)


def _path_from_root(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _top_level_package(module: str) -> str | None:
    parts = module.split(".")
    if len(parts) < 2 or parts[0] != "yuqa":
        return None
    return ".".join(parts[:2])


def _read_python_module(path: Path) -> PythonModule:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.add(name.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            if node.level:
                module = _module_name(path)
                base_parts = module.split(".")[:-1]
                target_parts = base_parts[: len(base_parts) - node.level + 1]
                imports.add(".".join(target_parts + [node.module]))
            else:
                imports.add(node.module)
    functions = sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in ast.walk(tree)
    )
    classes = sum(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
    return PythonModule(
        path=path,
        module=_module_name(path),
        imports=imports,
        lines=source.count("\n") + 1,
        functions=functions,
        classes=classes,
    )


def _iter_python_modules(root: Path) -> list[PythonModule]:
    return [_read_python_module(path) for path in sorted(root.rglob("*.py"))]


def _feature_tests(name: str, test_modules: list[PythonModule]) -> list[str]:
    """Return direct test files that touch a feature by import or filename."""

    prefix = f"yuqa.{name}"
    aliases = FEATURE_NAME_ALIASES[name]
    matched = {
        _path_from_root(module.path)
        for module in test_modules
        if any(
            imported == prefix or imported.startswith(prefix + ".")
            for imported in module.imports
        )
        or any(alias in module.path.stem for alias in aliases)
    }
    return sorted(matched)


def _feature_summary(name: str, test_modules: list[PythonModule]) -> dict[str, object]:
    base = PACKAGE_ROOT / name
    domain_dir = base / "domain"
    files = sorted(_path_from_root(path) for path in base.rglob("*.py"))
    tests = _feature_tests(name, test_modules)
    return {
        "name": name,
        "domain_modules": sorted(
            path.name for path in domain_dir.glob("*.py") if path.is_file()
        ),
        "files": files,
        "tests": tests,
        "test_status": "direct" if tests else "missing_direct_tests",
    }


def _runtime_flow() -> list[dict[str, str]]:
    """Return the normal runtime entry flow for debugging."""

    return [
        {"path": "main.py", "role": "CLI shim that forwards into the package entrypoint."},
        {
            "path": "yuqa/main.py",
            "role": "Loads env settings, runs migrations, builds services, and starts polling.",
        },
        {
            "path": "yuqa/telegram/services.py",
            "role": "Builds repositories, selects storage mode, and hosts shared service helpers.",
        },
        {
            "path": "yuqa/telegram/services_battles.py",
            "role": "Owns battle drafting, round resolution, and matchmaking behavior.",
        },
        {
            "path": "yuqa/telegram/services_battle_pass.py",
            "role": "Owns battle pass seasons, levels, and progress purchasing.",
        },
        {
            "path": "yuqa/telegram/services_players.py",
            "role": "Owns player lookup, profile, free rewards, and deck construction.",
        },
        {
            "path": "yuqa/telegram/services_social.py",
            "role": "Owns clan membership and idea proposal/moderation flows.",
        },
        {
            "path": "yuqa/telegram/services_content.py",
            "role": "Owns card, banner, shop, starter-card, and admin content flows.",
        },
        {
            "path": "yuqa/telegram/services_support.py",
            "role": "Holds small shared service dataclasses and utility helpers.",
        },
        {
            "path": "yuqa/telegram/router.py",
            "role": "Registers handlers, FSM flows, and callback wiring.",
        },
        {
            "path": "yuqa/telegram/router_views.py",
            "role": "Renders Telegram screens and admin sections reused by handlers.",
        },
        {
            "path": "yuqa/telegram/router_helpers.py",
            "role": "Holds parsing, pagination, and media extraction helpers for router flows.",
        },
    ]


def _module_groups() -> dict[str, list[str]]:
    """Return grouped edit paths for common tasks."""

    return {
        "runtime_bootstrap": ["main.py", "yuqa/main.py", "yuqa/telegram/config.py"],
        "telegram_flow": [
            "yuqa/telegram/router.py",
            "yuqa/telegram/states.py",
            "yuqa/telegram/callbacks.py",
        ],
        "telegram_views": [
            "yuqa/telegram/router_views.py",
            "yuqa/telegram/texts.py",
            "yuqa/telegram/ui.py",
            "yuqa/telegram/reply.py",
        ],
        "telegram_texts": [
            "yuqa/telegram/texts.py",
            "yuqa/telegram/texts_navigation.py",
            "yuqa/telegram/texts_battle.py",
            "yuqa/telegram/texts_battle_pass.py",
            "yuqa/telegram/texts_profile.py",
            "yuqa/telegram/texts_cards.py",
            "yuqa/telegram/texts_rewards.py",
            "yuqa/telegram/texts_ideas.py",
            "yuqa/telegram/texts_catalog.py",
            "yuqa/telegram/texts_admin.py",
        ],
        "telegram_ui": [
            "yuqa/telegram/ui.py",
            "yuqa/telegram/ui_navigation.py",
            "yuqa/telegram/ui_battle.py",
            "yuqa/telegram/ui_cards.py",
            "yuqa/telegram/ui_profile.py",
            "yuqa/telegram/ui_catalog.py",
            "yuqa/telegram/ui_rewards.py",
            "yuqa/telegram/ui_ideas.py",
            "yuqa/telegram/ui_admin.py",
        ],
        "telegram_services": [
            "yuqa/telegram/services.py",
            "yuqa/telegram/services_battles.py",
            "yuqa/telegram/services_battle_pass.py",
            "yuqa/telegram/services_players.py",
            "yuqa/telegram/services_social.py",
            "yuqa/telegram/services_content.py",
            "yuqa/telegram/services_support.py",
        ],
        "storage": [
            "yuqa/infrastructure/local.py",
            "yuqa/infrastructure/memory.py",
            "yuqa/infrastructure/sqlalchemy/repositories.py",
            "yuqa/infrastructure/sqlalchemy/models.py",
        ],
        "agent_docs": [
            "AGENTS.md",
            "docs/ai-agents.md",
            "docs/codebase.md",
            "scripts/agent_audit.py",
        ],
        "tests": [
            "tests/test_telegram_layer.py",
            "tests/test_telegram_services.py",
            "tests/test_persistence.py",
        ],
    }


def _change_playbooks() -> dict[str, list[str]]:
    """Return shortest edit paths for the most common task classes."""

    return {
        "runtime_bug": [
            "yuqa/main.py",
            "yuqa/telegram/services.py",
            "yuqa/telegram/services_battles.py",
            "yuqa/telegram/services_battle_pass.py",
            "yuqa/telegram/services_players.py",
            "yuqa/telegram/services_content.py",
            "yuqa/telegram/router.py",
        ],
        "new_domain_rule": [
            "yuqa/<feature>/domain/services.py",
            "yuqa/<feature>/domain/entities.py",
            "tests/test_<feature>.py",
        ],
        "telegram_copy_or_layout": [
            "yuqa/telegram/router_views.py",
            "yuqa/telegram/texts.py",
            "yuqa/telegram/texts_<family>.py",
            "yuqa/telegram/ui.py",
            "yuqa/telegram/ui_<family>.py",
            "tests/test_telegram_layer.py",
        ],
        "fsm_or_handler_flow": [
            "yuqa/telegram/router.py",
            "yuqa/telegram/states.py",
            "tests/test_router_wiring.py",
            "tests/test_telegram_services.py",
        ],
        "persistence_bug": [
            "yuqa/infrastructure/sqlalchemy/repositories.py",
            "yuqa/infrastructure/sqlalchemy/models.py",
            "tests/test_persistence.py",
        ],
    }


def build_summary() -> dict[str, object]:
    """Build a machine-readable architecture snapshot."""

    modules = _iter_python_modules(PACKAGE_ROOT)
    test_modules = _iter_python_modules(TESTS_ROOT)
    hotspots = [
        {
            "path": _path_from_root(module.path),
            "lines": module.lines,
            "functions": module.functions,
            "classes": module.classes,
        }
        for module in modules
        if module.lines >= HOTSPOT_THRESHOLD
    ]
    hotspots.sort(key=lambda item: (-int(item["lines"]), str(item["path"])))
    features = [_feature_summary(name, test_modules) for name in DOMAIN_PACKAGES]
    return {
        "entrypoints": [
            "main.py",
            "yuqa/main.py",
            "yuqa/telegram/router.py",
            "yuqa/telegram/services.py",
        ],
        "commands": {
            "install": "make sync",
            "run": "make run",
            "test": "make test",
            "test_file": "make test-file FILE=tests/test_shop.py",
            "lint": "make lint",
            "format": "make format",
            "agent_summary": "make agent-summary",
            "agent_check": "make agent-check",
        },
        "layers": {
            "domain": "Pure game rules and entities. No Telegram or persistence imports.",
            "telegram": "Bot transport, handlers, texts, UI, callbacks, and config.",
            "infrastructure": "Persistence adapters for in-memory, local catalog, and SQLAlchemy.",
            "shared": "Enums, IDs, errors, and reusable value objects.",
        },
        "runtime_flow": _runtime_flow(),
        "module_groups": _module_groups(),
        "change_playbooks": _change_playbooks(),
        "hotspots": hotspots,
        "features": features,
        "feature_test_gaps": [
            feature["name"]
            for feature in features
            if feature["test_status"] == "missing_direct_tests"
        ],
        "storage_modes": [
            {
                "mode": "memory",
                "trigger": "TelegramServices()",
                "notes": "Fastest for tests and isolated service experiments.",
            },
            {
                "mode": "catalog",
                "trigger": "TelegramServices(content_path=Path(...))",
                "notes": "Loads and persists JSON-backed content without SQLAlchemy.",
            },
            {
                "mode": "database",
                "trigger": "TelegramServices(content_path=..., database_url=...)",
                "notes": "Uses PersistentStateStore and Alembic-managed schema.",
            },
        ],
        "recommended_start_points": {
            "runtime_bootstrap": "yuqa/main.py",
            "telegram_handlers": "yuqa/telegram/router.py",
            "service_orchestration": "yuqa/telegram/services.py",
            "battle_orchestration": "yuqa/telegram/services_battles.py",
            "battle_pass_orchestration": "yuqa/telegram/services_battle_pass.py",
            "player_profile_orchestration": "yuqa/telegram/services_players.py",
            "social_orchestration": "yuqa/telegram/services_social.py",
            "content_admin_orchestration": "yuqa/telegram/services_content.py",
            "telegram_views": "yuqa/telegram/router_views.py",
            "telegram_copy": "yuqa/telegram/texts.py",
            "telegram_markup": "yuqa/telegram/ui.py",
            "router_helpers": "yuqa/telegram/router_helpers.py",
            "local_storage": "yuqa/infrastructure/local.py",
            "database_storage": "yuqa/infrastructure/sqlalchemy/repositories.py",
        },
        "docs": [
            "AGENTS.md",
            _path_from_root(DOCS_ROOT / "ai-agents.md"),
            _path_from_root(DOCS_ROOT / "codebase.md"),
        ],
    }


def check_boundaries() -> list[str]:
    """Return layer violations that make the codebase harder to reason about."""

    errors: list[str] = []
    modules = _iter_python_modules(PACKAGE_ROOT)
    for module in modules:
        owner = _top_level_package(module.module)
        if owner is None:
            continue
        for imported in module.imports:
            target = _top_level_package(imported)
            if target is None or target == owner:
                continue
            if owner in LAYER_GROUPS["shared"] and target.startswith("yuqa."):
                errors.append(
                    f"{module.path.relative_to(ROOT)} imports {imported}; shared must stay dependency-light"
                )
            elif owner in LAYER_GROUPS["domain"] and target in (
                *LAYER_GROUPS["telegram"],
                *LAYER_GROUPS["infrastructure"],
            ):
                errors.append(
                    f"{module.path.relative_to(ROOT)} imports {imported}; domain code must not depend on transport or persistence"
                )
            elif owner in LAYER_GROUPS["application"] and target in LAYER_GROUPS["telegram"]:
                errors.append(
                    f"{module.path.relative_to(ROOT)} imports {imported}; application should remain transport-agnostic"
                )
    return sorted(set(errors))


def main(argv: list[str]) -> int:
    """Run the requested agent-facing command."""

    command = argv[1] if len(argv) > 1 else "summary"
    if command == "summary":
        json.dump(build_summary(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    if command == "check":
        errors = check_boundaries()
        if errors:
            for error in errors:
                print(error)
            return 1
        print("OK: no layer boundary violations found")
        return 0
    print("Usage: agent_audit.py [summary|check]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
