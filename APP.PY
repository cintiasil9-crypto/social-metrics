from flask import Flask, Response
import requests
import time
import os
import json
import re

app = Flask(__name__)
GOOGLE_FEED = os.environ["GOOGLE_PROFILES_FEED"]

def fetch_rows():
    r = requests.get(GOOGLE_FEED, timeout=20)
    m = re.search(r"setResponse\((\{.*\})\)", r.text, re.S)
    payload = json.loads(m.group(1))

    cols = [c["label"] for c in payload["table"]["cols"]]
    rows = []

    for row in payload["table"]["rows"]:
        rec = {}
        for i, cell in enumerate(row["c"]):
            rec[cols[i]] = cell["v"] if cell else 0
        rows.append(rec)

    return rows

def calculate_metrics():

    rows = fetch_rows()
    now = time.time()

    total = set()
    spoke_24 = set()
    live = set()

    for r in rows:
        uid = r.get("avatar_uuid")
        if not uid:
            continue

        total.add(uid)

        ts = float(r.get("timestamp", now))
        msgs = int(r.get("messages", 0))
        age = now - ts

        if age <= 86400 and msgs > 0:
            spoke_24.add(uid)

        if age <= 60 and msgs > 0:
            live.add(uid)

    return {
        "total_registered": len(total),
        "spoke_24h": len(spoke_24),
        "live_now": len(live)
    }

@app.route("/metrics/platform")
def metrics():
    return Response(
        json.dumps(calculate_metrics()),
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"}
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
