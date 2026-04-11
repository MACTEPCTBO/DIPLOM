import asyncio
from typing import Annotated

import dotenv
import os

from fastapi import Depends
from supabase import AsyncClient


async def get_supabase_client() -> AsyncClient:
    client: AsyncClient = await (AsyncClient(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_PRIVATE_KEY")
    )).create(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_PRIVATE_KEY")
    )
    return client

# Проверка подключения
async def main():
    try:
        response = await ((await get_supabase_client()).table('User').select("*").limit(1)).execute()
        print("✅ Подключение успешно!")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")


SessionDep = Annotated[AsyncClient, Depends(get_supabase_client)]

if __name__ == "__main__":
    dotenv.load_dotenv()

    # Данные для подключения (получить в настройках Supabase)
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_PRIVATE_KEY")

    asyncio.run(main())