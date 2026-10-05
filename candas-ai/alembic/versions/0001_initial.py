"""initial schema with pgvector

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    role_enum = postgresql.ENUM('viewer', 'editor', 'approver', 'admin', name='role_enum', create_type=False)
    plan_enum = postgresql.ENUM('free', 'pro', 'enterprise', name='plan_enum', create_type=False)
    campaign_status_enum = postgresql.ENUM('draft', 'active', 'paused', 'completed', 'failed', name='campaign_status_enum', create_type=False)
    platform_enum = postgresql.ENUM('instagram', 'twitter', 'linkedin', 'tiktok', 'facebook', 'youtube', name='platform_enum', create_type=False)
    post_status_enum = postgresql.ENUM('draft', 'approved', 'rejected', 'scheduled', 'published', 'failed', name='post_status_enum', create_type=False)
    approval_decision_enum = postgresql.ENUM('approved', 'rejected', name='approval_decision_enum', create_type=False)
    publishing_status_enum = postgresql.ENUM('scheduled', 'published', 'failed', name='publishing_status_enum', create_type=False)

    role_enum.create(op.get_bind(), checkfirst=True)
    plan_enum.create(op.get_bind(), checkfirst=True)
    campaign_status_enum.create(op.get_bind(), checkfirst=True)
    platform_enum.create(op.get_bind(), checkfirst=True)
    post_status_enum.create(op.get_bind(), checkfirst=True)
    approval_decision_enum.create(op.get_bind(), checkfirst=True)
    publishing_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table('organisations', sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True), sa.Column('name', sa.String(255), nullable=False), sa.Column('plan', plan_enum, nullable=False, server_default='free'), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table('users', sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True), sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organisations.id', ondelete='CASCADE'), nullable=False), sa.Column('email', sa.String(255), nullable=False), sa.Column('name', sa.String(255), nullable=False), sa.Column('role', role_enum, nullable=False), sa.Column('auth_provider_id', sa.String(255), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_unique_constraint('uq_users_org_email', 'users', ['org_id','email'])
    op.create_index('ix_users_org_id', 'users', ['org_id'])
    op.create_table('campaigns', sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True), sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organisations.id', ondelete='CASCADE'), nullable=False), sa.Column('title', sa.String(255), nullable=False), sa.Column('brief', sa.Text, nullable=False), sa.Column('goals', postgresql.JSONB, nullable=False, server_default='[]'), sa.Column('target_audience', postgresql.JSONB, nullable=False, server_default='{}'), sa.Column('platforms', postgresql.ARRAY(sa.String), nullable=False), sa.Column('status', campaign_status_enum, nullable=False), sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False), sa.Column('thread_id', sa.String(255), unique=True), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index('ix_campaigns_org_id', 'campaigns', ['org_id'])
    op.create_table('posts', sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True), sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('campaign_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False), sa.Column('platform', platform_enum, nullable=False), sa.Column('copy', sa.Text, nullable=False), sa.Column('image_prompt', sa.Text), sa.Column('image_url', sa.Text), sa.Column('status', post_status_enum, nullable=False), sa.Column('variant', sa.CHAR(1)), sa.Column('compliance_flags', postgresql.JSONB, nullable=False, server_default='{}'), sa.Column('reflection_score', sa.Float), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index('ix_posts_org_id', 'posts', ['org_id']); op.create_index('ix_posts_campaign_id', 'posts', ['campaign_id'])
    op.create_table('approvals', sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True), sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('post_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('posts.id', ondelete='CASCADE')), sa.Column('campaign_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campaigns.id', ondelete='CASCADE')), sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False), sa.Column('decision', approval_decision_enum, nullable=False), sa.Column('feedback', sa.Text), sa.Column('decided_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table('publishing_logs', sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True), sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('post_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('posts.id', ondelete='CASCADE'), nullable=False), sa.Column('platform', platform_enum, nullable=False), sa.Column('platform_post_id', sa.Text), sa.Column('platform_post_url', sa.Text), sa.Column('status', publishing_status_enum, nullable=False), sa.Column('error_message', sa.Text), sa.Column('published_at', sa.DateTime(timezone=True)), sa.Column('scheduled_at', sa.DateTime(timezone=True)))
    op.create_table('analytics', sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True), sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('post_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('posts.id', ondelete='CASCADE'), nullable=False), sa.Column('platform', platform_enum, nullable=False), sa.Column('impressions', sa.Integer, server_default='0'), sa.Column('clicks', sa.Integer, server_default='0'), sa.Column('engagement_rate', sa.Float, server_default='0'), sa.Column('reach', sa.Integer, server_default='0'), sa.Column('conversions', sa.Integer, server_default='0'), sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table('campaign_embeddings', sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True), sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('campaign_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campaigns.id', ondelete='SET NULL')), sa.Column('content', sa.Text, nullable=False), sa.Column('embedding', sa.Text), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.execute('ALTER TABLE campaign_embeddings ALTER COLUMN embedding TYPE vector(1536) USING NULL')
    op.execute('CREATE INDEX IF NOT EXISTS ix_campaign_embeddings_hnsw ON campaign_embeddings USING hnsw (embedding vector_cosine_ops)')


def downgrade():
    op.drop_table('campaign_embeddings'); op.drop_table('analytics'); op.drop_table('publishing_logs'); op.drop_table('approvals'); op.drop_table('posts'); op.drop_table('campaigns'); op.drop_table('users'); op.drop_table('organisations')
    for name in ['publishing_status_enum','approval_decision_enum','post_status_enum','platform_enum','campaign_status_enum','plan_enum','role_enum']:
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
