from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from backend.app.core.config import settings


class Base(DeclarativeBase):
    pass


import sys
import os

# Configure engine based on database dialect (SQLite vs PostgreSQL)
engine_kwargs = {
    "echo": False,
    "future": True,
}

if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
elif "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
    from sqlalchemy.pool import NullPool
    engine_kwargs["poolclass"] = NullPool
else:
    # Enterprise PostgreSQL Connection Pool settings
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 1800

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session():
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


import logging

logger = logging.getLogger("wingman.database.session")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Pre-seed baseline distributed microservices
    standard_services = [
        ("api-gateway", "API Gateway", "Entrypoint gateway and routing layer"),
        ("checkout-service", "Checkout Service", "Order checkout orchestration"),
        ("order-service", "Order Service", "Order management & persistence"),
        ("payment-service", "Payment Service", "Payment gateway integration"),
        ("product-service", "Product Service", "Product catalog & inventory"),
        ("user-service", "User Service", "User identity and authentication"),
        ("notification-service", "Notification Service", "Async alerts & events"),
    ]
    try:
        from backend.app.models.models import ServiceModel
        from sqlalchemy import select
        async with async_session_factory() as session:
            async with session.begin():
                for svc_id, svc_name, svc_desc in standard_services:
                    existing = (await session.execute(select(ServiceModel).where(ServiceModel.id == svc_id))).scalar_one_or_none()
                    if not existing:
                        session.add(ServiceModel(
                            id=svc_id,
                            name=svc_name,
                            description=svc_desc,
                            status="healthy",
                            dependencies=[],
                        ))
    except Exception as e:
        logger.warning(f"Notice seeding baseline services: {e}")
