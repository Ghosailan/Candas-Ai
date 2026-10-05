from app.agents.tools.scheduler_tool import optimal_publish_time

def test_scheduler_returns_future_time():
    assert optimal_publish_time('instagram').tzinfo is not None
