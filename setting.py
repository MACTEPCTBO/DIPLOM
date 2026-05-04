import os
from yandex_music import ClientAsync

IP = "127.0.0.1"
PORT = 8000

API = "/api/server"

async def get_client_yandex() -> ClientAsync:
    client_yandex = await ClientAsync(os.getenv('YANDEX_TOKEN')).init()
    return client_yandex