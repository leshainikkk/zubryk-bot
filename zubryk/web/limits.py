import threading
import time
from collections import OrderedDict, deque

from flask import jsonify, request


class RateLimiter:
    def __init__(self):
        self.entries = OrderedDict()
        self.lock = threading.Lock()

    def check(self):
        if not request.path.startswith("/api/") or request.method == "OPTIONS":
            return
        ip = request.remote_addr
        if ip in ("127.0.0.1", "::1"):
            ip = request.headers.get("CF-Connecting-IP", ip)
        key = (ip, "write" if request.method != "GET" else "read")
        now=time.monotonic()
        limit=60 if key[1]=="write" else 240
        with self.lock:
            bucket=self.entries.setdefault(key,deque())
            self.entries.move_to_end(key)
            while bucket and bucket[0] < now-60:
                bucket.popleft()
            if len(bucket)>=limit:
                return jsonify(error="rate_limited", message="Немного подождите и повторите"),429,{"Retry-After":"60"}
            bucket.append(now)
            while len(self.entries)>4096:
                self.entries.popitem(last=False)
