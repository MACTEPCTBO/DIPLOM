import hashlib
import os
from datetime import datetime, timedelta
import jwt

import dotenv

from fastapi import APIRouter
from supabase import AsyncClient

from Server.Model.User import Register, Login, LoginResponse
from Server.engine import get_supabase_client
from Server.setting import API

user_router = APIRouter(prefix=f"{API}/user", tags=["User"])

dotenv.load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

@user_router.post("/register")
async def register(data: Register) -> bool:
    session: AsyncClient = await get_supabase_client()
    try:
        user_data = {
            "Login": data.Login,
            "Password": data.Password,
            "Username": data.Username,
        }
        await (session.table('User').insert(user_data)).execute()

        return True

    except Exception as err:
        print(err)
        return False


@user_router.post("/login")
async def login(data: Login):
    session: AsyncClient = await get_supabase_client()
    try:
        if data.RefreshToken is not None:
            decoded_payload = jwt.decode(data.RefreshToken, SECRET_KEY, algorithms=[ALGORITHM])
            id: int = decoded_payload['UserId']
            time_created: datetime = datetime.now()
        else:
            user = await (session.table('User')
                   .select("*")
                   .eq("Login", data.Login)
                   .eq("Password", data.Password)
                   .execute())
            id = user.data[0]['Id']
            time_created = user.data[0]['Created_at']


        return LoginResponse(RefreshToken=await create_refresh_token(id, time_created, session)
                             , AccessToken=await create_access_token(id, time_created))


    except Exception as err:
        print(err)
        return False


async def create_access_token(id: int, time_created: datetime) -> str:
    access_token = {
        "UserId": id,
        "TimeLife": (datetime.fromisoformat(str(time_created)) + timedelta(days=1)).timestamp()
    }
    token_access = jwt.encode(access_token, SECRET_KEY, algorithm=ALGORITHM)

    return token_access

async def create_refresh_token(id: int, time_created: datetime, session: AsyncClient) -> str:
    refresh_token = {
        "UserId": id,
        "TimeLife": (datetime.fromisoformat(str(time_created)) + timedelta(days=31)).timestamp()
    }

    token_refresh = jwt.encode(refresh_token, SECRET_KEY, algorithm=ALGORITHM)

    refresh_token['HashToken'] = hashlib.sha256(token_refresh.encode()).hexdigest()

    token_data = {
        "Token": token_refresh,
        "UserId": id,
        "HashToken": hashlib.sha256(token_refresh.encode()).hexdigest()
    }

    await (session.table('RefreshToken').insert(token_data)).execute()

    return token_refresh