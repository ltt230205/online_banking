from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import scalar


class SystemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def database_is_available(self) -> bool:
        return await scalar(self.session, "SELECT 1") == 1
