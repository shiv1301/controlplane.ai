from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    # Alembic handles schema creation, but we could do engine.begin() here if we wanted
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
