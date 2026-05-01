#!/usr/bin/env python3
"""Emit a compact repository map and validate layer boundaries."""

import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "src"
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
    "domain": {f"src.{name}" for name in DOMAIN_PACKAGES},
    "telegram": {"src.telegram"},
    "infrastructure": {"src.infrastructure"},
    "shared": {"src.shared"},
    "application": {"src.application"},
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


def _telegram_package_paths(
    package: str,
    *modules: str,
    include_surface: bool = False,
) -> list[str]:
    """Return package-relative Telegram module paths."""

    paths = [f"src/telegram/{package}/__init__.py"] if include_surface else []
    paths.extend(f"src/telegram/{package}/{module}.py" for module in modules)
    return paths


TELEGRAM_ROUTER_SURFACE = "src/telegram/router/__init__.py"
TELEGRAM_ROUTER_ENTRY = "src/telegram/router/router.py"
TELEGRAM_ROUTER_PUBLIC = "src/telegram/router/public.py"
TELEGRAM_ROUTER_ADMIN = "src/telegram/router/admin.py"
TELEGRAM_ROUTER_VIEWS = "src/telegram/router/views.py"
TELEGRAM_ROUTER_HELPERS = "src/telegram/router/helpers.py"
TELEGRAM_SERVICES_SURFACE = "src/telegram/services/__init__.py"
TELEGRAM_SERVICES_ENTRY = "src/telegram/services/services.py"
TELEGRAM_SERVICES_CONTRACTS = "src/telegram/services/contracts.py"
TELEGRAM_TEXTS_SURFACE = "src/telegram/texts/__init__.py"
TELEGRAM_TEXTS_ENTRY = "src/telegram/texts/texts.py"
TELEGRAM_UI_SURFACE = "src/telegram/ui/__init__.py"
TELEGRAM_UI_ENTRY = "src/telegram/ui/ui.py"
TELEGRAM_ROUTER_GROUP = _telegram_package_paths(
    "router",
    "router",
    "public",
    "admin",
    include_surface=True,
)
TELEGRAM_WIZARD_GROUP = _telegram_package_paths(
    "router",
    "wizards_players",
    "wizards_progression",
    "wizards_content",
    "wizards_cards",
    "wizards_banners",
    "wizards_shop",
    "battle",
)
TELEGRAM_TEXTS_GROUP = _telegram_package_paths(
    "texts",
    "texts",
    "navigation",
    "battle",
    "battle_pass",
    "profile",
    "cards",
    "rewards",
    "ideas",
    "catalog",
    "admin",
    include_surface=True,
)
TELEGRAM_UI_GROUP = _telegram_package_paths(
    "ui",
    "ui",
    "navigation",
    "battle",
    "cards",
    "profile",
    "catalog",
    "rewards",
    "ideas",
    "admin",
    include_surface=True,
)
TELEGRAM_SERVICES_GROUP = _telegram_package_paths(
    "services",
    "services",
    "contracts",
    "battles",
    "battle_pass",
    "players",
    "social",
    "content",
    "quests",
    "support",
    include_surface=True,
)


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
    if len(parts) < 2 or parts[0] != "src":
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
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for node in ast.walk(tree)
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

    prefix = f"src.{name}"
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
        {
            "path": "main.py",
            "role": "CLI shim that forwards into the package entrypoint.",
        },
        {
            "path": "src/main.py",
            "role": "Loads env settings, runs migrations, builds services, and starts polling.",
        },
        {
            "path": TELEGRAM_SERVICES_SURFACE,
            "role": "Stable import surface for the Telegram service container.",
        },
        {
            "path": TELEGRAM_SERVICES_ENTRY,
            "role": "Builds repositories, selects storage mode, and hosts shared service helpers.",
        },
        {
            "path": TELEGRAM_SERVICES_CONTRACTS,
            "role": "Defines type-only service contracts for mixin dependencies and IDE completion.",
        },
        {
            "path": "src/telegram/services/battles.py",
            "role": "Owns battle drafting, round resolution, and matchmaking behavior.",
        },
        {
            "path": "src/telegram/services/battle_pass.py",
            "role": "Owns battle pass seasons, levels, and progress purchasing.",
        },
        {
            "path": "src/telegram/services/players.py",
            "role": "Owns player lookup, profile, free rewards, and deck construction.",
        },
        {
            "path": "src/telegram/services/social.py",
            "role": "Owns clan membership and idea proposal/moderation flows.",
        },
        {
            "path": "src/telegram/services/content.py",
            "role": "Owns card, banner, shop, starter-card, and admin content flows.",
        },
        {
            "path": "src/telegram/services/quests.py",
            "role": "Owns cooldown-aware quest completion for player actions.",
        },
        {
            "path": "src/telegram/services/support.py",
            "role": "Holds small shared service dataclasses and utility helpers.",
        },
        {
            "path": TELEGRAM_ROUTER_SURFACE,
            "role": "Stable import surface for the Telegram router package.",
        },
        {
            "path": TELEGRAM_ROUTER_ENTRY,
            "role": "Thin compatibility surface that builds the router from public/admin registration modules.",
        },
        {
            "path": TELEGRAM_ROUTER_PUBLIC,
            "role": "Registers public commands, callbacks, and non-admin wizard state handlers.",
        },
        {
            "path": TELEGRAM_ROUTER_ADMIN,
            "role": "Registers admin commands, AdminCallback flows, and admin-only wizard state handlers.",
        },
        {
            "path": "src/telegram/router/wizards_players.py",
            "role": "Owns clan, idea, profile nickname, and admin player wizard steps.",
        },
        {
            "path": "src/telegram/router/wizards_progression.py",
            "role": "Owns battle pass and free-reward wizard steps.",
        },
        {
            "path": "src/telegram/router/wizards_content.py",
            "role": "Thin compatibility facade that re-exports the content wizard families.",
        },
        {
            "path": "src/telegram/router/wizards_cards.py",
            "role": "Owns universe, card, profile background, and starter-card wizard steps.",
        },
        {
            "path": "src/telegram/router/wizards_banners.py",
            "role": "Owns banner creation and banner-reward wizard steps.",
        },
        {
            "path": "src/telegram/router/wizards_shop.py",
            "role": "Owns shop item wizard steps.",
        },
        {
            "path": "src/telegram/router/battle.py",
            "role": "Owns shared battle command and matchmaking entry helpers.",
        },
        {
            "path": TELEGRAM_ROUTER_VIEWS,
            "role": "Renders Telegram screens and admin sections reused by handlers.",
        },
        {
            "path": TELEGRAM_ROUTER_HELPERS,
            "role": "Holds parsing, pagination, and media extraction helpers for router flows.",
        },
    ]


