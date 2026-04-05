import hashlib
import os
from datetime import datetime, timedelta
import jwt

import dotenv

from fastapi import APIRouter, HTTPException
from supabase import AsyncClient

from Server.Model.User import Register, Login, LoginResponse, RefreshToken
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


@user_router.post("/login", response_model=LoginResponse)
async def login(data: Login):
    session = await get_supabase_client()
    if data.AccessToken is None:
        # 1. Проверить логин/пароль в БД
        user = await (session.table("User")
                      .select("*")
                      .eq("Login", data.Login)
                      .eq("Password", data.Password)
                      .execute())
        if not user.data:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_id = user.data[0]["Id"]

    else:
        payload = jwt.decode(data.AccessToken, SECRET_KEY, algorithms=[ALGORITHM])

        if payload["TimeLife"] < datetime.now().timestamp():
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user = await (session.table("User")
                      .select("*")
                      .eq("Id", payload["UserId"])
                      .execute())
        if not user.data:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_id = user.data[0]["Id"]
        created_at = user.data[0]["Created_at"]

    # 2. Создать новую пару токенов
    access_token = await create_access_token(user_id)
    refresh_token = await create_refresh_token(user_id)
    hash_ = hashlib.sha256(refresh_token.encode()).hexdigest()

    token_data = {
        "Token": refresh_token,
        "UserId": user_id,
        "HashToken": hash_
    }

    await (session.table('RefreshToken').insert(token_data)).execute()

    return LoginResponse(AccessToken=access_token, RefreshToken=refresh_token)


@user_router.post("/refresh")
async def refresh(data: RefreshToken):
    session: AsyncClient = await get_supabase_client()
    try:
        payload = jwt.decode(data.Token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload["TimeLife"] < datetime.now().timestamp():
            return HTTPException(status_code=401, detail="Invalid credentials")

        user = await (session.table("User")
                .select("*")
                .eq("Id", payload["UserId"])
                ).execute()

        if len(user.data):
            access_token = await create_access_token(user.data[0]["Id"])
            refresh_token = await create_refresh_token(user.data[0]["Id"])

            old_token_hash = hashlib.sha256(data.Token.encode()).hexdigest()
            new_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

            # Вызываем хранимую процедуру
            try:
                result = await session.rpc(
                    'rotate_refresh_token',
                    {
                        'p_old_token_hash': old_token_hash,
                        'p_new_token': refresh_token,
                        'p_user_id': user.data[0]["Id"],
                        'p_new_token_hash': new_token_hash
                    }
                ).execute()
                if result.data == False:
                    return HTTPException(status_code=401, detail="Invalid credentials")

                return LoginResponse(AccessToken=access_token, RefreshToken=refresh_token)
            except Exception as e:
                print(f"Rotation failed: {e}")
                return False
        else:
            return HTTPException(status_code=401, detail="The user was not found")


    except Exception as err:
        raise HTTPException(status_code=401, detail="Invalid credentials")



async def create_access_token(id: int) -> str:
    access_token = {
        "UserId": id,
        "TimeLife": (datetime.now() + timedelta(days=1)).timestamp()
    }
    token_access = jwt.encode(access_token, SECRET_KEY, algorithm=ALGORITHM)

    return token_access

async def create_refresh_token(id: int) -> str:
    refresh_token = {
        "UserId": id,
        "TimeLife": (datetime.now() + timedelta(days=31)).timestamp()
    }

    token_refresh = jwt.encode(refresh_token, SECRET_KEY, algorithm=ALGORITHM)



    return token_refresh