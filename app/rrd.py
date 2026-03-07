from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from .utils import graph_absolute_paths, slugify


class RRDToolError(RuntimeError):
    pass


class RRDManager:
    def __init__(self, rrd_root: str | Path, graph_root: str | Path, step: int) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.rrd_root = Path(rrd_root)
        self.graph_root = Path(graph_root)
        self.step = step
        self.heartbeat = max(step * 2, 600)
        self.rrd_root.mkdir(parents=True, exist_ok=True)
        self.graph_root.mkdir(parents=True, exist_ok=True)

    def _run_rrdtool(self, args: list[str]) -> None:
        cmd = ["rrdtool", *args]
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RRDToolError(proc.stderr.strip() or proc.stdout.strip() or "rrdtool command failed")

    def ensure_rrd(self, router_name: str, if_index: int) -> Path:
        router_slug = slugify(router_name)
        router_dir = self.rrd_root / router_slug
        router_dir.mkdir(parents=True, exist_ok=True)
        rrd_path = router_dir / f"if{if_index}.rrd"

        if rrd_path.exists():
            return rrd_path

        self._run_rrdtool(
            [
                "create",
                str(rrd_path),
                "--step",
                str(self.step),
                f"DS:in:COUNTER:{self.heartbeat}:0:U",
                f"DS:out:COUNTER:{self.heartbeat}:0:U",
                "RRA:AVERAGE:0.5:1:2880",
                "RRA:MIN:0.5:1:2880",
                "RRA:MAX:0.5:1:2880",
                "RRA:AVERAGE:0.5:12:8760",
                "RRA:MIN:0.5:12:8760",
                "RRA:MAX:0.5:12:8760",
            ]
        )
        self.logger.info("created rrd: %s", rrd_path)
        return rrd_path

    def update(self, rrd_path: Path, ts: int, in_octets: int, out_octets: int) -> None:
        self._run_rrdtool([
            "update",
            str(rrd_path),
            f"{ts}:{in_octets}:{out_octets}",
        ])

    def render_graphs(self, router_name: str, if_index: int, iface_name: str) -> dict[str, Path]:
        periods = {
            "1day": "-1d",
            "1week": "-1w",
            "1month": "-1m",
        }

        rrd_path = self.ensure_rrd(router_name, if_index)
        graph_paths = graph_absolute_paths(self.graph_root, router_name, if_index)

        for label, start in periods.items():
            output = graph_paths[label]
            output.parent.mkdir(parents=True, exist_ok=True)
            self._run_rrdtool(
                [
                    "graph",
                    str(output),
                    "--start",
                    start,
                    "--end",
                    "now",
                    "--imgformat",
                    "PNG",
                    "--width",
                    "760",
                    "--height",
                    "220",
                    "--slope-mode",
                    "--lower-limit",
                    "0",
                    "--title",
                    f"{router_name} :: {iface_name} ({label})",
                    "--vertical-label",
                    "bits per second",
                    "--color",
                    "BACK#E6E6E6",
                    "--color",
                    "CANVAS#F2F2F2",
                    "--color",
                    "GRID#BBBBBB",
                    "--color",
                    "MGRID#888888",
                    f"DEF:inOct={rrd_path}:in:AVERAGE",
                    f"DEF:outOct={rrd_path}:out:AVERAGE",
                    "CDEF:inBits=inOct,8,*",
                    "CDEF:outBits=outOct,8,*",
                    "VDEF:inAvg=inBits,AVERAGE",
                    "VDEF:inMin=inBits,MINIMUM",
                    "VDEF:inMax=inBits,MAXIMUM",
                    "VDEF:outAvg=outBits,AVERAGE",
                    "VDEF:outMin=outBits,MINIMUM",
                    "VDEF:outMax=outBits,MAXIMUM",
                    "CDEF:inOctDay=inOct,86400,*",
                    "CDEF:outOctDay=outOct,86400,*",
                    "VDEF:inDailyTotal=inOctDay,AVERAGE",
                    "VDEF:outDailyTotal=outOctDay,AVERAGE",
                    "AREA:inBits#00B000:Incoming",
                    "LINE2:outBits#7F3FBF:Outgoing",
                    "COMMENT: \\n",
                    "COMMENT:            Avg         Min         Max         Daily Total\\l",
                    "GPRINT:inAvg: In  %8.2lf%s",
                    "GPRINT:inMin:%12.2lf%s",
                    "GPRINT:inMax:%12.2lf%s",
                    "GPRINT:inDailyTotal:%12.2lf%sB\\l",
                    "GPRINT:outAvg: Out %8.2lf%s",
                    "GPRINT:outMin:%12.2lf%s",
                    "GPRINT:outMax:%12.2lf%s",
                    "GPRINT:outDailyTotal:%12.2lf%sB\\l",
                ]
            )

        return graph_paths