def _module_groups() -> dict[str, list[str]]:
    """Return grouped edit paths for common tasks."""

    return {
        "runtime_bootstrap": ["main.py", "src/main.py", "src/telegram/config.py"],
        "telegram_flow": [
            *TELEGRAM_ROUTER_GROUP,
            "src/telegram/states.py",
            "src/telegram/callbacks.py",
        ],
        "telegram_wizards": TELEGRAM_WIZARD_GROUP,
        "telegram_views": [
            TELEGRAM_ROUTER_VIEWS,
            TELEGRAM_TEXTS_SURFACE,
            TELEGRAM_TEXTS_ENTRY,
            TELEGRAM_UI_SURFACE,
            TELEGRAM_UI_ENTRY,
            "src/telegram/reply.py",
        ],
        "telegram_texts": TELEGRAM_TEXTS_GROUP,
        "telegram_ui": TELEGRAM_UI_GROUP,
        "telegram_services": TELEGRAM_SERVICES_GROUP,
        "storage": [
            "src/infrastructure/local.py",
            "src/infrastructure/sqlalchemy/repositories.py",
            "src/infrastructure/sqlalchemy/models.py",
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
            "src/main.py",
            TELEGRAM_SERVICES_SURFACE,
            TELEGRAM_SERVICES_ENTRY,
            TELEGRAM_SERVICES_CONTRACTS,
            TELEGRAM_ROUTER_SURFACE,
            TELEGRAM_ROUTER_ENTRY,
            TELEGRAM_ROUTER_PUBLIC,
            TELEGRAM_ROUTER_ADMIN,
            TELEGRAM_ROUTER_VIEWS,
        ],
        "new_domain_rule": [
            "src/<feature>/domain/services.py",
            "src/<feature>/domain/entities.py",
            "tests/test_<feature>.py",
        ],
        "telegram_copy_or_layout": [
            TELEGRAM_ROUTER_VIEWS,
            TELEGRAM_TEXTS_SURFACE,
            TELEGRAM_TEXTS_ENTRY,
            "src/telegram/texts/<family>.py",
            TELEGRAM_UI_SURFACE,
            TELEGRAM_UI_ENTRY,
            "src/telegram/ui/<family>.py",
            "tests/test_telegram_layer.py",
        ],
        "fsm_or_handler_flow": [
            TELEGRAM_ROUTER_SURFACE,
            TELEGRAM_ROUTER_ENTRY,
            TELEGRAM_ROUTER_PUBLIC,
            TELEGRAM_ROUTER_ADMIN,
            "src/telegram/router/wizards_<family>.py",
            "src/telegram/states.py",
            "tests/test_router_wiring.py",
            "tests/test_telegram_services.py",
        ],
        "persistence_bug": [
            "src/infrastructure/sqlalchemy/repositories.py",
            "src/infrastructure/sqlalchemy/models.py",
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
            "src/main.py",
            TELEGRAM_ROUTER_SURFACE,
            TELEGRAM_SERVICES_SURFACE,
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
            "infrastructure": "Persistence adapters for local catalog and SQLAlchemy.",
            "shared": "Enums, IDs, errors, and reusable value objects.",
        },
        "public_surfaces": {
            "router": {
                "import": "src.telegram.router",
                "path": TELEGRAM_ROUTER_SURFACE,
                "implementation": TELEGRAM_ROUTER_ENTRY,
            },
            "services": {
                "import": "src.telegram.services",
                "path": TELEGRAM_SERVICES_SURFACE,
                "implementation": TELEGRAM_SERVICES_ENTRY,
            },
            "texts": {
                "import": "src.telegram.texts",
                "path": TELEGRAM_TEXTS_SURFACE,
                "implementation": TELEGRAM_TEXTS_ENTRY,
            },
            "ui": {
                "import": "src.telegram.ui",
                "path": TELEGRAM_UI_SURFACE,
                "implementation": TELEGRAM_UI_ENTRY,
            },
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
                "mode": "temporary_sqlite",
                "trigger": "TelegramServices()",
                "notes": "Uses an isolated temporary SQLite document store.",
            },
            {
                "mode": "catalog",
                "trigger": "TelegramServices(content_path=Path(...))",
                "notes": "Loads JSON-backed content and uses temporary SQLite for runtime state.",
            },
            {
                "mode": "database",
                "trigger": "TelegramServices(content_path=..., database_url=...)",
                "notes": "Uses PersistentStateStore and Alembic-managed schema.",
            },
        ],
        "recommended_start_points": {
            "runtime_bootstrap": "src/main.py",
            "telegram_router_surface": TELEGRAM_ROUTER_SURFACE,
            "telegram_services_surface": TELEGRAM_SERVICES_SURFACE,
            "telegram_texts_surface": TELEGRAM_TEXTS_SURFACE,
            "telegram_ui_surface": TELEGRAM_UI_SURFACE,
            "telegram_handlers": TELEGRAM_ROUTER_ENTRY,
            "telegram_public_handlers": TELEGRAM_ROUTER_PUBLIC,
            "telegram_admin_handlers": TELEGRAM_ROUTER_ADMIN,
            "service_orchestration": TELEGRAM_SERVICES_ENTRY,
            "service_contracts": TELEGRAM_SERVICES_CONTRACTS,
            "battle_orchestration": "src/telegram/services/battles.py",
            "battle_pass_orchestration": "src/telegram/services/battle_pass.py",
            "player_profile_orchestration": "src/telegram/services/players.py",
            "social_orchestration": "src/telegram/services/social.py",
            "content_admin_orchestration": "src/telegram/services/content.py",
            "quest_orchestration": "src/telegram/services/quests.py",
            "telegram_views": TELEGRAM_ROUTER_VIEWS,
            "telegram_copy": TELEGRAM_TEXTS_ENTRY,
            "telegram_markup": TELEGRAM_UI_ENTRY,
            "router_helpers": TELEGRAM_ROUTER_HELPERS,
            "local_storage": "src/infrastructure/local.py",
            "database_storage": "src/infrastructure/sqlalchemy/repositories.py",
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
            if owner in LAYER_GROUPS["shared"] and target.startswith("src."):
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
            elif (
                owner in LAYER_GROUPS["application"]
                and target in LAYER_GROUPS["telegram"]
            ):
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
