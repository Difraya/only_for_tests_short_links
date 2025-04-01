import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, AsyncSessionLocal, engine
from app.models.user import User
from sqlalchemy import select
from app.db.base import Base

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Создаем таблицы перед тестами и удаляем после."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_get_db_success():
    """Тест успешного получения и закрытия сессии БД."""
    async for session in get_db():
        assert isinstance(session, AsyncSession)
        # Проверяем, что сессия работает
        result = await session.execute(select(1))
        assert result.scalar_one() == 1

@pytest.mark.asyncio
async def test_get_db_error_handling():
    """Тест обработки ошибок при работе с сессией БД."""
    try:
        async for session in get_db():
            assert isinstance(session, AsyncSession)
            raise Exception("Test error")
    except Exception as e:
        assert str(e) == "Test error"
    
    async for session in get_db():
        assert isinstance(session, AsyncSession)
        result = await session.execute(select(1))
        assert result.scalar_one() == 1

@pytest.mark.asyncio
async def test_session_commit_rollback():
    """Тест транзакций в сессии БД."""
    async for session in get_db():
        test_user = User(
            email="session_test@example.com",
            username="sessionuser",
            hashed_password="testhash"
        )
        session.add(test_user)
        await session.commit()

        result = await session.execute(
            select(User).where(User.email == "session_test@example.com")
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.email == "session_test@example.com"

        duplicate_user = User(
            email="session_test@example.com",
            username="sessionuser2",
            hashed_password="testhash2"
        )
        session.add(duplicate_user)
        try:
            await session.commit()
        except:
            await session.rollback()

        result = await session.execute(
            select(User).where(User.username == "sessionuser2")
        )
        assert result.scalar_one_or_none() is None 
