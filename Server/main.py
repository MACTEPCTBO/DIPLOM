import os

import dotenv
import uvicorn
from fastapi import FastAPI

from Server.Router.User import user_router
from Server.setting import IP, PORT

app = FastAPI()

app.include_router(user_router)

if __name__ == "__main__":
    dotenv.load_dotenv()

    # Данные для подключения (получить в настройках Supabase)
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_PRIVATE_KEY")

    uvicorn.run(app, host=IP, port=PORT)