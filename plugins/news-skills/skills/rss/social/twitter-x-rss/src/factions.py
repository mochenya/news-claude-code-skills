from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from models import normalize_username


def _normalize_accounts(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("Faction group accounts must be a list")
    accounts: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise ValueError("Faction account names must be strings")
        username = normalize_username(item)
        if not username:
            raise ValueError("Faction account names cannot be empty")
        if username not in seen:
            seen.add(username)
            accounts.append(username)
    return accounts


@dataclass(frozen=True, slots=True)
class Faction:
    name: str
    groups: dict[str, list[str]]

    @property
    def accounts(self) -> list[str]:
        return list(dict.fromkeys(account for accounts in self.groups.values() for account in accounts))


class FactionConfig:
    def __init__(self, factions: dict[str, Faction]):
        self._factions = factions

    @classmethod
    def load(cls, path: str | Path) -> "FactionConfig":
        config_path = Path(path)
        if not config_path.exists():
            raise ValueError(f"Factions file not found: {config_path}")
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid factions JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("Invalid factions JSON: root must be an object")

        factions: dict[str, Faction] = {}
        for raw_name, value in payload.items():
            name = str(raw_name).strip()
            if not name:
                raise ValueError("Faction names cannot be empty")
            groups = cls._parse_groups(name, value)
            factions[name] = Faction(name=name, groups=groups)
        return cls(factions)

    @staticmethod
    def _parse_groups(name: str, value: Any) -> dict[str, list[str]]:
        if not isinstance(value, dict):
            raise ValueError(f"Invalid faction entry for '{name}'")
        extra_fields = set(value) - {"groups"}
        if extra_fields:
            raise ValueError(f"Faction '{name}' has unsupported fields: {', '.join(sorted(extra_fields))}")

        raw_groups = value.get("groups")
        if not isinstance(raw_groups, dict):
            raise ValueError(f"Faction '{name}' must define a groups object")
        groups: dict[str, list[str]] = {}
        assigned_accounts: set[str] = set()
        for raw_group, raw_accounts in raw_groups.items():
            group = str(raw_group).strip()
            if not group:
                raise ValueError(f"Faction '{name}' contains an empty group name")
            accounts = _normalize_accounts(raw_accounts)
            duplicated = assigned_accounts.intersection(accounts)
            if duplicated:
                raise ValueError(
                    f"Faction '{name}' assigns accounts to multiple groups: {', '.join(sorted(duplicated))}"
                )
            groups[group] = accounts
            assigned_accounts.update(accounts)
        return groups

    def get(self, name: str) -> Faction:
        requested = name.strip().lower()
        for faction_name, faction in self._factions.items():
            if faction_name.lower() == requested:
                return faction
        raise ValueError(f"Faction not found: {name}")
