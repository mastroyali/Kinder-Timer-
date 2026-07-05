import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

# Храним состояние: добавлен флаг режима редактирования для каждого ребенка
CHILDREN_DATA = {
    "ERIK": {
        "squares": ["gray", "gray", "gray"],
        "timers": [0, 0, 0],
        "penalty_minutes": 0,
        "edit_mode": False
    },
    "NICK": {
        "squares": ["gray", "gray", "gray"],
        "timers": [0, 0, 0],
        "penalty_minutes": 0,
        "edit_mode": False
    }
}

active_connections: list[WebSocket] = []
TIMER_DURATION = 20 * 60 

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Панель Контроля Времени</title>
    <style>
        html, body {
            height: 100%;
            margin: 0;
            padding: 0;
            background-color: #141419;
            color: #ffffff;
            font-family: 'Segoe UI', Arial, sans-serif;
            overflow-x: hidden;
            overflow-y: auto;
            -webkit-user-select: none;
            user-select: none;
        }
        
        .container { 
            display: flex;
            flex-direction: column;
            width: 100vw; 
            min-height: 100vh;
            box-sizing: border-box;
            padding: 2vh 2vw;
        }
        
        h2 { 
            text-align: center; 
            color: #a0a0ab; 
            margin: 0 0 2vh 0; 
            font-size: 4vh;
        }
        
        .table { 
            display: flex;
            flex-direction: column;
            gap: 3vh;
            flex-grow: 1;
            box-sizing: border-box;
        }
        
        /* Адаптивная карточка для каждого ребенка */
        .user-card {
            background-color: #1e1e24; 
            border-radius: 16px; 
            padding: 2vh; 
            box-shadow: 0 12px 36px rgba(0,0,0,0.5);
            border: 3px solid #3d3d4e;
            transition: border-color 0.3s ease;
            display: grid;
            grid-template-columns: 2fr 1fr 1fr 1fr 1.3fr;
            gap: 15px;
            align-items: center;
        }

        /* Розовые рамки в режиме редактирования */
        .user-card.edit-active {
            border-color: #ff69b4 !important;
            box-shadow: 0 0 20px rgba(255, 105, 180, 0.4);
        }
        
        .name-btn { 
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #2b2b36; 
            color: #fff; 
            border: 2px solid #444454; 
            padding: 15px 10px; 
            border-radius: 14px; 
            font-size: 4vh; 
            font-weight: bold; 
            cursor: pointer; 
            width: 100%;
            box-sizing: border-box;
            -webkit-appearance: none;
            appearance: none;
            background-image: none;
        }
        
        .name-btn:active {
            background-color: #3d3d4e;
        }
        
        /* Идеальная геометрия квадратов во всех браузерах */
        .square { 
            aspect-ratio: 1 / 1;
            width: 100%;
            max-width: 90px;
            margin: 0 auto;
            border-radius: 14px; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            font-size: 2.3vh; 
            font-weight: bold; 
            box-sizing: border-box;
            border: 3px solid #444454;
            -webkit-appearance: none;
            appearance: none;
            background-image: none;
            transition: transform 0.1s ease;
        }

        .square:disabled, .cell-x:disabled {
            cursor: default;
        }

        .edit-active .square:not(.gray), .edit-active .cell-x {
            cursor: pointer;
            border-color: #ff69b4 !important;
        }
        
        /* Фиксация цветов без системных градиентов мобильных ОС */
        .gray { background-color: #3d3d4e !important; color: #ffffff !important; border-color: #555568; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); }
        .yellow { background-color: #fbc02d !important; color: #000000 !important; border-color: #fff350; text-shadow: none; }
        .orange { background-color: #ef6c00 !important; color: #ffffff !important; border-color: #ff9d3f; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); }
        .red { background-color: #c62828 !important; color: #ffffff !important; border-color: #ff5f5f; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); }
        
        .cell-x { 
            background-color: #141419 !important; 
            border: 2px dashed #c62828; 
            border-radius: 14px; 
            padding: 15px 5px;
            display: flex; 
            justify-content: center; 
            align-items: center; 
            font-size: 3.5vh; 
            font-weight: bold; 
            color: #ff5252 !important; 
            width: 100%;
            box-sizing: border-box;
            -webkit-appearance: none;
            appearance: none;
            background-image: none;
        }

        /* Адаптивность: перестроение под вертикальный экран телефона */
        @media (max-width: 600px) {
            .user-card {
                grid-template-columns: 1fr 1fr 1fr;
                gap: 10px;
            }
            .name-btn {
                grid-column: span 2;
                font-size: 3.5vh;
                padding: 10px;
            }
            .cell-x {
                grid-column: span 1;
                font-size: 3vh;
                padding: 10px 5px;
            }
            .square {
                grid-column: span 1;
                font-size: 2vh;
                max-width: 75px;
            }
        }
    </style>
</head>
<body>
<div class="container" onclick="initAudio()">
    <h2>Мониторинг Наказаний</h2>
    <div class="table" id="table-content"></div>
</div>
<script>
    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = protocol + window.location.host + '/ws';
    let socket;
    let audioCtx = null;
    let pressTimer = null;

    function initAudio() {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
    }

    function playBeep() {
        initAudio();
        if (!audioCtx) return;
        try {
            const oscillator = audioCtx.createOscillator();
            const gainNode = audioCtx.createGain();
            oscillator.type = 'sine';
            oscillator.frequency.setValueAtTime(880, audioCtx.currentTime); 
            gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime); 
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.2); 
            oscillator.connect(gainNode);
            gainNode.connect(audioCtx.destination);
            oscillator.start();
            oscillator.stop(audioCtx.currentTime + 0.2);
        } catch (e) { console.log(e); }
    }

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
            const response = JSON.parse(event.data);
            if (response.play_sound) playBeep();
            renderTable(response.data);
        };
        socket.onclose = function() { setTimeout(connect, 1500); };
    }

    function renderTable(data) {
        const container = document.getElementById('table-content');
        if (!container) return;
        
        let html = "";
        for (const [name, info] of Object.entries(data)) {
            const editClass = info.edit_mode ? "edit-active" : "";
            const isClickable = info.edit_mode ? "" : "disabled";

            html += `
            <div class="user-card ${editClass}">
                <button class="name-btn" 
                        onmousedown="startPress('${name}')" 
                        onmouseup="endPress('${name}')" 
                        onmouseleave="cancelPress()"
                        ontouchstart="startPress('${name}')" 
                        ontouchend="endPress('${name}')">
                    ${name}${info.edit_mode ? " ⚙" : ""}
                </button>
                <button class="square ${info.squares[0]}" ${isClickable} onclick="clickElement('${name}', 0)">${formatTime(info.timers[0])}</button>
                <button class="square ${info.squares[1]}" ${isClickable} onclick="clickElement('${name}', 1)">${formatTime(info.timers[1])}</button>
                <button class="square ${info.squares[2]}" ${isClickable} onclick="clickElement('${name}', 2)">${formatTime(info.timers[2])}</button>
                <button class="cell-x" ${isClickable} onclick="clickElement('${name}', 'x')">${formatPenalty(info.penalty_minutes)}</button>
            </div>`;
        }
        container.innerHTML = html;
    }

    // Логика удержания кнопки (Long Press 3 секунды)
    function startPress(name) {
        initAudio();
        cancelPress();
        pressTimer = setTimeout(() => {
            sendAction({ "action": "long_press", "name": name });
            pressTimer = null;
        }, 3000); 
    }

    function endPress(name) {
        if (pressTimer !== null) {
            clearTimeout(pressTimer);
            pressTimer = null;
            sendAction({ "action": "click", "name": name });
        }
    }

    function cancelPress() {
        if (pressTimer !== null) {
            clearTimeout(pressTimer);
            pressTimer = null;
        }
    }

    function clickElement(name, elementIdx) {
        sendAction({ "action": "cancel_element", "name": name, "element": elementIdx });
    }

    function sendAction(payload) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(payload));
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
    # Если включен режим редактирования, обычные клики по имени игнорируются
    if child["edit_mode"]:
        return
        
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

