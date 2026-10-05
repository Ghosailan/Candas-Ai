from locust import HttpUser, task, between

class CampaignUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def create_campaign(self):
        self.client.post('/v1/campaigns', json={
            'title': 'Load test campaign',
            'brief': 'Promote a new AI productivity app for small teams.',
            'platforms': ['instagram', 'linkedin'],
            'goals': ['awareness'],
            'target_audience': {'segment': 'small business owners'},
        }, headers={'Authorization': 'Bearer test-token'})
