from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class RecommendationBase(BaseModel):
    student_id: int
    title: str = Field(..., min_length=1, max_length=200)
    message: str
    category: str
    impact_level: str = "Medium"  # Low, Medium, High
    is_read: bool = False


class RecommendationCreate(RecommendationBase):
    pass


class RecommendationResponse(RecommendationBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
