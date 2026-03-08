from __future__ import annotations

import asyncio
import logging
import os
import threading
from pathlib import Path

from .config import load_config
from .logging_setup import setup_logging
from .models import Database
from .poller import Poller
from .rrd import RRDManager
from .scheduler import PollScheduler
from .web import create_app


def main() -> None:
    setup_logging()
    logger = logging.getLogger("main")

    config_path = os.getenv("CONFIG_PATH", "config.yaml")
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    web_port = int(os.getenv("WEB_PORT", "8080"))
    web_user = os.getenv("WEB_USERNAME", "admin")
    web_password = os.getenv("WEB_PASSWORD", "changeme")
    refresh_seconds = int(os.getenv("WEB_REFRESH_SECONDS", "300"))

    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "traffic.db"
    rrd_root = data_dir / "rrd"
    graph_root = data_dir / "graphs"

    config = load_config(config_path)

    db = Database(db_path)
    db.init_schema()
    db.sync_from_config(config)

    rrd_manager = RRDManager(rrd_root=rrd_root, graph_root=graph_root, step=config.poll_interval)
    poller = Poller(config=config, db=db, rrd_manager=rrd_manager)
    scheduler = PollScheduler(poller=poller, interval=config.poll_interval)

    loop_thread = threading.Thread(
        target=lambda: asyncio.run(scheduler.run_forever()),
        daemon=True,
        name="poll-scheduler",
    )
    loop_thread.start()

    app = create_app(
        db=db,
        graph_root=graph_root,
        username=web_user,
        password=web_password,
        refresh_seconds=refresh_seconds,
        public_graphs=config.public_graphs,
    )

    logger.info("web server starting on 0.0.0.0:%s", web_port)
    app.run(host="0.0.0.0", port=web_port)


if __name__ == "__main__":
    main()
