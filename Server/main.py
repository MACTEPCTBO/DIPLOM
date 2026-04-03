import uvicorn
from fastapi import FastAPI

from Server.setting import IP, PORT

app = FastAPI()



if __name__ == "__main__":
    uvicorn.run(app, host=IP, port=PORT)