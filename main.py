import os
import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()

# Базовые данные приложения
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

TIMER_DURATION = 20 * 60 

def format_time(seconds):
    if seconds <= 0:
        return ""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h{m}m"
    if m > 0:
        return f"{m}m{s}s"
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
    # Генерируем HTML-контент динамически на стороне сервера при каждом обновлении
    
    table_rows = ""
    for name, info in CHILDREN_DATA.items():
        t0 = format_time(info["timers"][0])
        t1 = format_time(info["timers"][1])
        t2 = format_time(info["timers"][2])
        penalty = format_penalty(info["penalty_minutes"])
        
        table_rows += f"""
        <div class="row row-border">
            <div class="cell cell-name">
                <a class="name-btn" href="/click/{name}">{name}</a>
            </div>
            <div class="cell cell-square"><div class="square {info['squares'][0]}">{t0}</div></div>
            <div class="cell cell-square"><div class="square {info['squares'][1]}">{t1}</div></div>
            <div class="cell cell-square"><div class="square {info['squares'][2]}">{t2}</div></div>
            <div class="cell cell-penalty"><div class="cell-x">{penalty}</div></div>
        </div>
        """

    # Вставляем тег мета-обновления, который принудительно обновляет страницу раз в 1 секунду
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="1">
        <title>Панель Контроля Времени</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #141419;
                color: #ffffff;
                margin: 0;
                padding: 20px;
            }}
            .container {{ 
                width: 100%; 
                max-width: 600px; 
                margin: 0 auto;
            }}
            h2 {{ text-align: center; color: #a0a0ab; margin-bottom: 30px; }}
            
            .table {{ 
                background-color: #1e1e24; 
                border-radius: 12px; 
                padding: 15px; 
                box-shadow: 0 8px 24px rgba(0,0,0,0.5); 
                display: table;
                width: 100%;
                box-sizing: border-box;
            }}
            .row {{ 
                display: table-row;
            }}
            .cell {{
                display: table-cell;
                vertical-align: middle;
                padding: 10px 5px;
                text-align: center;
            }}
            .cell-name {{
                text-align: left;
                width: 30%;
            }}
            .cell-square {{
                width: 15%;
            }}
            .cell-penalty {{
                width: 25%;
            }}
            
            .header .cell {{ 
                font-weight: bold; 
                color: #8b8b98; 
                border-bottom: 2px solid #3d3d4e; 
                padding-bottom: 10px; 
            }}
            .row-border .cell {{
                border-bottom: 1px solid #2d2d38;
            }}
            
            .name-btn {{ 
                display: block;
                background-color: #2b2b36; 
                color: #fff; 
                border: 1px solid #444454; 
                padding: 12px 8px; 
                border-radius: 8px; 
                font-size: 15px; 
                font-weight: bold; 
                text-align: center;
                text-decoration: none;
                box-sizing: border-box;
                -webkit-appearance: none;
            }}
            .square {{ 
                border-radius: 6px; 
                display: block; 
                height: 50px; 
                line-height: 50px;
                font-size: 11px; 
                font-weight: bold; 
                color: #fff; 
                text-shadow: 1px 1px 2px rgba(0,0,0,0.8); 
                box-sizing: border-box;
            }}
            .gray {{ background-color: #3d3d4e; }}
            .yellow {{ background-color: #fbc02d; color: #000; text-shadow: none; }}
            .orange {{ background-color: #ef6c00; }}
            .red {{ background-color: #c62828; }}
            
            .cell-x {{ 
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
            }}
        </style>
    </head>
    <body>
    <div class="container">
        <h2>Монитор2</h2>
        <div class="table">
            <div class="row header">
                <div class="cell cell-name">Имя</div>
                <div class="cell cell-square">1</div>
                <div class="cell cell-square">2</div>
                <div class="cell cell-square">3</div>
                <div class="cell cell-penalty">Ячейка Х</div>
            </div>
            {table_rows}
        </div>
    </div>
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
            
    # После обработки клика мгновенно перенаправляем пользователя обратно на главную страницу
    return RedirectResponse(url="/", status_code=303)

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
