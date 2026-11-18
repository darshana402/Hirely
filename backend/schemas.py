from pydantic import BaseModel


class JobAnalysisRequest(BaseModel):

    title: str
    url: str
    text: str


class UserCreate(BaseModel):

    firebase_uid: str
    name: str
    email: str


class JobAnalysisResponse(BaseModel):

    id: int
    prediction: str
    risk_score: int
    reasons: list