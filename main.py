import os
import asyncio
import uuid
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

ADMIN_PASSWORD = "3003"
TIMER_DURATION = 20 * 60 

CHILDREN_DATA = {
    "ERIC": {
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

SYSTEM_LOGS = []
ACTIVE_CONNECTIONS = {}

def add_log(message: str):
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    SYSTEM_LOGS.append(f"[{now}] {message}")
    if len(SYSTEM_LOGS) > 100:
        SYSTEM_LOGS.pop(0)

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
            font-family: Arial, sans-serif;
            overflow-x: hidden;
            overflow-y: auto;
            -webkit-user-select: none;
            user-select: none;
        }
        
        .container { 
            display: flex;
            flex-direction: column;
            width: 100%; 
            min-height: 100vh;
            box-sizing: border-box;
            padding: 15px;
        }
        
        .main-content {
            flex: 1 0 auto;
        }
        
        h2 { 
            text-align: center; 
            color: #a0a0ab; 
            margin: 0 0 20px 0; 
            font-size: 26px;
        }
        
        .cards-wrapper { 
            display: flex;
            flex-direction: column;
            width: 100%;
            box-sizing: border-box;
        }
        
        .user-card {
            background-color: #1e1e24; 
            border-radius: 20px; 
            padding: 18px; 
            margin-bottom: 20px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
            border: 3px solid #3d3d4e;
        }

        .user-card.edit-active {
            border-color: #ff69b4 !important;
        }
        
        .name-btn { 
            background-color: #2b2b36; 
            color: #fff; 
            border: 2px solid #444454; 
            padding: 14px; 
            border-radius: 14px; 
            font-size: 24px; 
            font-weight: bold; 
            cursor: pointer; 
            width: 100%;
            box-sizing: border-box;
            text-align: center;
            outline: none;
            -webkit-tap-highlight-color: transparent;
        }
        
        .controls-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
            margin-top: 15px;
        }
        
        .square { 
            width: 23%;
            height: 85px;
            border-radius: 14px; 
            display: flex; 
            flex-direction: column;
            justify-content: center; 
            align-items: center; 
            font-size: 14px; 
            font-weight: bold; 
            border: 3px solid #444454;
            box-sizing: border-box;
            background-color: #3d3d4e;
            color: #ffffff;
            outline: none;
            -webkit-tap-highlight-color: transparent;
        }
        
        .gray { background-color: #3d3d4e !important; color: #ffffff !important; border-color: #555568; }
        .yellow { background-color: #fbc02d !important; color: #000000 !important; border-color: #fff350; }
        .orange { background-color: #ef6c00 !important; color: #ffffff !important; border-color: #ff9d3f; }
        .red { background-color: #c62828 !important; color: #ffffff !important; border-color: #ff5f5f; }
        
        .cell-x { 
            width: 23%;
            height: 85px;
            background-color: #141419 !important; 
            border: 3px dashed #c62828; 
            border-radius: 14px; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            font-size: 16px; 
            font-weight: bold; 
            color: #ff5252 !important; 
            box-sizing: border-box;
        }

        /* Оптимизированный контейнер регулировки штрафа */
        .penalty-edit-container {
            width: 23%;
            height: 85px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            align-items: center;
            box-sizing: border-box;
            padding: 2px 0;
        }

        .penalty-edit-btn {
            width: 100%;
            height: 24px; /* Чуть уменьшили высоту, чтобы дать простор тексту */
            border: 1.5px solid #ff69b4;
            border-radius: 6px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #fff;
            outline: none;
            -webkit-tap-highlight-color: transparent;
        }
        .btn-inc { background-color: #2e7d32; }
        .btn-dec { background-color: #c62828; }

        .penalty-edit-value {
            font-size: 15px; /* Увеличили шрифт */
            font-weight: 900; /* Сделали максимально жирным */
            color: #ff69b4;
            text-align: center;
            line-height: 24px;
            flex-grow: 1;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .bottom-bar {
            flex: 0 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
            padding: 10px 0;
            box-sizing: border-box;
        }

        .admin-trigger-btn {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            border: 2px solid #444454;
            background-color: #2b2b36;
            color: #a0a0ab;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            display: flex;
            justify-content: center;
            align-items: center;
            outline: none;
            -webkit-tap-highlight-color: transparent;
        }

        .admin-trigger-btn.admin-active {
            background-color: #1b5e20;
            border-color: #4caf50;
            color: #fff;
        }

        .log-trigger-btn {
            background: none;
            border: none;
            color: #4a4a5a;
            font-size: 14px;
            text-decoration: underline;
            cursor: pointer;
        }

        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background-color: rgba(0,0,0,0.85);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            box-sizing: border-box;
            padding: 20px;
        }

        .log-window {
            background-color: #1e1e24;
            border: 2px solid #3d3d4e;
            border-radius: 16px;
            width: 100%;
            max-width: 450px;
            height: 70vh;
            display: flex;
            flex-direction: column;
        }

        .modal-header {
            padding: 15px;
            border-bottom: 1px solid #3d3d4e;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: bold;
            color: #a0a0ab;
        }

        .modal-close {
            background: #3d3d4e;
            border: none;
            color: #fff;
            border-radius: 8px;
            padding: 6px 14px;
        }

        .log-content {
            flex-grow: 1;
            padding: 15px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 13px;
            color: #d1d1d6;
            white-space: pre-wrap;
        }

        .auth-window {
            background-color: #1e1e24;
            border: 2px solid #3d3d4e;
            border-radius: 16px;
            width: 280px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .auth-title {
            font-size: 18px;
            font-weight: bold;
            color: #a0a0ab;
            margin-bottom: 15px;
        }

        .auth-input {
            width: 100%;
            background-color: #141419;
            border: 2px solid #444454;
            border-radius: 10px;
            padding: 12px;
            color: #fff;
            font-size: 22px;
            text-align: center;
            margin-bottom: 15px;
            outline: none;
        }

        .auth-buttons {
            display: flex;
            width: 100%;
        }

        .auth-btn {
            flex: 1;
            padding: 10px;
            border-radius: 8px;
            border: none;
            font-weight: bold;
            font-size: 14px;
            color: white;
            margin: 0 5px;
        }
        .auth-confirm { background-color: #4caf50; }
        .auth-cancel { background-color: #3d3d4e; }
    </style>
</head>
<body>
<div class="container">
    <div class="main-content">
        <h2>Ч У П Р А</h2>
        <div class="cards-wrapper">
            
            <!-- КАРТОЧКА ERIC -->
            <div id="card_ERIC" class="user-card">
                <button id="name_ERIC" class="name-btn">ERIC</button>
                <div class="controls-row">
                    <button id="sq_ERIC_0" class="square"><span>1</span><strong id="t_ERIC_0"></strong></button>
                    <button id="sq_ERIC_1" class="square"><span>2</span><strong id="t_ERIC_1"></strong></button>
                    <button id="sq_ERIC_2" class="square"><span>3</span><strong id="t_ERIC_2"></strong></button>
                    
                    <!-- Блок отображения штрафа в обычном режиме -->
                    <div id="p_view_ERIC" class="cell-x">0m</div>
                    
                    <!-- Блок изменения штрафа (режим А) -->
                    <div id="p_edit_ERIC" class="penalty-edit-container" style="display:none;">
                        <button class="penalty-edit-btn btn-inc" onclick="modifyPenalty('ERIC', 'inc')">+</button>
                        <div id="p_val_ERIC" class="penalty-edit-value">0m</div>
                        <button class="penalty-edit-btn btn-dec" onclick="modifyPenalty('ERIC', 'dec')">-</button>
                    </div>
                </div>
            </div>

            <!-- КАРТОЧКА NICK -->
            <div id="card_NICK" class="user-card">
                <button id="name_NICK" class="name-btn">NICK</button>
                <div class="controls-row">
                    <button id="sq_NICK_0" class="square"><span>1</span><strong id="t_NICK_0"></strong></button>
                    <button id="sq_NICK_1" class="square"><span>2</span><strong id="t_NICK_1"></strong></button>
                    <button id="sq_NICK_2" class="square"><span>3</span><strong id="t_NICK_2"></strong></button>
                    
                    <div id="p_view_NICK" class="cell-x">0m</div>
                    
                    <div id="p_edit_NICK" class="penalty-edit-container" style="display:none;">
                        <button class="penalty-edit-btn btn-inc" onclick="modifyPenalty('NICK', 'inc')">+</button>
                        <div id="p_val_NICK" class="penalty-edit-value">0m</div>
                        <button class="penalty-edit-btn btn-dec" onclick="modifyPenalty('NICK', 'dec')">-</button>
                    </div>
                </div>
            </div>

        </div>
    </div>
    
    <div class="bottom-bar">
        <button class="admin-trigger-btn" id="adminBtn" onclick="clickAdminButton()">А</button>
        <button class="log-trigger-btn" onclick="openLogs()">Логи системы</button>
    </div>
</div>

<!-- Модальные окна -->
<div class="modal-overlay" id="logOverlay" onclick="closeModal('logOverlay', event)">
    <div class="log-window" onclick="event.stopPropagation()">
        <div class="modal-header">
            <span>История событий</span>
            <button class="modal-close" onclick="document.getElementById('logOverlay').style.display='none'">Закрыть</button>
        </div>
        <div class="log-content" id="logContent">Загрузка...</div>
    </div>
</div>

<div class="modal-overlay" id="authOverlay" onclick="closeModal('authOverlay', event)">
    <div class="auth-window" onclick="event.stopPropagation()">
        <div class="auth-title">Вход в режим "А"</div>
        <input type="password" class="auth-input" id="authPin" inputmode="numeric" pattern="[0-9]*" maxlength="4" placeholder="••••">
        <div class="auth-buttons">
            <button class="auth-btn auth-cancel" onclick="document.getElementById('authOverlay').style.display='none'">Отмена</button>
            <button class="auth-btn auth-confirm" onclick="submitAuth()">Войти</button>
        </div>
    </div>
</div>

<script>
    var protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    var wsUrl = protocol + window.location.host + '/ws';
    var socket;
    var audioCtx = null;
    var pressTimer = null;
    var isLongPressTriggered = false;
    
    var lastClickTime = 0;
    var CLICK_DEBOUNCE_MS = 300;
    var clientIsAdmin = false;

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
            var oscillator = audioCtx.createOscillator();
            var gainNode = audioCtx.createGain();
            oscillator.type = 'sine';
            oscillator.frequency.setValueAtTime(880, audioCtx.currentTime); 
            gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime); 
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.2); 
            oscillator.connect(gainNode);
            gainNode.connect(audioCtx.destination);
            oscillator.start();
            oscillator.stop(audioCtx.currentTime + 0.2);
        } catch (e) {}
    }

    function formatTime(seconds) {
        if (seconds <= 0) return "";
        var m = Math.floor(seconds / 60);
        var s = seconds % 60;
        return m + "m" + s + "s";
    }

    function formatPenalty(minutes) {
        if (minutes === 0) return "0m";
        var h = Math.floor(minutes / 60);
        var m = minutes % 60;
        if (h > 0) return "-" + h + "h" + m + "m";
        return "-" + m + "m";
    }

    function bindEvents(name) {
        var btn = document.getElementById("name_" + name);
        if (!btn) return;

        var startHandler = function(e) {
            if (!clientIsAdmin) return;
            initAudio();
            isLongPressTriggered = false;
            
            if (pressTimer) clearTimeout(pressTimer);
            
            pressTimer = setTimeout(function() {
                sendAction({ "action": "long_press", "name": name });
                isLongPressTriggered = true;
                pressTimer = null;
            }, 3000); 
        };

        var endHandler = function(e) {
            if (!clientIsAdmin) return;
            if (pressTimer) {
                clearTimeout(pressTimer);
                pressTimer = null;
            }
            if (!isLongPressTriggered) {
                var currentTime = new Date().getTime();
                if (currentTime - lastClickTime > CLICK_DEBOUNCE_MS) {
                    sendAction({ "action": "click", "name": name });
                    lastClickTime = currentTime;
                }
            }
            isLongPressTriggered = false;
        };

        var cancelHandler = function() {
            if (pressTimer) {
                clearTimeout(pressTimer);
                pressTimer = null;
            }
        };

        btn.ontouchstart = startHandler;
        btn.ontouchend = endHandler;
        btn.ontouchcancel = cancelHandler;

        btn.onmousedown = startHandler;
        btn.onmouseup = endHandler;
        btn.onmouseout = cancelHandler;

        for (var i = 0; i < 3; i++) {
            (function(idx) {
                var sq = document.getElementById("sq_" + name + "_" + idx);
                sq.onclick = function() {
                    if (!clientIsAdmin) return;
                    var cardData = window.lastData ? window.lastData[name] : null;
                    if (cardData && cardData.edit_mode) {
                        var currentTime = new Date().getTime();
                        if (currentTime - lastClickTime < CLICK_DEBOUNCE_MS) return;
                        lastClickTime = currentTime;
                        sendAction({ "action": "cancel_element", "name": name, "element": idx });
                    }
                };
            })(i);
        }
    }

    function connect() {
        socket = new WebSocket(wsUrl);
        socket.onmessage = function(event) {
            var response = JSON.parse(event.data);
            if (response.play_sound) playBeep();
            
            if (response.is_admin !== undefined) {
                clientIsAdmin = response.is_admin;
                var btn = document.getElementById("adminBtn");
                if (clientIsAdmin) {
                    btn.classList.add("admin-active");
                } else {
                    btn.classList.remove("admin-active");
                }
            }
            
            if (response.data) {
                window.lastData = response.data;
                updateChildUI("ERIC", response.data["ERIC"]);
                updateChildUI("NICK", response.data["NICK"]);
            }
            if (response.logs) renderLogs(response.logs);
        };
        socket.onclose = function() { setTimeout(connect, 5500); };
    }

    function updateChildUI(name, info) {
        if (!info) return;

        var card = document.getElementById("card_" + name);
        var nameBtn = document.getElementById("name_" + name);
        
        if (info.edit_mode) {
            card.classList.add("edit-active");
            nameBtn.innerHTML = name + " ⚙";
        } else {
            card.classList.remove("edit-active");
            nameBtn.innerHTML = name;
        }

        for (var i = 0; i < 3; i++) {
            var sq = document.getElementById("sq_" + name + "_" + i);
            var tNode = document.getElementById("t_" + name + "_" + i);
            sq.className = "square " + info.squares[i];
            tNode.innerHTML = formatTime(info.timers[i]);
        }

        var pView = document.getElementById("p_view_" + name);
        var pEdit = document.getElementById("p_edit_" + name);
        var pVal = document.getElementById("p_val_" + name);
        
        var penaltyText = formatPenalty(info.penalty_minutes);

        if (info.edit_mode && clientIsAdmin) {
            pView.style.display = "none";
            pVal.innerHTML = penaltyText; 
            pEdit.style.display = "flex";
        } else {
            pView.innerHTML = penaltyText;
            pView.style.display = "flex";
            pEdit.style.display = "none";
        }
    }

    function modifyPenalty(name, operation) {
        if (!clientIsAdmin) return;
        sendAction({ "action": "modify_penalty", "name": name, "operation": operation });
    }

    function clickAdminButton() {
        if (clientIsAdmin) {
            sendAction({ "action": "admin_logout" });
        } else {
            document.getElementById("authPin").value = "";
            document.getElementById("authOverlay").style.display = "flex";
            document.getElementById("authPin").focus();
        }
    }

    function submitAuth() {
        var pin = document.getElementById("authPin").value;
        if (pin.length === 4) {
            sendAction({ "action": "admin_login", "password": pin });
            document.getElementById("authOverlay").style.display = "none";
        }
    }

    function openLogs() {
        document.getElementById('logOverlay').style.display = 'flex';
        sendAction({ "action": "request_logs" });
    }

    function closeModal(id, e) {
        if(e.target.id === id) {
            document.getElementById(id).style.display = 'none';
        }
    }

    function renderLogs(logsList) {
        var content = document.getElementById('logContent');
        if (content) {
            content.textContent = logsList.length > 0 ? logsList.slice().reverse().join('\\n') : "История пуста.";
        }
    }

    function sendAction(payload) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(payload));
        }
    }

    bindEvents("ERIC");
    bindEvents("NICK");
    
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
    if child["edit_mode"]:
        return
        
    squares = child["squares"]
    if squares[0] == "gray":
        child["squares"][0] = "yellow"
        child["timers"][0] = TIMER_DURATION
        add_log(f"Для {name} активировано 1-е предупреждение (Желтый квадрат).")
    elif squares[0] == "yellow" and squares[1] == "gray":
        child["squares"][1] = "orange"
        child["timers"][1] = TIMER_DURATION
        add_log(f"Для {name} активировано 2-е предупреждение (Оранжевый квадрат).")
    elif squares[1] == "orange" and squares[2] == "gray":
        child["squares"][2] = "red"
        child["timers"][2] = TIMER_DURATION
        add_log(f"Для {name} активировано 3-е предупреждение (Красный квадрат).")
    elif squares[2] == "red":
        child["penalty_minutes"] += 20
        child["timers"][2] = TIMER_DURATION
        add_log(f"Для {name} добавлено +20 минут штрафа. Время 3-го кубика возвращено на 20 мин. Всего штрафа: {child['penalty_minutes']}м.")

def handle_cancel(name: str, element):
    child = CHILDREN_DATA[name]
    if not child["edit_mode"]:
        return

    idx = int(element)
    color_names = {0: "1-й (Желтый)", 1: "2-й (Оранжевый)", 2: "3-й (Красный)"}
    if child["squares"][idx] != "gray":
        child["squares"][idx] = "gray"
        child["timers"][idx] = 0
        add_log(f"В режиме редактирования сброшен {color_names.get(idx)} квадрат у {name}.")

def handle_modify_penalty(name: str, operation: str):
    child = CHILDREN_DATA[name]
    if not child["edit_mode"]:
        return

    if operation == "inc":
        child["penalty_minutes"] += 20
        add_log(f"В режиме редактирования добавлено +20 минут штрафа у {name}. Всего: {child['penalty_minutes']}м.")
    elif operation == "dec":
        if child["penalty_minutes"] >= 20:
            child["penalty_minutes"] -= 20
            add_log(f"В режиме редактирования снято -20 минут штрафа у {name}. Осталось: {child['penalty_minutes']}м.")

async def auto_disable_edit_mode(name: str):
    await asyncio.sleep(25)
    if CHILDREN_DATA[name]["edit_mode"]:
        CHILDREN_DATA[name]["edit_mode"] = False
        add_log(f"Режим редактирования для {name} автоматически закрыт по таймауту.")
        await broadcast_state(play_sound=False)

async def tick_processing():
    while True:
        await asyncio.sleep(1)
        for name, child in CHILDREN_DATA.items():
            if child["timers"][2] > 0:
                child["timers"][2] -= 1
                if child["timers"][2] == 0:
                    child["squares"][2] = "gray"
                    add_log(f"Время действия 3-го предупреждения (Красный квадрат) у {name} истекло.")
            elif child["timers"][1] > 0:
                child["timers"][1] -= 1
                if child["timers"][1] == 0:
                    child["squares"][1] = "gray"
                    add_log(f"Время действия 2-го предупреждения (Оранжевый квадрат) у {name} истекло.")
            elif child["timers"][0] > 0:
                child["timers"][0] -= 1
                if child["timers"][0] == 0:
                    child["squares"][0] = "gray"
                    add_log(f"Время действия 1-го предупреждения (Желтый квадрат) у {name} истекло.")
                    
        await broadcast_state(play_sound=False)

async def broadcast_state(play_sound: bool = False):
    if ACTIVE_CONNECTIONS:
        for ws, client_info in list(ACTIVE_CONNECTIONS.items()):
            payload = {
                "data": CHILDREN_DATA,
                "play_sound": play_sound,
                "logs": SYSTEM_LOGS,
                "is_admin": client_info["is_admin"]
            }
            try:
                await ws.send_json(payload)
            except Exception:
                pass

@app.on_event("startup")
async def startup_event():
    add_log("Система контроля времени успешно запущена.")
    asyncio.create_task(tick_processing())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ACTIVE_CONNECTIONS[websocket] = {"id": str(uuid.uuid4()), "is_admin": False}
    
    await websocket.send_json({
        "data": CHILDREN_DATA, 
        "play_sound": False, 
        "logs": SYSTEM_LOGS,
        "is_admin": False
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            name = data.get("name")
            
            client_info = ACTIVE_CONNECTIONS.get(websocket, {"is_admin": False})
            is_client_admin = client_info["is_admin"]
            
            if action == "admin_login":
                password = data.get("password")
                if password == ADMIN_PASSWORD:
                    ACTIVE_CONNECTIONS[websocket]["is_admin"] = True
                    add_log("Устройство успешно вошло в режим Администратора.")
                    await broadcast_state(play_sound=True)
                continue
                
            elif action == "admin_logout":
                ACTIVE_CONNECTIONS[websocket]["is_admin"] = False
                add_log("Устройство вышло из режима Администратора.")
                await broadcast_state(play_sound=False)
                continue
                
            elif action == "request_logs":
                await websocket.send_json({"logs": SYSTEM_LOGS})
                continue

            if not is_client_admin:
                continue

            if action == "click":
                handle_click(name)
                await broadcast_state(play_sound=True)
                
            elif action == "long_press":
                CHILDREN_DATA[name]["edit_mode"] = not CHILDREN_DATA[name]["edit_mode"]
                state_str = "активирован" if CHILDREN_DATA[name]["edit_mode"] else "деактивирован"
                add_log(f"Режим редактирования для {name} {state_str} вручную удержанием.")
                await broadcast_state(play_sound=True)
                if CHILDREN_DATA[name]["edit_mode"]:
                    asyncio.create_task(auto_disable_edit_mode(name))
                    
            elif action == "cancel_element":
                element = data.get("element")
                handle_cancel(name, element)
                await broadcast_state(play_sound=True)
                
            elif action == "modify_penalty":
                operation = data.get("operation")
                handle_modify_penalty(name, operation)
                await broadcast_state(play_sound=True)
                
    except WebSocketDisconnect:
        if websocket in ACTIVE_CONNECTIONS:
            del ACTIVE_CONNECTIONS[websocket]

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
