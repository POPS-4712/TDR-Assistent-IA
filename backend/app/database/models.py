"""
SQLAlchemy models for Automation Center.
"""

import uuid
from datetime import datetime
from typing import List

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UUID,
    Boolean,
    Integer,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Credential(AsyncAttrs, Base):
    """Credential model - stores only metadata, NOT raw secrets."""
    __tablename__ = "credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(100), nullable=False, index=True)
    account_identifier = Column(String(255), nullable=False, index=True)
    scopes = Column(ARRAY(String), nullable=False, default=[])
    status = Column(String(50), nullable=False, default="active")
    n8n_credential_id = Column(String(255), nullable=True)
    credential_metadata = Column(JSONB, nullable=False, default=dict)
    last_refresh = Column(DateTime, nullable=True)
    last_validation = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_credentials_provider", "provider"),
        Index("idx_credentials_account", "account_identifier"),
        Index("idx_credentials_status", "status"),
    )

class Automation(AsyncAttrs, Base):
    """Automation model - stores metadata for automation configurations."""
    __tablename__ = "automations"

    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    version = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="disabled")
    manifest_url = Column(String(1000), nullable=True)
    dependencies = Column(ARRAY(String), nullable=False, default=[])
    n8n_workflow_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class AutomationCredential(AsyncAttrs, Base):
    """Association table for automation-credential relationships."""
    __tablename__ = "automation_credentials"

    automation_id = Column(String(255), ForeignKey("automations.id", ondelete="CASCADE"), primary_key=True)
    credential_id = Column(UUID(as_uuid=True), ForeignKey("credentials.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Execution(AsyncAttrs, Base):
    """Execution model - stores execution metadata."""
    __tablename__ = "executions"

    id = Column(String(255), primary_key=True)
    automation_id = Column(String(255), ForeignKey("automations.id"), nullable=False, index=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    workflow_id = Column(String(255), nullable=True)
    n8n_execution_id = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    result_data = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("idx_executions_automation", "automation_id", "started_at", "status"),
        Index("idx_executions_status", "status"),
    )

class AutomationCenterSetting(AsyncAttrs, Base):
    """Automation Center Setting model - stores non-sensitive configuration."""
    __tablename__ = "automation_center_settings"

    key = Column(String(255), primary_key=True)
    value = Column(JSONB, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

# Existing table - do not modify
class AssistantProcessedItem(AsyncAttrs, Base):
    """Existing assistant_processed_items table - preserved."""
    __tablename__ = "assistant_processed_items"

    item_key = Column(String(500), primary_key=True)
    source = Column(String(100), nullable=False)
    title = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=False, default="{}")
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Profile(AsyncAttrs, Base):
    """Local user profile with non-sensitive personalization metadata."""
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False, default="")
    profession_name = Column(String(160), nullable=False, default="")
    profession_sector = Column(String(160), nullable=False, default="")
    profession_level = Column(String(120), nullable=False, default="")
    goals = Column(ARRAY(String), nullable=False, default=[])
    languages = Column(ARRAY(String), nullable=False, default=[])
    excluded_topics = Column(ARRAY(String), nullable=False, default=[])
    is_active = Column(Boolean, nullable=False, default=False, index=True)
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_profiles_active_enabled", "is_active", "is_enabled"),
    )


class ProfilePreference(AsyncAttrs, Base):
    """Extensible and explicitly non-sensitive profile preferences."""
    __tablename__ = "profile_preferences"

    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    news_frequency = Column(String(40), nullable=False, default="daily")
    relevance_level = Column(String(40), nullable=False, default="high")
    sources = Column(ARRAY(String), nullable=False, default=[])
    preferred_schedule = Column(String(120), nullable=True)
    notifications_enabled = Column(Boolean, nullable=False, default=True)
    additional_settings = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ProfileInterest(AsyncAttrs, Base):
    """Weighted interest tag associated with a profile."""
    __tablename__ = "profile_interests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    weight = Column(Integer, nullable=False, default=5)

    __table_args__ = (
        Index("idx_profile_interests_profile_name", "profile_id", "name", unique=True),
    )


class ProfileSkill(AsyncAttrs, Base):
    """Skill tag associated with a profile."""
    __tablename__ = "profile_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(160), nullable=False)

    __table_args__ = (
        Index("idx_profile_skills_profile_name", "profile_id", "name", unique=True),
    )


class ProfileCompany(AsyncAttrs, Base):
    """Company or organization tag associated with a profile."""
    __tablename__ = "profile_companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(160), nullable=False)

    __table_args__ = (
        Index("idx_profile_companies_profile_name", "profile_id", "name", unique=True),
    )


class ProfileLocation(AsyncAttrs, Base):
    """Location preference associated with a profile."""
    __tablename__ = "profile_locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    value = Column(String(160), nullable=False)
    country = Column(String(120), nullable=True)
    city = Column(String(120), nullable=True)
    region = Column(String(120), nullable=True)
    remote = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_profile_locations_profile_value", "profile_id", "value", unique=True),
    )


class ProfileTopic(AsyncAttrs, Base):
    """Topic tag associated with a profile."""
    __tablename__ = "profile_topics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(160), nullable=False)

    __table_args__ = (
        Index("idx_profile_topics_profile_name", "profile_id", "name", unique=True),
    )


class ProfileAutomation(AsyncAttrs, Base):
    """Per-profile, non-secret configuration for an existing automation."""
    __tablename__ = "profile_automations"

    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    automation_id = Column(String(255), ForeignKey("automations.id", ondelete="CASCADE"), primary_key=True)
    enabled = Column(Boolean, nullable=False, default=True)
    configuration = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_profile_automations_profile_enabled", "profile_id", "enabled"),
    )


class ProfileTemplate(AsyncAttrs, Base):
    """Built-in or user-defined non-sensitive starting point for profiles."""
    __tablename__ = "profile_templates"

    id = Column(String(120), primary_key=True)
    name = Column(String(160), nullable=False, unique=True)
    description = Column(Text, nullable=False, default="")
    icon = Column(String(32), nullable=False, default="profile")
    template_data = Column(JSONB, nullable=False, default=dict)
    is_system = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_profile_templates_system", "is_system"),
    )
