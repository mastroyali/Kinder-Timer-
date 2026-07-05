import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

CHILDREN_DATA = {
    "ERIK": {
        "squares": ["gray", "gray", "gray"],
        "timers": [0, 0, 0],
        "penalty_minutes": 0
    },
    "NICK": {
        "squares": ["gray", "gray", "gray"],
        "timers": [0, 0, 0],
        "penalty_minutes": 0
    }
}

active_connections = []
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
            font-family: Arial, sans-serif;
            background-color: #141419;
            color: #ffffff;
            margin: 0;
            padding: 20px;
        }
        .container { 
            width: 100%; 
            max-width: 600px; 
            margin: 0 auto;
        }
        h2 { text-align: center; color: #a0a0ab; margin-bottom: 30px; }
        
        .table { 
            background-color: #1e1e24; 
            border-radius: 12px; 
            padding: 15px; 
            box-shadow: 0 8px 24px rgba(0,0,0,0.5); 
            display: table;
            width: 100%;
            box-sizing: border-box;
        }
        .row { 
            display: table-row;
        }
        .cell {
            display: table-cell;
            vertical-align: middle;
            padding: 10px 5px;
            text-align: center;
        }
        .cell-name {
            text-align: left;
            width: 30%;
        }
        .cell-square {
            width: 15%;
        }
        .cell-penalty {
            width: 25%;
        }
        
        .header .cell { 
            font-weight: bold; 
            color: #8b8b98; 
            border-bottom: 2px solid #3d3d4e; 
            padding-bottom: 10px; 
        }
        .row-border .cell {
            border-bottom: 1px solid #2d2d38;
        }
        
        .name-btn { 
            background-color: #2b2b36; 
            color: #fff; 
            border: 1px solid #444454; 
            padding: 12px 8px; 
            border-radius: 8px; 
            font-size: 15px; 
            font-weight: bold; 
            cursor: pointer; 
            text-align: left;
            width: 100%;
            box-sizing: border-box;
            -webkit-appearance: none;
        }
        .square { 
            border-radius: 6px; 
            display: block; 
            height: 50px;
            line-height: 50px;
            font-size: 11px; 
            font-weight: bold; 
            color: #fff; 
            text-shadow: 1px 1px 2px rgba(0,0,0,0.8); 
            box-sizing: border-box;
        }
        .gray { background-color: #3d3d4e; }
        .yellow { background-color: #fbc02d; color: #000; text-shadow: none; }
        .orange { background-color: #ef6c00; }
        .red { background-color: #c62828; }
        
        .cell-x { 
            background-color: #141419; 
            border: 1px dashed #c62828; 
            border-radius: 8px; 
            height: 50px; 
            line-height: 50px;
            font-size: 16px; 
            font-weight: bold; 
            color: #ff5252; 
            display: block;
            box-sizing: border-box;
        }
        #debug-log {
            margin-top: 20px;
            padding: 10px;
            background: #000;
            color: #0f0;
            font-family: monospace;
            font-size: 12px;
            border-radius: 5px;
            max-height: 150px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
<div class="container" onclick="initAudio()">
    <h2>Ч У П Р А</h2>
    <div class="table" id="table-content">Ожидание данных...</div>
    <div id="debug-log">Лог отладки для iPad: Система запущена...</div>
</div>

<script>
    // Функция логирования прямо на экран старого iPad
    function logDebug(msg) {
        var logDiv = document.getElementById('debug-log');
        if (logDiv) {
            logDiv.innerHTML += '<br/>' + msg;
        }
    }

    // Безопасное определение URL вебсокета
    var wsUrl = "";
    try {
        var protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        wsUrl = protocol + window.location.host + '/ws';
        logDebug("WS URL определен: " + wsUrl);
    } catch(e) {
        logDebug("Ошибка определения URL: " + e.message);
    }

    var socket = null;
    var audioCtx = null;

    function initAudio() {
        if (!audioCtx) {
            try {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                var buffer = audioCtx.createBuffer(1, 1, 22050);
                var source = audioCtx.createBufferSource();
                source.buffer = buffer;
                source.connect(audioCtx.destination);
                if (source.start) { source.start(0); } else if (source.noteOn) { source.noteOn(0); }
                logDebug("Аудио инициализировано");
            } catch (e) {
                logDebug("Ошибка аудио: " + e.message);
            }
        }
    }

    function playBeep() {
        initAudio();
        if (!audioCtx) return;
        try {
            var oscillator = audioCtx.createOscillator();
            var gainNode = audioCtx.createGain();
            oscillator.type = 'sine';
            oscillator.frequency.setValueAtTime(880, audioCtx.currentTime); 
            gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime); 
            gainNode.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 0.2); 
            oscillator.connect(gainNode);
            gainNode.connect(audioCtx.destination);
            if (oscillator.start) { oscillator.start(0); } else if (oscillator.noteOn) { oscillator.noteOn(0); }
            if (oscillator.stop) { oscillator.stop(audioCtx.currentTime + 0.2); } else if (oscillator.noteOff) { oscillator.noteOff(audioCtx.currentTime + 0.2); }
        } catch (e) {
            logDebug("Ошибка воспроизведения: " + e.message);
        }
    }

    function formatTime(seconds) {
        if (seconds <= 0) return "";
        var h = Math.floor(seconds / 3600);
        var m = Math.floor((seconds % 3600) / 60);
        var s = seconds % 60;
        if (h > 0) return h + "h" + m + "m";
        if (m > 0) return m + "m" + s + "s";
        return s + "s";
    }

    function formatPenalty(minutes) {
        if (minutes === 0) return "0m";
        var h = Math.floor(minutes / 60);
        var m = minutes % 60;
        if (h > 0) return "-" + h + "h" + m + "m";
        return "-" + m + "m";
    }

    function connect() {
        try {
            logDebug("Попытка подключения к WebSocket...");
            // Проверка поддержки WebSocket старым браузером
            var WSObj = window.WebSocket || window.MozWebSocket;
            if (!WSObj) {
                logDebug("Критическая ошибка: Браузер не поддерживает WebSocket!");
                return;
            }
            
            socket = new WSObj(wsUrl);
            
            socket.onopen = function() {
                logDebug("WebSocket соединение успешно установлено!");
            };

            socket.onmessage = function(event) {
                try {
                    var response = JSON.parse(event.data);
                    if (response.play_sound) {
                        playBeep();
                    }
                    renderTable(response.data);
                } catch(err) {
                    logDebug("Ошибка обработки сообщения: " + err.message);
                }
            };

            socket.onclose = function() { 
                logDebug("Соединение закрыто. Реконнект через 2 сек...");
                setTimeout(connect, 2000); 
            };

            socket.onerror = function(err) {
                logDebug("Ошибка WebSocket-соединения.");
            };

        } catch(e) {
            logDebug("Ошибка в блоке connect: " + e.message);
        }
    }

    function renderTable(data) {
        var container = document.getElementById('table-content');
        if (!container) return;
        
        try {
            var html = '<div class="row header">' +
                       '<div class="cell cell-name">Имя</div>' +
                       '<div class="cell cell-square">1</div>' +
                       '<div class="cell cell-square">2</div>' +
                       '<div class="cell cell-square">3</div>' +
                       '<div class="cell cell-penalty">Ячейка Х</div>' +
                       '</div>';
                       
            for (var name in data) {
                if (data.hasOwnProperty(name)) {
                    var info = data[name];
                    html += '<div class="row row-border">' +
                        '<div class="cell cell-name"><button class="name-btn" onclick="clickName(\'' + name + '\')">' + name + '</button></div>' +
                        '<div class="cell cell-square"><div class="square ' + info.squares[0] + '">' + formatTime(info.timers[0]) + '</div></div>' +
                        '<div class="cell cell-square"><div class="square ' + info.squares[1] + '">' + formatTime(info.timers[1]) + '</div></div>' +
                        '<div class="cell cell-square"><div class="square ' + info.squares[2] + '">' + formatTime(info.timers[2]) + '</div></div>' +
                        '<div class="cell cell-penalty"><div class="cell-x">' + formatPenalty(info.penalty_minutes) + '</div></div>' +
                    '</div>';
                }
            }
            container.innerHTML = html;
        } catch(e) {
            logDebug("Ошибка рендеринга таблицы: " + e.message);
        }
    }

    function clickName(name) {
        if (socket && socket.readyState === 1) { // 1 означает OPEN в старых спецификациях
            try {
                socket.send(JSON.stringify({ "action": "click", "name": name }));
            } catch(e) {
                logDebug("Ошибка отправки клика: " + e.message);
            }
        } else {
            logDebug("Клик не отправлен: сокет не готов.");
        }
    }
    
    // Запуск процесса соединения
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
        child["squares"][0] = "yellow"
        child["timers"][0] = TIMER_DURATION
    elif squares[0] == "yellow" and squares[1] == "gray":
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
            if child["timers"][2] > 0:
                child["timers"][2] -= 1
                if child["timers"][2] == 0:
                    child["squares"][2] = "gray"
            elif child["timers"][1] > 0:
                child["timers"][1] -= 1
                if child["timers"][1] == 0:
                    child["squares"][1] = "gray"
            elif child["timers"][0] > 0:
                child["timers"][0] -= 1
                if child["timers"][0] == 0:
                    child["squares"][0] = "gray"
                    
        await broadcast_state(play_sound=False)

async def broadcast_state(play_sound: bool = False):
    if active_connections:
        payload = {
            "data": CHILDREN_DATA,
            "play_sound": play_sound
        }
        tasks = [connection.send_json(payload) for connection in active_connections]
        await asyncio.gather(*tasks, return_exceptions=True)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(tick_processing())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    await websocket.send_json({"data": CHILDREN_DATA, "play_sound": False})
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "click":
                handle_click(data.get("name"))
                await broadcast_state(play_sound=True)
    except WebSocketDisconnect:
        active_connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
