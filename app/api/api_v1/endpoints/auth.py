from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.auth import UserCreate, UserResponse, Token
from app.models.user import User
from app.core.hashing import get_password_hash
from app.core.security import get_current_user

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Проверяем, существует ли пользователь
    existing_user = await User.get_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Создаем нового пользователя
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        username=user.username
    )
    
    try:
        await db_user.save(db)
        
        # Получаем полного пользователя из БД, чтобы Pydantic мог корректно его обработать
        result = await db.execute(select(User).where(User.id == db_user.id))
        created_user = result.scalar_one_or_none()
        
        if not created_user:
            # Это не должно произойти, но на всякий случай
            raise HTTPException(status_code=500, detail="Could not retrieve created user")
            
        return created_user
    except Exception as e:
        # Обрабатываем любые исключения при сохранении
        raise HTTPException(status_code=500, detail="Error saving user to database")

@router.post("/jwt/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    user_record = await User.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Создаем User объект из записи, полученной из БД
    # SQLAlchemy 2.0 возвращает Row объект, который нужно преобразовать
    user_dict = dict(user_record._mapping) 
    current_user = User(**user_dict)
    
    access_token = create_access_token(data={"sub": current_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# Добавляем тестовый эндпоинт для проверки аутентификации
@router.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Возвращает информацию о текущем пользователе."""
    return current_user