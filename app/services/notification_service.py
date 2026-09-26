import logging

from sqlalchemy.orm import Session

from app.models.entities import Notification


logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_in_app(self, user_id: int, event_type: str, title: str, content: str) -> None:
        self.session.add(
            Notification(
                user_id=user_id,
                notification_type="IN_APP",
                event_type=event_type,
                title=title,
                content=content,
                status="SENT",
            )
        )

    def send_sms(self, destination: str, message: str) -> None:
        logger.info("Mock SMS sent to %s: %s", destination[-4:].rjust(len(destination), "*"), message)

    def send_email(self, destination: str, subject: str, message: str) -> None:
        logger.info("Mock email sent to %s (%s): %s", destination, subject, message)
