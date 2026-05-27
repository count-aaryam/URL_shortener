from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.schemas.user import UserRegisterRequest


class AuthService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, payload: UserRegisterRequest) -> User:
        # Check email not already taken
        existing = await self._get_by_email(payload.email)
        if existing:
            raise ValueError("Email already registered")

        # Check username not already taken
        existing = await self._get_by_username(payload.username)
        if existing:
            raise ValueError("Username already taken")

        user = User(
            email=payload.email,
            username=payload.username,
            hashed_password=hash_password(payload.password),
        )

        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def login(self, email: str, password: str) -> tuple[User, str]:
        user = await self._get_by_email(email)

        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("Account is deactivated")

        token = create_access_token(user_id=user.id, email=user.email)
        return user, token

    async def get_user_by_id(self, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id, User.is_active == True)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()