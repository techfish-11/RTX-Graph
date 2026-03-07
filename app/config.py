from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(slots=True)
class InterfaceConfig:
    if_index: int
    name: str


@dataclass(slots=True)
class RouterConfig:
    name: str
    host: str
    community: str
    version: str
    port: int
    timeout: int
    retries: int
    hc_counters: bool
    interfaces: list[InterfaceConfig]


@dataclass(slots=True)
class AppConfig:
    poll_interval: int
    routers: list[RouterConfig]


class ConfigError(ValueError):
    pass


def _load_interface(item: dict) -> InterfaceConfig:
    if "if_index" not in item:
        raise ConfigError("interface に if_index が必要です")
    return InterfaceConfig(
        if_index=int(item["if_index"]),
        name=str(item.get("name") or f"if{item['if_index']}"),
    )


def _load_router(item: dict) -> RouterConfig:
    for key in ("name", "host", "community"):
        if key not in item:
            raise ConfigError(f"router に {key} が必要です")

    interfaces_raw = item.get("interfaces") or []
    if not interfaces_raw:
        raise ConfigError(f"router={item.get('name')} に interfaces が定義されていません")

    interfaces = [_load_interface(iface) for iface in interfaces_raw]

    return RouterConfig(
        name=str(item["name"]),
        host=str(item["host"]),
        community=str(item["community"]),
        version=str(item.get("version", "2c")),
        port=int(item.get("port", 161)),
        timeout=int(item.get("timeout", 2)),
        retries=int(item.get("retries", 1)),
        hc_counters=bool(item.get("hc_counters", False)),
        interfaces=interfaces,
    )


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as fp:
        raw = yaml.safe_load(fp) or {}

    poll_interval = int(raw.get("poll_interval", 300))
    routers_raw = raw.get("routers") or []

    if not routers_raw:
        raise ConfigError("routers が1件以上必要です")

    routers = [_load_router(router) for router in routers_raw]
    return AppConfig(poll_interval=poll_interval, routers=routers)
