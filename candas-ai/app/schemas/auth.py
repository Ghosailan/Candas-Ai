from pydantic import BaseModel, Field
from app.models.enums import Role


class LocalTokenRequest(BaseModel):
    email: str
    name: str = Field(min_length=1, max_length=255)
    role: Role = Role.viewer
    org_name: str = Field(default='Local Dev Organisation', min_length=1, max_length=255)


class LocalTokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    user: dict
