from datetime import date, datetime, timezone

from app.api.schemas.enums import InputStatus, InputType
from app.models import Input


class InputService:
    def build_voice_input(
        self,
        original_filename: str,
        station_id: str | None = None,
        responder_badge: str | None = None,
        incident_date_hint: date | None = None,
    ) -> Input:
        now = datetime.now(timezone.utc)
        return Input(
            input_type=InputType.voice,
            status=InputStatus.queued,
            original_filename=original_filename,
            station_id=station_id,
            responder_badge=responder_badge,
            incident_date_hint=incident_date_hint,
            created_at=now,
            updated_at=now,
        )

    def build_text_input(
        self,
        narrative: str,
        station_id: str | None = None,
        responder_badge: str | None = None,
        incident_date_hint: date | None = None,
    ) -> Input:
        words = narrative.split()
        if len(words) < 10:
            raise ValueError("Must contain at least 10 words")
        now = datetime.now(timezone.utc)
        return Input(
            input_type=InputType.text,
            status=InputStatus.ready,
            transcript=narrative,
            character_count=len(narrative),
            word_count=len(words),
            station_id=station_id,
            responder_badge=responder_badge,
            incident_date_hint=incident_date_hint,
            created_at=now,
            updated_at=now,
        )
