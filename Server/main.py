import os

import dotenv
import uvicorn
from fastapi import FastAPI

from Server.Router.Track import track_router
from Server.Router.User import user_router
from setting import IP, PORT

app = FastAPI()

dotenv.load_dotenv()
app.include_router(user_router)
app.include_router(track_router)

if __name__ == "__main__":


    # Данные для подключения (получить в настройках Supabase)
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_PRIVATE_KEY")

    uvicorn.run(app, host=IP, port=PORT)