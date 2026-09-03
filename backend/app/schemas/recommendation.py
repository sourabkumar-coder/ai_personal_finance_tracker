from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class RecommendationBase(BaseModel):
    student_id: int = Field(..., gt=0, examples=[1])
    title: str = Field(..., min_length=1, max_length=200, examples=["Budget Exceeded in Food"])
    message: str = Field(..., examples=["You have spent 95% of your food budget limit."])
    category: str = Field(..., examples=["Food"])
    impact_level: str = Field("Medium", examples=["High"])  # Low, Medium, High
    is_read: bool = Field(False, examples=[False])


class RecommendationCreate(RecommendationBase):
    pass


class RecommendationResponse(RecommendationBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
