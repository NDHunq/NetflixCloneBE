from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Session

from app.db.database import Base


class SSOIdentity(Base):
    __tablename__ = "sso_identities"
    __table_args__ = (
        UniqueConstraint("provider", "subject", "profile_id", name="uq_provider_subject_profile"),
    )

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False, default="superapp")
    subject = Column(String(255), nullable=False, index=True)
    profile_id = Column(String(100), nullable=False, index=True)
    audience = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    gender = Column(String(50), nullable=True)
    local_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        return {
            "provider": self.provider,
            "subject": self.subject,
            "profile_id": self.profile_id,
            "audience": self.audience,
            "full_name": self.full_name,
            "gender": self.gender,
            "local_user_id": self.local_user_id,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }


def get_identity(db: Session, provider: str, subject: str, profile_id: str):
    return (
        db.query(SSOIdentity)
        .filter(
            SSOIdentity.provider == provider,
            SSOIdentity.subject == subject,
            SSOIdentity.profile_id == profile_id,
        )
        .first()
    )


def upsert_identity(
    db: Session,
    provider: str,
    subject: str,
    profile_id: str,
    audience: str,
    full_name: str,
    gender: str,
    local_user_id: int,
) -> SSOIdentity:
    identity = get_identity(db, provider=provider, subject=subject, profile_id=profile_id)

    if not identity:
        identity = SSOIdentity(
            provider=provider,
            subject=subject,
            profile_id=profile_id,
            local_user_id=local_user_id,
        )
        db.add(identity)

    identity.audience = audience
    identity.full_name = full_name
    identity.gender = gender
    identity.last_login_at = func.now()

    db.commit()
    db.refresh(identity)
    return identity
