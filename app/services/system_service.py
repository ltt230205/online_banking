from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.system_repository import SystemRepository


class SystemService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = SystemRepository(session)

    async def database_is_available(self) -> bool:
        return await self.repository.database_is_available()
