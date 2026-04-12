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


@dataclass(slots=True)
class PythonModule:
    """Minimal static metadata for one Python module."""

    path: Path
    module: str
    imports: set[str]
    lines: int


def _module_name(path: Path) -> str:
    relative = path.relative_to(ROOT).with_suffix("")
    return ".".join(relative.parts)


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
    return PythonModule(
        path=path,
        module=_module_name(path),
        imports=imports,
        lines=source.count("\n") + 1,
    )


def _iter_python_modules(root: Path) -> list[PythonModule]:
    return [_read_python_module(path) for path in sorted(root.rglob("*.py"))]


def _feature_summary(name: str) -> dict[str, object]:
    base = PACKAGE_ROOT / name
    domain_dir = base / "domain"
    files = sorted(path.relative_to(ROOT).as_posix() for path in base.rglob("*.py"))
    tests = sorted(
        path.relative_to(ROOT).as_posix()
        for path in TESTS_ROOT.glob(f"test*{name.replace('_', '')}*.py")
    )
    return {
        "name": name,
        "domain_modules": sorted(
            path.name for path in domain_dir.glob("*.py") if path.is_file()
        ),
        "files": files,
        "tests": tests,
    }


def build_summary() -> dict[str, object]:
    """Build a machine-readable architecture snapshot."""

    modules = _iter_python_modules(PACKAGE_ROOT)
    hotspots = [
        {
            "path": module.path.relative_to(ROOT).as_posix(),
            "lines": module.lines,
        }
        for module in modules
        if module.lines >= HOTSPOT_THRESHOLD
    ]
    hotspots.sort(key=lambda item: (-int(item["lines"]), str(item["path"])))
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
        "hotspots": hotspots,
        "features": [_feature_summary(name) for name in DOMAIN_PACKAGES],
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
            "local_storage": "yuqa/infrastructure/local.py",
            "database_storage": "yuqa/infrastructure/sqlalchemy/repositories.py",
        },
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
