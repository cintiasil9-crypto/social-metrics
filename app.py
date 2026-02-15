from flask import Flask, Response
import requests
import time
import os
import json
import re

app = Flask(__name__)

GOOGLE_PROFILES_FEED = os.environ["GOOGLE_PROFILES_FEED"]


# ------------------------------------------------
# FETCH GOOGLE SHEET
# ------------------------------------------------

def fetch_rows():
    r = requests.get(GOOGLE_PROFILES_FEED, timeout=20)

    match = re.search(r"setResponse\((\{.*\})\)", r.text, re.S)
    if not match:
        return []

    payload = json.loads(match.group(1))

    cols = [c["label"] for c in payload["table"]["cols"]]
    rows = []

    for row in payload["table"]["rows"]:
        record = {}
        for i, cell in enumerate(row["c"]):
            record[cols[i]] = cell["v"] if cell else 0
        rows.append(record)

    return rows


# ------------------------------------------------
# CALCULATE METRICS (REAL-TIME)
# ------------------------------------------------

def calculate_metrics():

    rows = fetch_rows()
    now = time.time()

    total_registered = set()
    spoke_24h = set()
    live_now = set()
    power_users = set()
    silent_observers = set()

    for r in rows:

        uid = r.get("avatar_uuid")
        if not uid:
            continue

        total_registered.add(uid)

        try:
            ts = float(r.get("timestamp", now))
            msgs = int(r.get("messages", 0))
        except:
            continue

        age = now - ts

        if age <= 86400 and msgs > 0:
            spoke_24h.add(uid)

        if age <= 60 and msgs > 0:
            live_now.add(uid)

        if age <= 3600 and msgs >= 20:
            power_users.add(uid)

        if age <= 300 and msgs == 0:
            silent_observers.add(uid)

    return {
        "total_registered": len(total_registered),
        "spoke_24h": len(spoke_24h),
        "live_now": len(live_now),
        "power_users": len(power_users),
        "silent_observers": len(silent_observers)
    }


# ------------------------------------------------
# API ENDPOINT
# ------------------------------------------------

@app.route("/metrics/platform", methods=["GET"])
def metrics_platform():
    metrics = calculate_metrics()

    return Response(
        json.dumps(metrics),
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"}
    )


@app.route("/")
def ok():
    return "SOCIAL METRICS LIVE", 200


# ------------------------------------------------
# RUN (RENDER COMPATIBLE)
# ------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
