from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SOURCES_PATH = DATA_DIR / "sources.json"


@dataclass(slots=True)
class SourceConfig:
    key: str
    name: str
    url: str
    enabled: bool = True
    sort_order: int = 0


@dataclass(slots=True)
class CategoryConfig:
    key: str
    name: str
    enabled: bool = True
    sort_order: int = 0
    sources: list[SourceConfig] | None = None

    def __post_init__(self) -> None:
        if self.sources is None:
            self.sources = []


def get_sources_path(path: str | Path | None = None) -> Path:
    return Path(path) if path else SOURCES_PATH


def load_source_registry(path: str | Path | None = None) -> list[CategoryConfig]:
    sources_path = get_sources_path(path)
    data = json.loads(sources_path.read_text(encoding="utf-8"))
    return parse_source_registry(data)


def parse_source_registry(data: dict[str, Any]) -> list[CategoryConfig]:
    categories_raw = data.get("categories")
    if not isinstance(categories_raw, list):
        raise ValueError("sources.json must contain a top-level 'categories' list")

    categories: list[CategoryConfig] = []
    seen_category_keys: set[str] = set()
    seen_source_keys: set[str] = set()

    for index, category_raw in enumerate(categories_raw):
        if not isinstance(category_raw, dict):
            raise ValueError(f"categories[{index}] must be an object")

        category_key = _require_text(category_raw, "key", f"categories[{index}]")
        category_name = _require_text(category_raw, "name", f"categories[{index}]")
        if category_key in seen_category_keys:
            raise ValueError(f"duplicate category key: {category_key}")
        seen_category_keys.add(category_key)

        sources_raw = category_raw.get("sources")
        if not isinstance(sources_raw, list):
            raise ValueError(f"categories[{index}].sources must be a list")

        sources: list[SourceConfig] = []
        for source_index, source_raw in enumerate(sources_raw):
            if not isinstance(source_raw, dict):
                raise ValueError(f"categories[{index}].sources[{source_index}] must be an object")

            source_key = _require_text(source_raw, "key", f"categories[{index}].sources[{source_index}]")
            source_name = _require_text(source_raw, "name", f"categories[{index}].sources[{source_index}]")
            source_url = _require_text(source_raw, "url", f"categories[{index}].sources[{source_index}]")
            if source_key in seen_source_keys:
                raise ValueError(f"duplicate source key: {source_key}")
            seen_source_keys.add(source_key)

            sources.append(
                SourceConfig(
                    key=source_key,
                    name=source_name,
                    url=source_url,
                    enabled=bool(source_raw.get("enabled", True)),
                    sort_order=int(source_raw.get("order", source_raw.get("sort_order", 0)) or 0),
                )
            )

        categories.append(
            CategoryConfig(
                key=category_key,
                name=category_name,
                enabled=bool(category_raw.get("enabled", True)),
                sort_order=int(category_raw.get("order", category_raw.get("sort_order", 0)) or 0),
                sources=sources,
            )
        )

    return categories


def build_category_lookup(categories: list[CategoryConfig]) -> dict[str, CategoryConfig]:
    return {category.key: category for category in categories}


def list_category_keys(categories: list[CategoryConfig]) -> list[str]:
    return [category.key for category in categories]


def _require_text(obj: dict[str, Any], key: str, label: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}.{key} must be a non-empty string")
    return value.strip()
