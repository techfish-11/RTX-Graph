from __future__ import annotations

import re
from pathlib import Path


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    slug = slug.strip("-")
    return slug.lower() or "unknown"


def graph_relative_paths(router_name: str, if_index: int) -> dict[str, str]:
    router_slug = slugify(router_name)
    interface_dir = f"if{if_index}"
    return {
        "1day": f"{router_slug}/{interface_dir}/traffic_1day.png",
        "1week": f"{router_slug}/{interface_dir}/traffic_1week.png",
        "1month": f"{router_slug}/{interface_dir}/traffic_1month.png",
    }


def graph_absolute_paths(graph_root: Path, router_name: str, if_index: int) -> dict[str, Path]:
    rel_paths = graph_relative_paths(router_name, if_index)
    return {key: graph_root / rel for key, rel in rel_paths.items()}
