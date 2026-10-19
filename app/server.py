import json
import os
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

VERSION = os.environ["APP_VERSION"]
STUDENT = os.environ["STUDENT_ID"]
POD = socket.gethostname()
STARTED = time.monotonic()
FEATURE_PINNED = os.getenv("FEATURE_PINNED", "false") == "true"

NOTICES = [
    {
        "id": 1,
        "title": "Library opening hours",
        "category": "Academic",
        "pinned": False,
    },
    {
        "id": 2,
        "title": "Examination timetable published",
        "category": "Examinations",
        "pinned": True,
    },
    {
        "id": 3,
        "title": "Campus sports registration",
        "category": "Events",
        "pinned": False,
    },
]


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path

        if path == "/version":
            self.send_json(200, {
                "version": VERSION,
                "student": STUDENT,
                "pod": POD,
            })

        elif path == "/healthz":
            uptime = time.monotonic() - STARTED
            healthy = (
                uptime >= 5
                and VERSION != "1.2.0-broken"
            )

            self.send_json(200 if healthy else 503, {
                "healthy": healthy,
                "uptimeSeconds": round(uptime, 3),
                "student": STUDENT,
                "version": VERSION,
            })

        elif path == "/notices":
            if VERSION == "1.0.0":
                notices = [
                    {"id": item["id"], "title": item["title"]}
                    for item in NOTICES
                ]
                self.send_json(200, {"notices": notices})
            else:
                notices = [dict(item) for item in NOTICES]

                if FEATURE_PINNED:
                    notices.sort(key=lambda item: not item["pinned"])

                self.send_json(200, {
                    "notices": notices,
                    "pinnedFirst": FEATURE_PINNED,
                })

        else:
            self.send_json(404, {"error": "Not found"})

    def log_message(self, format, *args):
        print(
            f"{self.log_date_time_string()} "
            f"{self.client_address[0]} {format % args}",
            flush=True,
        )


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    print(
        f"Notice Board {VERSION}, student {STUDENT}, port 8080",
        flush=True,
    )
    server.serve_forever()