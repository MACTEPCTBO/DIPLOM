import os
from yandex_music import ClientAsync
import dotenv

dotenv.load_dotenv()

IP = os.getenv('IP')
PORT = int(os.getenv('PORT'))

API = os.getenv('API')

async def get_client_yandex() -> ClientAsync:
    client_yandex = await ClientAsync(os.getenv('YANDEX_TOKEN')).init()
    return client_yandex