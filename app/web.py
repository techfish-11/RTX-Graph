from __future__ import annotations

import secrets
import time
from functools import wraps
from pathlib import Path
from typing import Callable

from flask import Flask, Response, abort, render_template, request, send_from_directory

from .models import Database
from .utils import graph_relative_paths


def create_app(
    db: Database,
    graph_root: str | Path,
    username: str,
    password: str,
    refresh_seconds: int = 300,
) -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    graph_root_path = Path(graph_root)

    def _unauthorized() -> Response:
        return Response(
            "Authentication required",
            401,
            {"WWW-Authenticate": 'Basic realm="RTX Graph"'},
        )

    def requires_basic_auth(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            auth = request.authorization
            if not auth:
                return _unauthorized()

            user_ok = secrets.compare_digest(auth.username or "", username)
            pass_ok = secrets.compare_digest(auth.password or "", password)
            if not (user_ok and pass_ok):
                return _unauthorized()

            return func(*args, **kwargs)

        return wrapper

    @app.route("/")
    @requires_basic_auth
    def index():
        routers = db.get_routers()
        return render_template("index.html", routers=routers, refresh_seconds=refresh_seconds)

    @app.route("/router/<int:router_id>")
    @requires_basic_auth
    def router_view(router_id: int):
        router = db.get_router(router_id)
        if not router:
            abort(404)
        interfaces = db.get_interfaces(router_id)
        return render_template(
            "router.html",
            router=router,
            interfaces=interfaces,
            refresh_seconds=refresh_seconds,
        )

    @app.route("/router/<int:router_id>/interface/<int:interface_id>")
    @requires_basic_auth
    def interface_view(router_id: int, interface_id: int):
        router = db.get_router(router_id)
        interface = db.get_interface(router_id, interface_id)
        if not router or not interface:
            abort(404)

        graphs = graph_relative_paths(router["name"], interface["if_index"])
        return render_template(
            "interface.html",
            router=router,
            interface=interface,
            graphs=graphs,
            refresh_seconds=refresh_seconds,
            refresh_nonce=int(time.time()),
        )

    @app.route("/graphs/<path:filename>")
    @requires_basic_auth
    def graph_image(filename: str):
        file_path = graph_root_path / filename
        if not file_path.exists() or not file_path.is_file():
            abort(404)
        return send_from_directory(graph_root_path, filename)

    return app
