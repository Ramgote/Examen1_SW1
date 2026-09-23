from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool
from app.api.deps import current_user
from app.core.database import get_db
from app.core.security import create_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import LoginInput, RegisterInput, TokenRead, UserRead

router = APIRouter(prefix="/auth", tags=["Autenticación"])
# Un hash de trabajo evita omitir el coste de verificación para correos inexistentes.
DUMMY_HASH = hash_password("dummy-password-not-an-account")


@router.post("/register", response_model=UserRead, status_code=201)
async def register(data: RegisterInput, db: AsyncSession = Depends(get_db, scope="function")):
    user = User(email=data.email, full_name=data.full_name,
                hashed_password=await run_in_threadpool(hash_password, data.password))
    try:
        async with db.begin_nested():
            db.add(user)
            await db.flush()
    except IntegrityError:
        raise HTTPException(409, "El correo ya está registrado")
    return user


@router.post("/login", response_model=TokenRead)
async def login(data: LoginInput, db: AsyncSession = Depends(get_db, scope="function")):
    user = await db.scalar(select(User).where(User.email == data.email))
    valid = await run_in_threadpool(verify_password, data.password,
                                   user.hashed_password if user else DUMMY_HASH)
    if not valid or user is None or not user.is_active:
        raise HTTPException(401, "Correo o contraseña incorrectos", headers={"WWW-Authenticate": "Bearer"})
    return TokenRead(access_token=create_token(user.id))


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(current_user)):
    return user
