#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class RouteResult:
    status: int
    file: str | None = None
    location: str | None = None


def file_inventory(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }


def parse_redirects(text: str) -> dict[str, tuple[str, int]]:
    rules: dict[str, tuple[str, int]] = {}
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) not in {2, 3}:
            raise ValueError(f"invalid redirect at line {line_number}")
        source, destination = parts[:2]
        status = int(parts[2]) if len(parts) == 3 else 302
        if source in rules:
            raise ValueError(f"duplicate redirect source: {source}")
        rules[source] = (destination, status)
    return rules


def resolve_route(
    root: Path,
    redirects: str,
    request_path: str,
    paths: set[str] | None = None,
) -> RouteResult:
    inventory = paths if paths is not None else file_inventory(root)
    path = urlsplit(request_path).path or "/"
    rules = parse_redirects(redirects)

    if path in rules:
        destination, status = rules[path]
        return RouteResult(status=status, location=destination)

    relative = path.lstrip("/")
    if path == "/" and "index.html" in inventory:
        return RouteResult(status=200, file="index.html")

    if relative.endswith(".html") and relative in inventory:
        if relative == "index.html":
            return RouteResult(status=308, location="/")
        if relative.endswith("/index.html"):
            return RouteResult(status=308, location=f"/{relative[:-10]}")
        return RouteResult(status=308, location=f"/{relative[:-5]}")

    if not path.endswith("/"):
        extensionless = f"{relative}.html"
        if extensionless in inventory:
            return RouteResult(status=200, file=extensionless)
        directory_index = f"{relative}/index.html"
        if directory_index in inventory:
            return RouteResult(status=308, location=f"{path}/")

    if path.endswith("/"):
        directory_index = f"{relative}index.html"
        if directory_index in inventory:
            return RouteResult(status=200, file=directory_index)

    if relative in inventory:
        return RouteResult(status=200, file=relative)

    if "404.html" not in inventory and "index.html" in inventory:
        return RouteResult(status=200, file="index.html")
    return RouteResult(status=404)


def validate_privacy_routes(
    root: Path,
    redirects: str,
    paths: set[str] | None = None,
) -> list[str]:
    expected = {
        "/privacy": RouteResult(status=200, file="privacy.html"),
        "/privacy/": RouteResult(status=301, location="/privacy"),
        "/privacy-policy": RouteResult(status=301, location="/privacy"),
        "/privacy-policy/": RouteResult(status=301, location="/privacy"),
        "/privacy.html": RouteResult(status=308, location="/privacy"),
    }
    errors: list[str] = []
    for path, required in expected.items():
        observed = resolve_route(root, redirects, path, paths)
        if observed != required:
            errors.append(
                f"Cloudflare Pages route mismatch for {path}: "
                f"expected {required}, observed {observed}"
            )
    return errors


def serve(root: Path, host: str, port: int) -> None:
    redirects = (root / "_redirects").read_text(encoding="utf-8")
    paths = file_inventory(root)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            result = resolve_route(root, redirects, self.path, paths)
            if result.location is not None:
                self.send_response(result.status)
                self.send_header("Location", result.location)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if result.file is None:
                self.send_error(result.status)
                return
            body = (root / result.file).read_bytes()
            content_type = mimetypes.guess_type(result.file)[0] or "application/octet-stream"
            if content_type.startswith("text/"):
                content_type = f"{content_type}; charset=utf-8"
            self.send_response(result.status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"serving http://{host}:{server.server_port}", flush=True)
    server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.serve:
        serve(root, args.host, args.port)
        return 0
    redirects = (root / "_redirects").read_text(encoding="utf-8")
    paths = file_inventory(root)
    route_paths = ("/privacy", "/privacy/", "/privacy-policy", "/privacy-policy/", "/privacy.html")
    observations = {
        path: asdict(resolve_route(root, redirects, path, paths))
        for path in route_paths
    }
    errors = validate_privacy_routes(root, redirects, paths)
    print(json.dumps({"routes": observations, "errors": errors}, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
