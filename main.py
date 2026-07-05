import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

CHILDREN_DATA = {
    "Максим": {
        "squares": ["gray", "gray", "gray"],
        "timers": [0, 0, 0],
        "penalty_minutes": 0
    },
    "Аня": {
        "squares": ["gray", "gray", "gray"],
        "timers": [0, 0, 0],
        "penalty_minutes": 0
    }
}

active_connections: list[WebSocket] = []
TIMER_DURATION = 20 * 60 

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Панель Контроля Времени</title>
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
            background-color: #141419;
            color: #ffffff;
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
        }
        .container { width: 100%; max-width: 600px; }
        h2 { text-align: center; color: #a0a0ab; margin-bottom: 30px; }
        .table { background-color: #1e1e24; border-radius: 12px; padding: 15px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
        .row { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1.2fr; align-items: center; gap: 10px; padding: 15px 0; border-bottom: 1px solid #2d2d38; }
        .row:last-child { border-bottom: none; }
        .header { font-weight: bold; color: #8b8b98; border-bottom: 2px solid #3d3d4e; padding-bottom: 10px; }
        .name-btn { background-color: #2b2b36; color: #fff; border: 1px solid #444454; padding: 12px; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; text-align: left; }
        .square { aspect-ratio: 1; border-radius: 6px; display: flex; justify-content: center; align-items: center; font-size: 11px; font-weight: bold; color: #fff; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); }
        .gray { background-color: #3d3d4e; }
        .green { background-color: #2e7d32; }
        .orange { background-color: #ef6c00; }
        .red { background-color: #c62828; }
        .cell-x { background-color: #141419; border: 1px dashed #c62828; border-radius: 8px; height: 100%; display: flex; justify-content: center; align-items: center; font-size: 16px; font-weight: bold; color: #ff5252; min-height: 45px; }
    </style>
</head>
<body>
<div class="container">
    <h2>Мониторинг Наказаний</h2>
    <div class="table" id="table-content"></div>
</div>
<script>
    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = protocol + window.location.host + '/ws';
    let socket;

    function formatTime(seconds) {
        if (seconds <= 0) return "";
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        if (h > 0) return `${h}h${m}m`;
        if (m > 0) return `${m}m${s}s`;
        return `${s}s`;
    }

    function formatPenalty(minutes) {
        if (minutes === 0) return "0m";
        const h = Math.floor(minutes / 60);
        const m = minutes % 60;
        if (h > 0) return `-${h}h${m}m`;
        return `-${m}m`;
    }

    function connect() {
        socket = new WebSocket(wsUrl);
        socket.onmessage = function(event) {
            renderTable(JSON.parse(event.data));
        };
        socket.onclose = function() { setTimeout(connect, 1500); };
    }

    function renderTable(data) {
        const container = document.getElementById('table-content');
        let html = `<div class="row header"><div>Имя</div><div style="text-align:center">1</div><div style="text-align:center">2</div><div style="text-align:center">3</div><div style="text-align:center">Ячейка Х</div></div>`;
        for (const [name, info] of Object.entries(data)) {
            html += `<div class="row">
                <button class="name-btn" onclick="clickName('${name}')">${name}</button>
                <div class="square ${info.squares[0]}">${formatTime(info.timers[0])}</div>
                <div class="square ${info.squares[1]}">${formatTime(info.timers[1])}</div>
                <div class="square ${info.squares[2]}">${formatTime(info.timers[2])}</div>
                <div class="cell-x">${formatPenalty(info.penalty_minutes)}</div>
            </div>`;
        }
        container.innerHTML = html;
    }

    function clickName(name) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ "action": "click", "name": name }));
        }
    }
    connect();
</script>
</body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(HTML_TEMPLATE)

def handle_click(name: str):
    child = CHILDREN_DATA[name]
    squares = child["squares"]
    if squares[0] == "gray":
        child["squares"][0] = "green"
        child["timers"][0] = TIMER_DURATION
    elif squares[0] == "green" and squares[1] == "gray":
        child["squares"][1] = "orange"
        child["timers"][1] = TIMER_DURATION
    elif squares[1] == "orange" and squares[2] == "gray":
        child["squares"][2] = "red"
        child["timers"][2] = TIMER_DURATION
    elif squares[2] == "red":
        child["penalty_minutes"] += 20

async def tick_processing():
    while True:
        await asyncio.sleep(1)
        for name, child in CHILDREN_DATA.items():
            for i in range(3):
                if child["timers"][i] > 0:
                    child["timers"][i] -= 1
                    if child["timers"][i] == 0:
                        child["squares"][i] = "gray"
        await broadcast_state()

async def broadcast_state():
    if active_connections:
        tasks = [connection.send_json(CHILDREN_DATA) for connection in active_connections]
        await asyncio.gather(*tasks, return_exceptions=True)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(tick_processing())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    await websocket.send_json(CHILDREN_DATA)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "click":
                handle_click(data.get("name"))
                await broadcast_state()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
