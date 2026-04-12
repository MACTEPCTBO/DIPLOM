import os
from yandex_music import ClientAsync

IP = "192.168.1.105"
PORT = 8000

API = "/api/server"

async def get_client_yandex() -> ClientAsync:
    client_yandex = await ClientAsync(os.getenv('YANDEX_TOKEN')).init()
    return client_yandex