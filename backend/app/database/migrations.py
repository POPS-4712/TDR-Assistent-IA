"""
Database migration management for Automation Center.
Creates new database tables on application startup.
"""

import logging
from typing import List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Base

logger = logging.getLogger(__name__)

# SQL migrations
MIGRATIONS: List[str] = [
    # Create credentials table
    """
    CREATE TABLE IF NOT EXISTS credentials (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        provider TEXT NOT NULL,
        account_identifier TEXT NOT NULL,
        scopes TEXT[] NOT NULL DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'active',
        n8n_credential_id TEXT,
        last_refresh TIMESTAMPTZ,
        expires_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    # Extend existing credentials metadata without storing secret material.
    """
    ALTER TABLE credentials
    ADD COLUMN IF NOT EXISTS credential_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
    """,
    """
    ALTER TABLE credentials
    ADD COLUMN IF NOT EXISTS last_validation TIMESTAMPTZ
    """,
    # Create indexes for credentials
    """
    CREATE INDEX IF NOT EXISTS idx_credentials_provider ON credentials (provider)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_credentials_account ON credentials (account_identifier)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_credentials_status ON credentials (status)
    """,
    # Create automations table
    """
    CREATE TABLE IF NOT EXISTS automations (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        version TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'disabled',
        manifest_url TEXT,
        dependencies TEXT[] DEFAULT '{}',
        n8n_workflow_id TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    # Create automation_credentials table
    """
    CREATE TABLE IF NOT EXISTS automation_credentials (
        automation_id TEXT NOT NULL,
        credential_id UUID NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (automation_id, credential_id),
        FOREIGN KEY (automation_id) REFERENCES automations(id) ON DELETE CASCADE,
        FOREIGN KEY (credential_id) REFERENCES credentials(id) ON DELETE CASCADE
    )
    """,
    # Create executions table
    """
    CREATE TABLE IF NOT EXISTS executions (
        id TEXT PRIMARY KEY,
        automation_id TEXT NOT NULL,
        workflow_id TEXT,
        n8n_execution_id TEXT,
        status TEXT NOT NULL,
        started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        completed_at TIMESTAMPTZ,
        error_message TEXT,
        result_data JSONB,
        FOREIGN KEY (automation_id) REFERENCES automations(id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_executions_automation ON executions (automation_id, started_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_executions_status ON executions (status)
    """,
    # Create automation_center_settings table
    """
    CREATE TABLE IF NOT EXISTS automation_center_settings (
        key TEXT PRIMARY KEY,
        value JSONB NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    # Profile and personalization system. These tables intentionally contain only
    # metadata and preferences; credentials and secret material remain separate.
    """
    CREATE TABLE IF NOT EXISTS profiles (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(120) NOT NULL UNIQUE,
        description TEXT NOT NULL DEFAULT '',
        profession_name VARCHAR(160) NOT NULL DEFAULT '',
        profession_sector VARCHAR(160) NOT NULL DEFAULT '',
        profession_level VARCHAR(120) NOT NULL DEFAULT '',
        goals TEXT[] NOT NULL DEFAULT '{}',
        languages TEXT[] NOT NULL DEFAULT '{}',
        excluded_topics TEXT[] NOT NULL DEFAULT '{}',
        is_active BOOLEAN NOT NULL DEFAULT FALSE,
        is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_profiles_active_enabled
    ON profiles (is_active, is_enabled)
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_profiles_single_active
    ON profiles (is_active) WHERE is_active = TRUE
    """,
    """
    CREATE TABLE IF NOT EXISTS profile_preferences (
        profile_id UUID PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
        news_frequency VARCHAR(40) NOT NULL DEFAULT 'daily',
        relevance_level VARCHAR(40) NOT NULL DEFAULT 'high',
        sources TEXT[] NOT NULL DEFAULT '{}',
        preferred_schedule VARCHAR(120),
        notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
        additional_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS profile_interests (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        name VARCHAR(160) NOT NULL,
        weight INTEGER NOT NULL DEFAULT 5 CHECK (weight BETWEEN 1 AND 10),
        UNIQUE (profile_id, name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS profile_skills (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        name VARCHAR(160) NOT NULL,
        UNIQUE (profile_id, name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS profile_companies (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        name VARCHAR(160) NOT NULL,
        UNIQUE (profile_id, name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS profile_locations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        value VARCHAR(160) NOT NULL,
        country VARCHAR(120),
        city VARCHAR(120),
        region VARCHAR(120),
        remote BOOLEAN NOT NULL DEFAULT FALSE,
        UNIQUE (profile_id, value)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS profile_topics (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        name VARCHAR(160) NOT NULL,
        UNIQUE (profile_id, name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS profile_automations (
        profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        automation_id TEXT NOT NULL REFERENCES automations(id) ON DELETE CASCADE,
        enabled BOOLEAN NOT NULL DEFAULT TRUE,
        configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (profile_id, automation_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_profile_automations_profile_enabled
    ON profile_automations (profile_id, enabled)
    """,
    """
    CREATE TABLE IF NOT EXISTS profile_templates (
        id VARCHAR(120) PRIMARY KEY,
        name VARCHAR(160) NOT NULL UNIQUE,
        description TEXT NOT NULL DEFAULT '',
        icon VARCHAR(32) NOT NULL DEFAULT 'profile',
        template_data JSONB NOT NULL DEFAULT '{}'::jsonb,
        is_system BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_profile_templates_system
    ON profile_templates (is_system)
    """,
    # Phase 2.10 execution tracking remains metadata-only and is backwards compatible.
    """
    ALTER TABLE executions
    ADD COLUMN IF NOT EXISTS profile_id UUID REFERENCES profiles(id) ON DELETE SET NULL
    """,
    """
    ALTER TABLE executions
    ADD COLUMN IF NOT EXISTS duration_ms INTEGER
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_executions_profile ON executions (profile_id, started_at DESC)
    """,
]

async def run_migrations(session: AsyncSession) -> None:
    """Run all database migrations."""
    logger.info("Starting database migrations")
    
    for migration in MIGRATIONS:
        try:
            await session.execute(text(migration))
            logger.info(f"Migration executed successfully: {migration[:50]}...")
        except Exception as e:
            logger.error(f"Error executing migration: {e}")
            raise
    
    logger.info("All migrations completed successfully")

async def create_tables(session: AsyncSession) -> None:
    """Create all tables using SQLAlchemy models."""
    from sqlalchemy.ext.asyncio import AsyncEngine
    from sqlalchemy import text
    
    logger.info("Creating database tables")
    
    # Create metadata tables
    from .models import Base
    from .db import engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created successfully")