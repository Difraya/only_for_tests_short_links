from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.session import get_db
from app.schemas.link import LinkCreate, LinkUpdate, LinkResponse
from app.models.link import Link
from app.models.user import User
from app.core.security import get_current_user
from datetime import datetime, timezone
from app.core.config import settings

router = APIRouter()
redirect_router = APIRouter()

@router.post("/shorten", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
async def create_short_link(
    link: LinkCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if link.custom_alias:
        existing_link = await Link.get_by_alias(db, link.custom_alias)
        if existing_link:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom alias already exists"
            )

    db_link = Link(
        original_url=str(link.original_url).rstrip('/'),
        custom_alias=link.custom_alias,
        user_id=current_user.id,
        expires_at=link.expires_at
    )
    
    if not db_link.custom_alias:
        while True:
            short_code = Link.generate_short_code()
            existing_link_by_code = await Link.get_by_short_code(db, short_code)
            if not existing_link_by_code:
                db_link.short_code = short_code
                break
    else:
        db_link.short_code = db_link.custom_alias
        
    await db_link.save(db) 
    
    response_data = {
        **db_link.__dict__, 
        "short_url": f"{request.base_url}{db_link.short_code}"
    }
    return response_data

@redirect_router.get("/{short_code}")
async def redirect_to_original(
    short_code: str,
    db: AsyncSession = Depends(get_db)
):
    link_row = await Link.get_by_short_code(db, short_code)
    if not link_row:
        link_row = await Link.get_by_alias(db, short_code)
        if not link_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

    link_id = link_row.id 

    result = await db.execute(select(Link).where(Link.id == link_id))
    link = result.scalar_one_or_none()

    if not link:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link inconsistency")


    if link.expires_at and link.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Link expired")

    link.clicks = (link.clicks or 0) + 1
    await link.save(db) 

    return RedirectResponse(url=str(link.original_url).rstrip('/'))

@router.get("/{short_code}/stats", response_model=LinkResponse)
async def get_link_stats(
    short_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Link).where((Link.short_code == short_code) | (Link.custom_alias == short_code))
    result = await db.execute(query)
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

    response_data = {
        "id": link.id,
        "original_url": str(link.original_url).rstrip('/'), 
        "short_code": link.short_code,
        "custom_alias": link.custom_alias,
        "user_id": link.user_id,
        "clicks": link.clicks or 0,
        "expires_at": link.expires_at,
        "created_at": link.created_at,
        "updated_at": link.updated_at,
        "short_url": f"{request.base_url}{link.short_code}"
    }
    return response_data

@router.put("/{short_code}", response_model=LinkResponse)
async def update_link(
    short_code: str,
    link_update: LinkUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Link).where((Link.short_code == short_code) | (Link.custom_alias == short_code))
    result = await db.execute(query)
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

    if link.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this link")

    link_data = link_update.model_dump(exclude_unset=True)
    for key, value in link_data.items():
        # Особо обрабатываем original_url, если он есть
        if key == 'original_url' and value is not None:
             setattr(link, key, str(value).rstrip('/')) 
        else:
            setattr(link, key, value)

    await link.save(db)

    response_data = {
        **link.__dict__,
        "short_url": f"{request.base_url}{link.short_code}",
        "original_url": str(link.original_url).rstrip('/')
    }
    return response_data

@router.delete("/{short_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Link).where((Link.short_code == short_code) | (Link.custom_alias == short_code))
    result = await db.execute(query)
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

    if link.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this link")

    await link.delete(db) 
    return 
