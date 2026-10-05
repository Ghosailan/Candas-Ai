from enum import Enum

class Role(str, Enum):
    viewer = 'viewer'
    editor = 'editor'
    approver = 'approver'
    admin = 'admin'

class Plan(str, Enum):
    free = 'free'
    pro = 'pro'
    enterprise = 'enterprise'

class CampaignStatus(str, Enum):
    draft = 'draft'
    active = 'active'
    paused = 'paused'
    completed = 'completed'
    failed = 'failed'

class Platform(str, Enum):
    instagram = 'instagram'
    twitter = 'twitter'
    linkedin = 'linkedin'
    tiktok = 'tiktok'
    facebook = 'facebook'
    youtube = 'youtube'
    telegram = 'telegram'

class PostStatus(str, Enum):
    draft = 'draft'
    approved = 'approved'
    rejected = 'rejected'
    scheduled = 'scheduled'
    published = 'published'
    failed = 'failed'

class ApprovalDecision(str, Enum):
    approved = 'approved'
    rejected = 'rejected'

class PublishingStatus(str, Enum):
    scheduled = 'scheduled'
    published = 'published'
    failed = 'failed'

class WebhookEventType(str, Enum):
    trend_spike = 'trend.spike'
    competitor_post = 'competitor.post'
    schedule_trigger = 'schedule.trigger'
    approval_decision = 'approval.decision'
