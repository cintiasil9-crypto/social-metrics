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
# CALCULATE METRICS (REAL-TIME, EVENT-BASED)
# ------------------------------------------------

def calculate_metrics():

    rows = fetch_rows()
    now = time.time()

    total_registered = set()
    spoke_24h = set()
    live_now = set()
    power_counter = {}

    for r in rows:

        uid = r.get("avatar_uuid")
        if not uid:
            continue

        total_registered.add(uid)

        try:
            ts = float(r.get("timestamp"))
        except:
            continue

        age = now - ts

        # Spoke in last 24 hours
        if age <= 86400:
            spoke_24h.add(uid)

        # Live right now (last 60 seconds)
        if age <= 60:
            live_now.add(uid)

        # Count messages in last hour for power users
        if age <= 3600:
            power_counter[uid] = power_counter.get(uid, 0) + 1

    # Power users = 20+ messages in last hour
    power_users = len([u for u, count in power_counter.items() if count >= 20])

    return {
        "total_registered": len(total_registered),
        "spoke_24h": len(spoke_24h),
        "live_now": len(live_now),
        "power_users": power_users,
        "silent_observers": 0  # cannot derive from event table
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

@app.route("/metrics/panel")
def metrics_panel():

    metrics = calculate_metrics()

    total = metrics.get("total_registered", 0)
    spoke = metrics.get("spoke_24h", 0)
    live = metrics.get("live_now", 0)
    power = metrics.get("power_users", 0)

    html = f"""
    <html>
    <head>
    <meta http-equiv="refresh" content="30">
    <style>

        html, body {{
            margin:0;
            padding:0;
            height:100%;
            width:100%;
            overflow:hidden;
            font-family: 'Segoe UI', sans-serif;
            background: radial-gradient(circle at center,
                #140030 0%,
                #0b001f 40%,
                #000010 100%);
            color:white;
        }}

        .container {{
            height:100vh;
            width:100vw;
            display:flex;
            flex-direction:column;
            justify-content:space-evenly;
            align-items:center;
            padding:40px;
            box-sizing:border-box;
        }}

        .title {{
            font-size:42px;
            letter-spacing:4px;
            margin-bottom:10px;
            background: linear-gradient(90deg,#00f0ff,#ff00ff);
            -webkit-background-clip:text;
            -webkit-text-fill-color:transparent;
            text-align:center;
        }}

        .board {{
            width:90%;
            max-width:1200px;
            height:85%;
            display:flex;
            flex-direction:column;
            justify-content:space-evenly;
        }}

        .card {{
            flex:1;
            margin:15px 0;
            background:rgba(25,25,60,0.6);
            backdrop-filter:blur(12px);
            border-radius:24px;
            display:flex;
            flex-direction:column;
            justify-content:center;
            align-items:center;
            box-shadow:
                0 0 30px rgba(0,255,255,0.25),
                0 0 60px rgba(255,0,255,0.2);
        }}

        .label {{
            font-size:22px;
            letter-spacing:2px;
            opacity:0.7;
            margin-bottom:15px;
        }}

        .value {{
            font-size:72px;
            font-weight:700;
            background:linear-gradient(90deg,#00f0ff,#ff00ff);
            -webkit-background-clip:text;
            -webkit-text-fill-color:transparent;
            text-shadow:0 0 25px rgba(0,255,255,0.4);
        }}

    </style>
    </head>

    <body>
        <div class="container">

            <div class="title">📊 PLATFORM METRICS</div>

            <div class="board">

                <div class="card">
                    <div class="label">TOTAL REGISTERED</div>
                    <div class="value">{total}</div>
                </div>

                <div class="card">
                    <div class="label">SPOKE LAST 24 HOURS</div>
                    <div class="value">{spoke}</div>
                </div>

                <div class="card">
                    <div class="label">LIVE RIGHT NOW</div>
                    <div class="value">{live}</div>
                </div>

                <div class="card">
                    <div class="label">POWER USERS (1H)</div>
                    <div class="value">{power}</div>
                </div>

            </div>
        </div>
    </body>
    </html>
    """

    return html


@app.route("/")
def ok():
    return "SOCIAL METRICS LIVE", 200


# ------------------------------------------------
# RUN (RENDER COMPATIBLE)
# ------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
