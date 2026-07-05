import os
import asyncio
import uuid
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

# Пароль для активации режима Администратора
ADMIN_PASSWORD = "1234"
TIMER_DURATION = 20 * 60 

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

SYSTEM_LOGS = []

# Структура для отслеживания активных соединений и их прав
# Хранит dict вида: { websocket_object: {"id": str, "is_admin": bool} }
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
            padding: 15px;
            justify-content: space-between;
        }
        
        h2 { 
            text-align: center; 
            color: #a0a0ab; 
            margin: 0 0 20px 0; 
            font-size: 28px;
            letter-spacing: 0.5px;
        }
        
        .cards-wrapper { 
            display: flex;
            flex-direction: column;
            gap: 20px;
            flex-grow: 1;
            width: 100%;
            box-sizing: border-box;
        }
        
        .user-card {
            background-color: #1e1e24; 
            border-radius: 20px; 
            padding: 18px; 
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
            border: 3px solid #3d3d4e;
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .user-card.edit-active {
            border-color: #ff69b4 !important;
            box-shadow: 0 0 20px rgba(255, 105, 180, 0.3);
        }
        
        .name-btn { 
            background-color: #2b2b36; 
            color: #fff; 
            border: 2px solid #444454; 
            padding: 14px; 
            border-radius: 14px; 
            font-size: 26px; 
            font-weight: bold; 
            cursor: pointer; 
            width: 100%;
            box-sizing: border-box;
            text-align: center;
            -webkit-appearance: none;
            appearance: none;
            touch-action: none;
        }
        
        .name-btn:disabled {
            cursor: default;
            opacity: 0.8;
        }
        
        .controls-row {
            display: grid;
            grid-template-columns: repeat(3, 1fr) 1.3fr;
            gap: 10px;
            align-items: center;
            width: 100%;
        }
        
        .square { 
            aspect-ratio: 1 / 1;
            width: 100%;
            border-radius: 14px; 
            display: flex; 
            flex-direction: column;
            justify-content: center; 
            align-items: center; 
            font-size: 14px; 
            font-weight: bold; 
            box-sizing: border-box;
            border: 3px solid #444454;
            -webkit-appearance: none;
            appearance: none;
        }

        .square:disabled, .cell-x:disabled {
            cursor: default;
        }

        .edit-active .square:not(.gray) {
            cursor: pointer;
            border-color: #ff69b4 !important;
        }
        
        .gray { background-color: #3d3d4e !important; color: #ffffff !important; border-color: #555568; text-shadow: 1px 1px 2px rgba(0,0,0,0.6); }
        .yellow { background-color: #fbc02d !important; color: #000000 !important; border-color: #fff350; text-shadow: none; }
        .orange { background-color: #ef6c00 !important; color: #ffffff !important; border-color: #ff9d3f; text-shadow: 1px 1px 2px rgba(0,0,0,0.6); }
        .red { background-color: #c62828 !important; color: #ffffff !important; border-color: #ff5f5f; text-shadow: 1px 1px 2px rgba(0,0,0,0.6); }
        
        .cell-x { 
            height: 100%;
            min-height: 75px;
            background-color: #141419 !important; 
            border: 3px dashed #c62828; 
            border-radius: 14px; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            font-size: 19px; 
            font-weight: bold; 
            color: #ff5252 !important; 
            width: 100%;
            box-sizing: border-box;
            -webkit-appearance: none;
            appearance: none;
        }

        /* Контейнер регулировки штрафа для режима редактирования */
        .penalty-edit-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 5px;
            height: 100%;
            width: 100%;
            box-sizing: border-box;
        }

        .penalty-edit-btn {
            height: 100%;
            min-height: 75px;
            border: 2px solid #ff69b4;
            border-radius: 12px;
            font-size: 24px;
            font-weight: bold;
            cursor: pointer;
            display: flex;
            justify-content: center;
            align-items: center;
            -webkit-appearance: none;
        }
        .btn-inc { background-color: #2e7d32; color: #fff; }
        .btn-dec { background-color: #c62828; color: #fff; }

        /* Нижняя панель управления системными кнопками */
        .bottom-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
            padding: 15px 10px 5px 10px;
            box-sizing: border-box;
        }

        /* Кнопка Администратора "А" */
        .admin-trigger-btn {
            width: 36px;
            height: 36px;
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
            transition: all 0.3s ease;
            -webkit-appearance: none;
        }

        .admin-trigger-btn.admin-active {
            background-color: #1b5e20;
            border-color: #4caf50;
            color: #fff;
            box-shadow: 0 0 10px rgba(76, 175, 80, 0.4);
        }

        .log-trigger-btn {
            background: none;
            border: none;
            color: #4a4a5a;
            font-size: 13px;
            text-decoration: underline;
            cursor: pointer;
            padding: 5px 10px;
            -webkit-appearance: none;
        }
        
        .log-trigger-btn:active { color: #8a8a9a; }

        /* Модальные окна */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
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
            height: 75vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
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
            cursor: pointer;
            font-size: 14px;
        }

        .log-content {
            flex-grow: 1;
            padding: 15px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
            line-height: 1.5;
            color: #d1d1d6;
            white-space: pre-wrap;
            -webkit-user-select: text;
            user-select: text;
        }

        /* Окно ввода пароля */
        .auth-window {
            background-color: #1e1e24;
            border: 2px solid #3d3d4e;
            border-radius: 16px;
            width: 280px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 15px;
            align-items: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        }

        .auth-title {
            font-size: 18px;
            font-weight: bold;
            color: #a0a0ab;
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
            letter-spacing: 6px;
            box-sizing: border-box;
            outline: none;
        }

        .auth-input:focus {
            border-color: #4caf50;
        }

        .auth-buttons {
            display: flex;
            gap: 10px;
            width: 100%;
        }

        .auth-btn {
            flex: 1;
            padding: 10px;
            border-radius: 8px;
            border: none;
            font-weight: bold;
            cursor: pointer;
            font-size: 14px;
        }
        .auth-confirm { background-color: #4caf50; color: white; }
        .auth-cancel { background-color: #3d3d4e; color: white; }
    </style>
</head>
<body>
<div class="container" pointerdown="initAudio()">
    <div>
        <h2>Мониторинг Наказаний</h2>
        <div class="cards-wrapper" id="table-content"></div>
    </div>
    
    <div class="bottom-bar">
        <button class="admin-trigger-btn" id="adminBtn" onclick="clickAdminButton()">А</button>
        <button class="log-trigger-btn" onclick="openLogs()">Логи системы</button>
    </div>
</div>

<!-- Модальное окно истории -->
<div class="modal-overlay" id="logOverlay" onclick="closeModal('logOverlay', event)">
    <div class="log-window" onclick="event.stopPropagation()">
        <div class="modal-header">
            <span>История событий</span>
            <button class="modal-close" onclick="document.getElementById('logOverlay').style.display='none'">Закрыть</button>
        </div>
        <div class="log-content" id="logContent">Загрузка...</div>
    </div>
</div>

<!-- Модальное окно авторизации А-режима -->
<div class="modal-overlay" id="authOverlay" onclick="closeModal('authOverlay', event)">
    <div class="auth-window" onclick="event.stopPropagation()">
        <div class="auth-title">Вход в режим "А"</div>
        <input type="password" class="auth-input" id="authPin" inputmode="numeric" pattern="[0-9]*" maxlength="4" placeholder="••••">
        <div class="auth-buttons">
            <button class="auth-btn class auth-cancel" onclick="document.getElementById('authOverlay').style.display='none'">Отмена</button>
            <button class="auth-btn auth-confirm" onclick="submitAuth()">Войти</button>
        </div>
    </div>
</div>

<script>
    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = protocol + window.location.host + '/ws';
    let socket;
    let audioCtx = null;
    let pressTimer = null;
    
    let lastClickTime = 0;
    const CLICK_DEBOUNCE_MS = 300;
    let clientIsAdmin = false; // Локальный статус админа для отрисовки

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
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}m${s}s`;
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
            
            if (response.hasOwnProperty("is_admin")) {
                clientIsAdmin = response.is_admin;
                const btn = document.getElementById("adminBtn");
                if (clientIsAdmin) {
                    btn.classList.add("admin-active");
                } else {
                    btn.classList.remove("admin-active");
                }
            }
            
            if (response.data) renderTable(response.data);
            if (response.logs) renderLogs(response.logs);
        };
        socket.onclose = function() { setTimeout(connect, 1500); };
    }

    function renderTable(data) {
        const container = document.getElementById('table-content');
        if (!container) return;
        
        let html = "";
        for (const [name, info] of Object.entries(data)) {
            const editClass = info.edit_mode ? "edit-active" : "";
            const isClickable = (info.edit_mode && clientIsAdmin) ? "" : "disabled";
            const nameDisabled = clientIsAdmin ? "" : "disabled";

            // Генерируем блок штрафа: либо обычная ячейка, либо +/- в режиме редактирования
            let penaltyBlockHtml = "";
            if (info.edit_mode && clientIsAdmin) {
                penaltyBlockHtml = `
                <div class="penalty-edit-container">
                    <button class="penalty-edit-btn btn-inc" onclick="modifyPenalty('${name}', 'inc')">+</button>
                    <button class="penalty-edit-btn btn-dec" onclick="modifyPenalty('${name}', 'dec')">-</button>
                </div>`;
            } else {
                penaltyBlockHtml = `
                <button class="cell-x" disabled>
                    ${formatPenalty(info.penalty_minutes)}
                </button>`;
            }

            html += `
            <div class="user-card ${editClass}">
                <button class="name-btn" ${nameDisabled}
                        onpointerdown="startPress(event, '${name}')" 
                        onpointerup="endPress(event, '${name}')" 
                        onpointerleave="cancelPress()">
                    ${name}${info.edit_mode ? " ⚙" : ""}
                </button>
                <div class="controls-row">
                    <button class="square ${info.squares[0]}" ${isClickable} onclick="clickElement('${name}', 0)">
                        <span>1</span><strong>${formatTime(info.timers[0])}</strong>
                    </button>
                    <button class="square ${info.squares[1]}" ${isClickable} onclick="clickElement('${name}', 1)">
                        <span>2</span><strong>${formatTime(info.timers[1])}</strong>
                    </button>
                    <button class="square ${info.squares[2]}" ${isClickable} onclick="clickElement('${name}', 2)">
                        <span>3</span><strong>${formatTime(info.timers[2])}</strong>
                    </button>
                    ${penaltyBlockHtml}
                </div>
            </div>`;
        }
        container.innerHTML = html;
    }

    function startPress(e, name) {
        if (!clientIsAdmin) return;
        e.preventDefault();
        initAudio();
        cancelPress();
        
        const currentTime = new Date().getTime();
        if (currentTime - lastClickTime < CLICK_DEBOUNCE_MS) return;

        pressTimer = setTimeout(() => {
            sendAction({ "action": "long_press", "name": name });
            pressTimer = null;
            lastClickTime = new Date().getTime();
        }, 3000); 
    }

    function endPress(e, name) {
        if (!clientIsAdmin) return;
        e.preventDefault();
        const currentTime = new Date().getTime();
        
        if (pressTimer !== null) {
            clearTimeout(pressTimer);
            pressTimer = null;
            
            if (currentTime - lastClickTime > CLICK_DEBOUNCE_MS) {
                sendAction({ "action": "click", "name": name });
                lastClickTime = currentTime;
            }
        }
    }

    function cancelPress() {
        if (pressTimer !== null) {
            clearTimeout(pressTimer);
            pressTimer = null;
        }
    }

    function clickElement(name, elementIdx) {
        if (!clientIsAdmin) return;
        const currentTime = new Date().getTime();
        if (currentTime - lastClickTime < CLICK_DEBOUNCE_MS) return;
        lastClickTime = currentTime;
        
        sendAction({ "action": "cancel_element", "name": name, "element": elementIdx });
    }

    function modifyPenalty(name, operation) {
        if (!clientIsAdmin) return;
        sendAction({ "action": "modify_penalty", "name": name, "operation": operation });
    }

    function clickAdminButton() {
        if (clientIsAdmin) {
            // Если уже админ — выходим без запроса пароля
            sendAction({ "action": "admin_logout" });
        } else {
            document.getElementById("authPin").value = "";
            document.getElementById("authOverlay").style.display = "flex";
            document.getElementById("authPin").focus();
        }
    }

    function submitAuth() {
        const pin = document.getElementById("authPin").value;
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
        const content = document.getElementById('logContent');
        if (content) {
            content.textContent = logsList.length > 0 ? logsList.reverse().join('\\n') : "История пуста.";
        }
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
        # Новая логика: время в предыдущем (3-м) кубике снова становится 20 минут
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
    await asyncio.sleep(5)
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
        # Каждому клиенту шлем общие данные + его личный статус админа
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
    # Регистрируем устройство на сервере со статусом "не админ" по умолчанию
    ACTIVE_CONNECTIONS[websocket] = {"id": str(uuid.uuid4()), "is_admin": False}
    
    # Первичный пакет данных для подключившегося устройства
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
            
            # Проверяем, авторизован ли текущий клиент как администратор
            client_info = ACTIVE_CONNECTIONS.get(websocket, {"is_admin": False})
            is_client_admin = client_info["is_admin"]
            
            # Действия авторизации (доступны всем)
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

            # Защищенные действия (требуют прав "А" на этом устройстве)
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
