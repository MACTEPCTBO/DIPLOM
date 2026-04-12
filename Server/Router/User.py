import hashlib
import os
from datetime import datetime, timedelta
from typing import Annotated

import jwt
import dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette import status

from Server.Model.User import Register, Login, LoginResponse, RefreshToken, UserAuth
from Server.engine import SessionDep
from setting import API

user_router = APIRouter(prefix=f"{API}/user", tags=["User"])

dotenv.load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")


@user_router.post("/register")
async def register(
    data: Register,
    session: SessionDep
) -> bool:
    try:
        user_data = {
            "Login": data.Login,
            "Password": data.Password,
            "Username": data.Username,
        }
        await session.table('User').insert(user_data).execute()
        return True
    except Exception as err:
        print(err)
        return False


@user_router.post("/login", response_model=LoginResponse)
async def login(
    data: Login,
    session: SessionDep
):
    # Если передан AccessToken, используем его для аутентификации
    if data.AccessToken is None:
        # Проверка логина/пароля
        user = await (
            session.table("User")
            .select("*")
            .eq("Login", data.Login)
            .eq("Password", data.Password)
            .execute()
        )
        if not user.data:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        user_id = user.data[0]["Id"]
    else:
        # Аутентификация по существующему AccessToken
        try:
            payload = jwt.decode(data.AccessToken, SECRET_KEY, algorithms=[ALGORITHM])
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

        if payload["TimeLife"] < datetime.now().timestamp():
            raise HTTPException(status_code=401, detail="Token expired")

        user = await (
            session.table("User")
            .select("*")
            .eq("Id", payload["UserId"])
            .execute()
        )
        if not user.data:
            raise HTTPException(status_code=401, detail="User not found")
        user_id = user.data[0]["Id"]

    # Создание новой пары токенов
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    hash_ = hashlib.sha256(refresh_token.encode()).hexdigest()

    token_data = {
        "Token": refresh_token,
        "UserId": user_id,
        "HashToken": hash_
    }
    await session.table('RefreshToken').insert(token_data).execute()

    return LoginResponse(AccessToken=access_token, RefreshToken=refresh_token)


@user_router.post("/refresh")
async def refresh(
    data: RefreshToken,
    session: SessionDep
):
    try:
        payload = jwt.decode(data.Token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload["TimeLife"] < datetime.now().timestamp():
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = await (
        session.table("User")
        .select("*")
        .eq("Id", payload["UserId"])
        .execute()
    )
    if not user.data:
        raise HTTPException(status_code=401, detail="User not found")

    # Генерация новых токенов
    new_access_token = create_access_token(user.data[0]["Id"])
    new_refresh_token = create_refresh_token(user.data[0]["Id"])

    old_token_hash = hashlib.sha256(data.Token.encode()).hexdigest()
    new_token_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()

    # Вызов хранимой процедуры для ротации refresh токена
    try:
        result = await session.rpc(
            'rotate_refresh_token',
            {
                'p_old_token_hash': old_token_hash,
                'p_new_token': new_refresh_token,
                'p_user_id': user.data[0]["Id"],
                'p_new_token_hash': new_token_hash
            }
        ).execute()
        if not result.data:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        return LoginResponse(AccessToken=new_access_token, RefreshToken=new_refresh_token)
    except Exception as e:
        print(f"Rotation failed: {e}")
        raise HTTPException(status_code=500, detail="Token rotation failed")


# Синхронные вспомогательные функции (не требуют async)
def create_access_token(user_id: int) -> str:
    payload = {
        "UserId": user_id,
        "TimeLife": (datetime.now() + timedelta(days=1)).timestamp()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    payload = {
        "UserId": user_id,
        "TimeLife": (datetime.now() + timedelta(days=31)).timestamp()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


security = HTTPBearer()


async def get_current_user(
        session: SessionDep,
        credentials: HTTPAuthorizationCredentials = Depends(security),

)-> UserAuth:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload["TimeLife"] < datetime.now().timestamp():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["UserId"]
    user_result = await (
        session.table("User")
        .select("*")
            .eq("Id", user_id)
        .execute()
    )
    if not user_result.data:
        raise HTTPException(status_code=404, detail="User not found")

    # Верните нужные вам данные о пользователе
    return UserAuth(
        Id=user_result.data[0]["Id"],
        Username=user_result.data[0]["Username"],
                    )


# Теперь создаём тип зависимости
UserDep = Annotated[UserAuth, Depends(get_current_user)]