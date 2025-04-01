from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, text
from sqlalchemy.sql import func
from app.db.base import Base
import random
import string

class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String)
    short_code = Column(String, unique=True, index=True)
    custom_alias = Column(String, unique=True, index=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    clicks = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @classmethod
    def generate_short_code(cls, length: int = 6) -> str:
        """Генерирует случайный короткий код"""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    @classmethod
    async def get_by_short_code(cls, db, short_code: str):
        result = await db.execute(
            text("SELECT * FROM links WHERE short_code = :short_code"),
            {"short_code": short_code}
        )
        return result.first()

    @classmethod
    async def get_by_alias(cls, db, alias: str):
        result = await db.execute(
            text("SELECT * FROM links WHERE custom_alias = :alias"),
            {"alias": alias}
        )
        return result.first()

    async def save(self, db):
        if not self.id:
            # Генерируем короткий код, если его нет
            if not self.short_code:
                self.short_code = self.generate_short_code()
            
            result = await db.execute(
                text("""
                INSERT INTO links (
                    original_url, short_code, custom_alias, user_id,
                    clicks, expires_at
                )
                VALUES (
                    :original_url, :short_code, :custom_alias, :user_id,
                    :clicks, :expires_at
                )
                RETURNING id
                """),
                {
                    "original_url": str(self.original_url),  # Преобразуем Url в строку
                    "short_code": self.short_code,
                    "custom_alias": self.custom_alias,
                    "user_id": self.user_id,
                    "clicks": self.clicks,
                    "expires_at": self.expires_at
                }
            )
            self.id = result.scalar()
        else:
            await db.execute(
                text("""
                UPDATE links
                SET original_url = :original_url,
                    custom_alias = :custom_alias,
                    clicks = :clicks,
                    expires_at = :expires_at,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """),
                {
                    "id": self.id,
                    "original_url": str(self.original_url), # Преобразуем Url в строку
                    "custom_alias": self.custom_alias,
                    "clicks": self.clicks,
                    "expires_at": self.expires_at
                }
            )
        await db.commit()

    async def delete(self, db):
        await db.execute(
            text("DELETE FROM links WHERE id = :id"),
            {"id": self.id}
        )
        await db.commit() 