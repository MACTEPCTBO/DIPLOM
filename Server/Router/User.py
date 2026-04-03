from fastapi import APIRouter


user_router = APIRouter(prefix="/user", tags=["User"])


@user_router.post("/register")
async def register(data):...