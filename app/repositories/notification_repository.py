from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import execute


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_in_app(self, user_id: int, event_type: str, title: str, content: str) -> None:
        await execute(
            self.session,
            "INSERT INTO notifications(user_id, notification_type, event_type, title, content, status) "
            "VALUES (:user_id, 'IN_APP', :event_type, :title, :content, 'SENT')",
            {"user_id": user_id, "event_type": event_type, "title": title, "content": content},
        )
