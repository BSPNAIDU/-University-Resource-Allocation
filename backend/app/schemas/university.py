from pydantic import BaseModel, Field, EmailStr, ConfigDict


class UniversityRegister(BaseModel):
    university_name: str = Field(..., min_length=3, max_length=200)
    university_code: str = Field(..., min_length=3, max_length=50)
    address: str | None = None
    city: str | None = None
    state: str | None = None
    password: str = Field(..., min_length=8, max_length=72)


class UniversityLogin(BaseModel):
    university_code: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=72)


class UniversityResponse(BaseModel):
    id: int
    university_name: str
    university_code: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    university: UniversityResponse
