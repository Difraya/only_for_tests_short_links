import asyncio
import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings
from app.db.base import Base
from app.main import app
from app.db.session import get_db

settings = Settings(_env_file=".env.test")

TEST_DATABASE_URL = f"sqlite+aiosqlite:///./test_{uuid.uuid4()}.db"
engine = create_async_engine(TEST_DATABASE_URL, echo=False) 
TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

@pytest_asyncio.fixture(scope="session")
async def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def prepare_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(prepare_database):
    async with TestingSessionLocal() as session:
        yield session

@pytest_asyncio.fixture
async def test_client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def test_user(db_session):
    from app.models.user import User
    from app.core.hashing import get_password_hash
    
    user_uuid = uuid.uuid4()
    user = User(
        email=f"test_{user_uuid}@example.com",
        hashed_password=get_password_hash("testpass123"),
        username=f"testuser_{user_uuid}"
    )
    await user.save(db_session)
    return {"id": user.id, "email": user.email, "username": user.username}

@pytest_asyncio.fixture
async def test_user2(db_session):
    from app.models.user import User
    from app.core.hashing import get_password_hash
    
    user = User(
        email=f"test2_{uuid.uuid4()}@example.com",
        hashed_password=get_password_hash("testpass123"),
        username=f"testuser2_{uuid.uuid4()}"
    )
    await user.save(db_session)
    return {"id": user.id, "email": user.email, "username": user.username}

@pytest_asyncio.fixture
async def test_user_token(test_user):
    from app.core.security import create_access_token
    return create_access_token(data={"sub": test_user["email"]})

@pytest_asyncio.fixture
async def test_link_factory(db_session):
    from app.models.link import Link
    from datetime import datetime, timezone, timedelta
    
    async def create_link(
        user_id,
        original_url="https://example.com",
        custom_alias=None,
        expires_at=None
    ):
        link = Link(
            original_url=original_url,
            custom_alias=custom_alias,
            user_id=user_id,
            expires_at=expires_at,
            short_code=Link.generate_short_code() if not custom_alias else custom_alias
        )
        await link.save(db_session)
        return link
    
    return create_link 
