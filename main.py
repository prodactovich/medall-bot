import argparse
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import psycopg
from psycopg.rows import dict_row


def connect():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        dbname=os.getenv("DB_NAME", "contest"),
    )


def parse_dt(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def format_dt(value):
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


class Handler(BaseHTTPRequestHandler):
    def json_response(self, code, data):
        body = json.dumps(data, separators=(",", ":")).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def empty_response(self, code):
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        qs = parse_qs(url.query)

        if url.path == "/ping":
            self.json_response(200, {"status": "ok"})
            return

        if url.path != "/booklist":
            self.empty_response(404)
            return

        try:
            if "user_id" in qs:
                field = "user_id"
                value = int(qs["user_id"][0])
            elif "place_id" in qs:
                field = "place_id"
                value = int(qs["place_id"][0])
            else:
                self.empty_response(400)
                return

            with connect() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(
                        f"""
                        SELECT id, user_id, place_id, time_from, time_to
                        FROM bookings
                        WHERE {field} = %s
                        ORDER BY time_from, id
                        """,
                        (value,),
                    )
                    rows = cur.fetchall()

            self.json_response(
                200,
                {
                    "bookings": [
                        {
                            "id": row["id"],
                            "user_id": row["user_id"],
                            "place_id": row["place_id"],
                            "from": format_dt(row["time_from"]),
                            "to": format_dt(row["time_to"]),
                        }
                        for row in rows
                    ]
                },
            )
        except Exception:
            self.empty_response(400)

    def do_POST(self):
        url = urlparse(self.path)
        qs = parse_qs(url.query)

        if url.path != "/book":
            self.empty_response(404)
            return

        try:
            user_id = int(qs["user_id"][0])
            place_id = int(qs["place_id"][0])
            time_from = parse_dt(qs["from"][0])
            time_to = parse_dt(qs["to"][0])

            if time_from >= time_to:
                self.empty_response(400)
                return

            with connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT 1
                        FROM bookings
                        WHERE place_id = %s
                          AND time_from < %s
                          AND %s < time_to
                        LIMIT 1
                        """,
                        (place_id, time_to, time_from),
                    )
                    if cur.fetchone() is not None:
                        self.empty_response(409)
                        return

                    cur.execute(
                        """
                        INSERT INTO bookings (user_id, place_id, time_from, time_to)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (user_id, place_id, time_from, time_to),
                    )

            self.empty_response(200)
        except Exception:
            self.empty_response(400)

    def log_message(self, *_):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    HTTPServer(("0.0.0.0", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