def handle_cancel(name: str, element):
    child = CHILDREN_DATA[name]
    if not child["edit_mode"]:
        return

    # Отмена штрафного времени в ячейке Х
    if element == 'x':
        if child["penalty_minutes"] >= 20:
            child["penalty_minutes"] -= 20
    # Отмена конкретных квадратов предупреждений
    else:
        idx = int(element)
        child["squares"][idx] = "gray"
        child["timers"][idx] = 0

# Таймер автоматического выхода из режима редактирования через 5 секунд
async def auto_disable_edit_mode(name: str):
    await asyncio.sleep(5)
    if CHILDREN_DATA[name]["edit_mode"]:
        CHILDREN_DATA[name]["edit_mode"] = False
        await broadcast_state(play_sound=False)

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
            action = data.get("action")
            name = data.get("name")
            
            if action == "click":
                handle_click(name)
                await broadcast_state(play_sound=True)
                
            elif action == "long_press":
                # Переключаем режим редактирования
                CHILDREN_DATA[name]["edit_mode"] = not CHILDREN_DATA[name]["edit_mode"]
                await broadcast_state(play_sound=True)
                if CHILDREN_DATA[name]["edit_mode"]:
                    asyncio.create_task(auto_disable_edit_mode(name))
                    
            elif action == "cancel_element":
                element = data.get("element")
                handle_cancel(name, element)
                await broadcast_state(play_sound=True)
                
    except WebSocketDisconnect:
        active_connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
