from structlog import get_logger
log = get_logger()

async def notify_approval_required(campaign_id: str, org_id: str) -> None:
    log.info('approval_required_notification', campaign_id=campaign_id, org_id=org_id)
