from __future__ import annotations

import asyncio
import logging
import time

from .config import AppConfig, InterfaceConfig, RouterConfig
from .models import Database
from .rrd import RRDManager
from .snmp import SNMPError, fetch_interface_counters


class Poller:
    def __init__(self, config: AppConfig, db: Database, rrd_manager: RRDManager) -> None:
        self.config = config
        self.db = db
        self.rrd_manager = rrd_manager
        self.logger = logging.getLogger(self.__class__.__name__)

    async def poll_once(self) -> None:
        tasks = [self._poll_router(router) for router in self.config.routers]
        await asyncio.gather(*tasks)

    async def _poll_router(self, router: RouterConfig) -> None:
        tasks = [self._poll_interface(router, iface) for iface in router.interfaces]
        await asyncio.gather(*tasks)

    async def _poll_interface(self, router: RouterConfig, iface: InterfaceConfig) -> None:
        ts = int(time.time())
        interface_id = self.db.get_interface_id(router.name, iface.if_index)

        # attempt SNMP fetch, handling missing-object case specially
        try:
            in_octets, out_octets = await asyncio.to_thread(
                fetch_interface_counters,
                router.host,
                router.community,
                iface.if_index,
                router.version,
                router.port,
                router.timeout,
                router.retries,
            )
        except SNMPError as exc:
            msg = str(exc)
            if "No Such" in msg:
                self.logger.info(
                    "SNMP missing for %s if%d: %s, assuming zero",
                    router.name,
                    iface.if_index,
                    msg,
                )
                in_octets = 0
                out_octets = 0
            else:
                # log and bail out early
                self.db.log_poll(
                    interface_id=interface_id,
                    ts=ts,
                    status="error",
                    error=msg,
                )
                self.logger.warning(
                    "poll failed %s if%d: %s",
                    router.name,
                    iface.if_index,
                    msg,
                )
                return

        # update RRD and graphs; capture errors separately
        try:
            rrd_path = await asyncio.to_thread(
                self.rrd_manager.ensure_rrd,
                router.name,
                iface.if_index,
            )
            await asyncio.to_thread(
                self.rrd_manager.update,
                rrd_path,
                ts,
                in_octets,
                out_octets,
            )
            await asyncio.to_thread(
                self.rrd_manager.render_graphs,
                router.name,
                iface.if_index,
                iface.name,
            )

            self.db.log_poll(
                interface_id=interface_id,
                ts=ts,
                in_octets=in_octets,
                out_octets=out_octets,
                status="ok",
            )
            self.logger.info(
                "polled %s if%d in=%d out=%d",
                router.name,
                iface.if_index,
                in_octets,
                out_octets,
            )
        except (OSError, RuntimeError) as exc:
            self.db.log_poll(
                interface_id=interface_id,
                ts=ts,
                status="error",
                error=str(exc),
            )
            self.logger.warning(
                "poll failed %s if%d: %s",
                router.name,
                iface.if_index,
                exc,
            )
