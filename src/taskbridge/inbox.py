"""Cross-tool inbox scanning for the unified inbox report (ADR-002)."""

import time
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .config import config as default_config

# Module names gated by profile (ADR-003). Extended as adapters land.
INBOX_MODULES = ("obsidian_inbox",)


@dataclass
class InboxItem:
    """A single unprocessed item surfaced by an inbox scanner."""

    label: str
    path: str
    age_days: float
    uri: str


def scan_obsidian_folders(
    configs: list[dict[str, str]], config_manager: Config | None = None
) -> list[InboxItem]:
    """Scan configured vault folders for unprocessed markdown notes.

    Each config is a {label, path} dict where path is relative to the vault root
    (e.g. "00 Inbox", "30 Resources/37 Literature"). A folder that doesn't exist
    or isn't a directory yields no items for that entry rather than raising -
    one misconfigured source shouldn't break the whole scan.
    """
    config_manager = config_manager or default_config
    vault_path = config_manager.get_obsidian_vault_path()
    if not vault_path:
        return []
    vault_path = Path(vault_path)

    items: list[InboxItem] = []
    for entry in configs:
        items.extend(_scan_folder(config_manager, vault_path, entry["label"], entry["path"]))
    return items


def _scan_folder(
    config_manager: Config, vault_path: Path, label: str, relative_path: str
) -> list[InboxItem]:
    folder = vault_path / relative_path
    if not folder.is_dir():
        return []

    now = time.time()
    items = []
    for md_file in sorted(folder.glob("*.md")):
        age_days = (now - md_file.stat().st_mtime) / 86400
        file_relative = f"{relative_path}/{md_file.name}"
        uri = config_manager.generate_obsidian_file_url(file_relative)
        items.append(InboxItem(label=label, path=str(md_file), age_days=age_days, uri=uri))
    return items


def enabled_modules(config_manager: Config | None = None, profile: str | None = None) -> list[str]:
    """List inbox modules enabled for the active profile, in a stable order."""
    config_manager = config_manager or default_config
    return [m for m in INBOX_MODULES if config_manager.is_module_enabled(m, profile=profile)]


def scan_all(config_manager: Config | None = None, profile: str | None = None) -> list[InboxItem]:
    """Aggregate items from every scanner enabled for the active profile."""
    config_manager = config_manager or default_config
    active_modules = enabled_modules(config_manager, profile)

    items: list[InboxItem] = []
    if "obsidian_inbox" in active_modules:
        items.extend(scan_obsidian_folders(config_manager.get_inbox_folders(), config_manager))
    return items


def group_by_label(items: list[InboxItem]) -> list[tuple[str, int, float]]:
    """Group items by label, returning (label, count, oldest_age_days) sorted by label."""
    groups: dict[str, list[InboxItem]] = {}
    for item in items:
        groups.setdefault(item.label, []).append(item)

    return [
        (label, len(group), max(i.age_days for i in group))
        for label, group in sorted(groups.items())
    ]
