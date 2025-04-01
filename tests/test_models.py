import pytest
import string

from app.models.link import Link
from app.models.user import User
from sqlalchemy import select
from app.core.hashing import get_password_hash

def test_generate_short_code():
    """Тест генерации короткого кода для Link."""
    code1 = Link.generate_short_code()

    # Проверка типа и длины по умолчанию
    assert isinstance(code1, str)
    assert len(code1) == 6

    # Проверка допустимых символов (буквы и цифры)
    allowed_chars = string.ascii_letters + string.digits
    assert all(char in allowed_chars for char in code1)

    # Проверка генерации с другой длиной
    code2_len = 8
    code2 = Link.generate_short_code(length=code2_len)
    assert isinstance(code2, str)
    assert len(code2) == code2_len
    assert all(char in allowed_chars for char in code2)

    # Проверка, что коды обычно разные (вероятностный тест)
    code3 = Link.generate_short_code()
    assert code1 != code3

@pytest.mark.asyncio
async def test_get_link_by_short_code_not_found(db_session):
    """Тест получения Link по несуществующему short_code."""
    non_existent_code = "nonexist"
    link = await Link.get_by_short_code(db_session, non_existent_code)
    assert link is None

@pytest.mark.asyncio
async def test_get_link_by_alias_not_found(db_session):
    """Тест получения Link по несуществующему alias."""
    non_existent_alias = "nonexist-alias"
    link = await Link.get_by_alias(db_session, non_existent_alias)
    assert link is None

@pytest.mark.asyncio
async def test_get_user_by_email_not_found(db_session):
    """Тест получения User по несуществующему email."""
    non_existent_email = "nonexistent@example.com"
    user = await User.get_by_email(db_session, non_existent_email)
    assert user is None

# --- Тесты для модели Link (продолжение) ---

@pytest.mark.asyncio
async def test_link_save_update(db_session):
    """Тест обновления существующей Link через метод save."""
    # 1. Создаем пользователя
    test_user = User(
        email="testsave@example.com",
        username="testsaveuser",
        hashed_password="somehash"
    )
    await test_user.save(db_session) # Сохраняем пользователя, чтобы получить ID

    # 2. Создаем и сохраняем ссылку (INSERT)
    original_url = "https://initial.com"
    link = Link(
        original_url=original_url,
        short_code="update_test",
        user_id=test_user.id
    )
    await link.save(db_session)
    assert link.id is not None
    assert str(link.original_url) == original_url

    # 3. Модифицируем ссылку
    updated_url = "https://updated.com"
    link.original_url = updated_url

    # 4. Сохраняем изменения (UPDATE)
    await link.save(db_session)

    # 5. Проверяем, что изменения сохранились в БД
    # Используем select для явной загрузки из БД
    stmt = select(Link).where(Link.id == link.id)
    result = await db_session.execute(stmt)
    updated_link = result.scalar_one_or_none()

    assert updated_link is not None
    assert str(updated_link.original_url) == updated_url

@pytest.mark.asyncio
async def test_link_delete(db_session):
    """Тест удаления Link через метод delete."""
    # 1. Создаем пользователя
    test_user = User(
        email="testdelete@example.com",
        username="testdeleteuser",
        hashed_password="somehash"
    )
    await test_user.save(db_session)

    # 2. Создаем и сохраняем ссылку
    link = Link(
        original_url="https://todelete.com",
        short_code="delete_test",
        user_id=test_user.id
    )
    await link.save(db_session)
    link_id = link.id
    assert link_id is not None

    # 3. Удаляем ссылку
    await link.delete(db_session)

    # 4. Проверяем, что ссылка удалена из БД
    stmt = select(Link).where(Link.id == link_id)
    result = await db_session.execute(stmt)
    deleted_link = result.scalar_one_or_none()
    assert deleted_link is None

# --- Тесты для модели User (продолжение) ---

@pytest.mark.asyncio
async def test_user_authenticate_success(db_session):
    """Тест успешной аутентификации пользователя."""
    password = "correctpassword"
    email = "auth_success@example.com"
    user = User(
        email=email,
        username="auth_success_user",
        hashed_password=get_password_hash(password)
    )
    await user.save(db_session)

    authenticated_user = await User.authenticate(db_session, email=email, password=password)
    assert authenticated_user is not None
    assert authenticated_user.id == user.id
    assert authenticated_user.email == email

@pytest.mark.asyncio
async def test_user_authenticate_wrong_password(db_session):
    """Тест аутентификации пользователя с неверным паролем."""
    password = "correctpassword"
    email = "auth_wrong_pass@example.com"
    user = User(
        email=email,
        username="auth_wrong_pass_user",
        hashed_password=get_password_hash(password)
    )
    await user.save(db_session)

    authenticated_user = await User.authenticate(db_session, email=email, password="wrongpassword")
    assert authenticated_user is None

@pytest.mark.asyncio
async def test_user_authenticate_non_existent_user(db_session):
    """Тест аутентификации несуществующего пользователя."""
    authenticated_user = await User.authenticate(db_session, email="nonexistent@authenticate.com", password="anypassword")
    assert authenticated_user is None 