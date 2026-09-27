import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.notification_repository import NotificationRepository


logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.notifications = NotificationRepository(session)

    async def create_in_app(self, user_id: int, event_type: str, title: str, content: str) -> None:
        await self.notifications.create_in_app(user_id, event_type, title, content)

    def send_sms(self, destination: str, message: str) -> None:
        logger.info("Mock SMS sent to %s: %s", destination[-4:].rjust(len(destination), "*"), message)

    def send_email(self, destination: str, subject: str, message: str) -> None:
        logger.info("Mock email sent to %s (%s): %s", destination, subject, message)
