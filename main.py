import os
import json
import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

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

SYSTEM_FLAGS = {
    "play_sound": False
}

TIMER_DURATION = 20 * 60 

def format_time(seconds):
    if seconds <= 0:
        return ""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h"
    if m > 0:
        return f"{m}m"
    return f"{s}s"

def format_penalty(minutes):
    if minutes == 0:
        return "0m"
    h = minutes // 60
    m = minutes % 60
    if h > 0:
        return f"-{h}h{m}m"
    return f"-{m}m"

@app.get("/")
async def get_dashboard():
    # Главная страница: крупный интерфейс без мерцания
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Ч У П Р А</title>
        <style>
            html, body {
                height: 100%;
                margin: 0;
                padding: 0;
                background-color: #141419;
                color: #ffffff;
                font-family: Arial, sans-serif;
                overflow: hidden;
            }
            .container {
                display: flex;
                flex-direction: column;
                height: 100vh;
                width: 100vw;
                box-sizing: border-box;
                padding: 2vh 2vw;
            }
            h2 {
                text-align: center;
                color: #a0a0ab;
                margin: 0 0 2vh 0;
                font-size: 4vh;
                height: 5vh;
            }
            .table {
                display: flex;
                flex-direction: column;
                flex-grow: 1;
                background-color: #1e1e24;
                border-radius: 16px;
                padding: 2vh;
                box-shadow: 0 12px 36px rgba(0,0,0,0.5);
                box-sizing: border-box;
            }
            .row {
                display: flex;
                flex-direction: row;
                align-items: center;
                width: 100%;
            }
            .header {
                height: 6vh;
                border-bottom: 3px solid #3d3d4e;
                font-weight: bold;
                color: #8b8b98;
                font-size: 3vh;
            }
            .row-user {
                flex-grow: 1;
                border-bottom: 1px solid #2d2d38;
            }
            .row-user:last-child {
                border-bottom: none;
            }
            .cell {
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0 1vw;
                box-sizing: border-box;
                height: 100%;
            }
            .cell-name { width: 30%; justify-content: flex-start; }
            .cell-square { width: 15%; }
            .cell-penalty { width: 25%; }

            .name-btn {
                display: flex;
                align-items: center;
                justify-content: center;
                background-color: #2b2b36;
                color: #fff;
                border: 2px solid #444454;
                border-radius: 12px;
                font-size: 4.5vh;
                font-weight: bold;
                text-decoration: none;
                width: 100%;
                height: 85%;
                box-sizing: border-box;
                -webkit-appearance: none;
            }
            .name-btn:active {
                background-color: #3d3d4e;
            }
            .square {
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                width: 100%;
                height: 85%;
                font-size: 3.5vh;
                font-weight: bold;
                color: #fff;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
                box-sizing: border-box;
            }
            .gray { background-color: #3d3d4e; }
            .yellow { background-color: #fbc02d; color: #000; text-shadow: none; }
            .orange { background-color: #ef6c00; }
            .red { background-color: #c62828; }

            .cell-x {
                background-color: #141419;
                border: 2px dashed #c62828;
                border-radius: 12px;
                width: 100%;
                height: 85%;
                font-size: 4.5vh;
                font-weight: bold;
                color: #ff5252;
                display: flex;
                align-items: center;
                justify-content: center;
                box-sizing: border-box;
            }
            #hidden-loader {
                display: none;
            }
        </style>
    </head>
    <body onclick="initAudio()">
    <div class="container">
        <h2>Мониторинг Наказаний</h2>
        <div class="table">
            <div class="header row">
                <div class="cell cell-name">Имя</div>
                <div class="cell cell-square">1</div>
                <div class="cell cell-square">2</div>
                <div class="cell cell-square">3</div>
                <div class="cell cell-penalty">Ячейка Х</div>
            </div>
            
            <!-- Строка Эрика -->
            <div class="row row-user" id="row-ERIK">
                <div class="cell cell-name"><a class="name-btn" href="/click/ERIK" target="hidden-loader">ERIK</a></div>
                <div class="cell cell-square"><div id="ERIK-sq0" class="square gray"></div></div>
                <div class="cell cell-square"><div id="ERIK-sq1" class="square gray"></div></div>
                <div class="cell cell-square"><div id="ERIK-sq2" class="square gray"></div></div>
                <div class="cell cell-penalty"><div id="ERIK-txtX" class="cell-x">0m</div></div>
            </div>

            <!-- Строка Ника -->
            <div class="row row-user" id="row-NICK">
                <div class="cell cell-name"><a class="name-btn" href="/click/NICK" target="hidden-loader">NICK</a></div>
                <div class="cell cell-square"><div id="NICK-sq0" class="square gray"></div></div>
                <div class="cell cell-square"><div id="NICK-sq1" class="square gray"></div></div>
                <div class="cell cell-square"><div id="NICK-sq2" class="square gray"></div></div>
                <div class="cell cell-penalty"><div id="NICK-txtX" class="cell-x">0m</div></div>
            </div>
        </div>
    </div>

    <!-- Абсолютно скрытый фрейм, который раз в секунду запрашивает данные в фоне без мерцания экрана -->
    <iframe id="hidden-loader" name="hidden-loader" src="/iframe-data"></iframe>

    <script>
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
                } catch (e) { console.log("Audio Init Error"); }
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
            } catch (e) { console.log("Sound Error"); }
        }

        // Функция обновления DOM, вызываемая из скрытого фрейма
        window.updateDOM = function(id, className, innerHTML) {
            var el = document.getElementById(id);
            if (el) {
                if (el.className !== className) el.className = className;
                if (el.innerHTML !== innerHTML) el.innerHTML = innerHTML;
            }
        };

        window.triggerSound = function() {
            playBeep();
        };

        // Заставляем iframe обновляться раз в секунду в фоновом режиме
        setInterval(function() {
            var iframe = document.getElementById('hidden-loader');
            if (iframe) {
                iframe.src = "/iframe-data?ts=" + new Date().getTime();
            }
        }, 1000);
    </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/iframe-data")
async def get_iframe_data(ts: str = None):
    # Эта страница грузится внутри скрытого фрейма и передает команды наверх в основное окно
    sound_trigger = ""
    if SYSTEM_FLAGS["play_sound"]:
        SYSTEM_FLAGS["play_sound"] = False
        sound_trigger = "window.parent.triggerSound();"

    js_commands = ""
    for name, info in CHILDREN_DATA.items():
        t0 = format_time(info["timers"][0])
        t1 = format_time(info["timers"][1])
        t2 = format_time(info["timers"][2])
        penalty = format_penalty(info["penalty_minutes"])
        
        js_commands += f"window.parent.updateDOM('{name}-sq0', 'square {info['squares'][0]}', '{t0}');"
        js_commands += f"window.parent.updateDOM('{name}-sq1', 'square {info['squares'][1]}', '{t1}');"
        js_commands += f"window.parent.updateDOM('{name}-sq2', 'square {info['squares'][2]}', '{t2}');"
        js_commands += f"window.parent.updateDOM('{name}-txtX', 'cell-x', '{penalty}');"

    html_content = f"""
    <html>
    <head><meta http-equiv="refresh" content="1"></head>
    <body>
    <script>
        try {{
            {sound_trigger}
            {js_commands}
        }} catch(e) {{}}
    </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/click/{name}")
async def process_click(name: str):
    if name in CHILDREN_DATA:
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
            
        SYSTEM_FLAGS["play_sound"] = True
            
    # Перенаправляем скрытый фрейм на пустую страницу обновления данных
    return RedirectResponse(url="/iframe-data", status_code=303)

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

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(tick_processing())

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
