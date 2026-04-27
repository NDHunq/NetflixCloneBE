from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import Session
import hashlib
from typing import Optional
from uuid import UUID

from app.core.security import SecurityManager
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), index=True, nullable=False)  # NOT unique anymore (same user can have multiple profiles)
    full_name = Column(String(100), nullable=False)
    profile_id = Column(String(36), nullable=False)  # UUID string from SuperApp
    profile_name = Column(String(100), nullable=True)  # Display name of the profile
    hashed_password = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "phone_number": self.phone_number,
            "full_name": self.full_name,
            "profile_id": self.profile_id,
            "profile_name": self.profile_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def verify_password(self, password: str) -> bool:
        if self.hashed_password is None:
            return False  # SSO user cannot login with password
        return SecurityManager.verify_password(password, self.hashed_password)


def create_user(db: Session, phone_number: str, full_name: str, password: str, profile_id: str = "local", profile_name: str = "Local") -> User:
    user = User(
        phone_number=phone_number,
        full_name=full_name,
        profile_id=profile_id,
        profile_name=profile_name,
        hashed_password=SecurityManager.hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_phone(db: Session, phone_number: str):
    return db.query(User).filter(User.phone_number == phone_number).first()


def get_user_by_profile(db: Session, phone_number: str, profile_id: str):
    """Get user by (phone_number, profile_id) tuple for SSO"""
    return db.query(User).filter(
        User.phone_number == phone_number,
        User.profile_id == profile_id
    ).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def create_sso_user(
    db: Session,
    provider: str,
    subject: str,
    profile_id: str,
    full_name: str,
    profile_name: str,
    phone_number: str,
) -> User:
    """Create new Netflix user for this specific SuperApp profile"""
    # SSO users do not have password authentication - token only
    user = User(
        phone_number=phone_number,
        full_name=full_name or "SSO User",
        profile_id=profile_id,  # Store SuperApp profile UUID
        profile_name=profile_name,  # Store profile display name
        hashed_password=None,  # SSO user has no password
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
