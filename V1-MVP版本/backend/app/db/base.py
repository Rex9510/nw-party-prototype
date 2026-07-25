"""所有模型 import 入口（Alembic 用）。"""
from app.db.session import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.party import Street, Community, Branch  # noqa: F401
from app.models.member import Member, MemberImport  # noqa: F401
from app.models.activity import (  # noqa: F401
    Activity,
    ActivityAttachment,
    ActivityParticipant,
)
from app.models.audit import AuditFlow, AuditLog  # noqa: F401
from app.models.study import StudyHour  # noqa: F401
from app.models.dict import Lecturer, TrainingCategory, TrainingSource  # noqa: F401
