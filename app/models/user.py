from sqlalchemy import Column, Integer, String, DateTime, text
from sqlalchemy.sql import func
from app.db.base import Base
from app.core.hashing import verify_password

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @classmethod
    async def get_by_email(cls, db, email: str):
        result = await db.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {"email": email}
        )
        return result.first()

    @classmethod
    async def authenticate(cls, db, email: str, password: str):
        user = await cls.get_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def save(self, db):
        if not self.id:
            result = await db.execute(
                text("""
                INSERT INTO users (email, username, hashed_password)
                VALUES (:email, :username, :hashed_password)
                RETURNING id
                """),
                {
                    "email": self.email,
                    "username": self.username,
                    "hashed_password": self.hashed_password
                }
            )
            self.id = result.scalar()
        else:
            await db.execute(
                text("""
                UPDATE users
                SET email = :email,
                    username = :username,
                    hashed_password = :hashed_password,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """),
                {
                    "id": self.id,
                    "email": self.email,
                    "username": self.username,
                    "hashed_password": self.hashed_password
                }
            )
        await db.commit()

    async def delete(self, db):
        await db.execute(
            text("DELETE FROM users WHERE id = :id"),
            {"id": self.id}
        )
        await db.commit()