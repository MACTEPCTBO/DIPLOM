import os

import dotenv
import uvicorn
from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from Server.Router.Track import track_router
from Server.Router.User import user_router
from setting import IP, PORT
from fastapi.responses import FileResponse

app = FastAPI()

dotenv.load_dotenv()
app.include_router(user_router)
app.include_router(track_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                     # или ["http://localhost:8000", "null", "file://"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="templates"), name="static")

# Отдаём index.html как статический файл из корня templates
@app.get("/")
async def index():
    from fastapi.responses import FileResponse
    return FileResponse("templates/index.html")


@app.get("/download/PC")
async def download_pc():
    return FileResponse(
        path="templates/main.exe",
        media_type="application/octet-stream",
        filename="Космос просто.exe"   # именно .exe
    )



if __name__ == "__main__":


    # Данные для подключения (получить в настройках Supabase)
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_PRIVATE_KEY")

    uvicorn.run(app, host='0.0.0.0')