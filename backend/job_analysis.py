from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime

from .database import Base


class JobAnalysis(Base):
    __tablename__ = "job_analysis"

    id = Column(Integer, primary_key=True, index=True)

    firebase_uid = Column(
        String,
        nullable=True
    )

    job_title = Column(
        String,
        nullable=False
    )

    job_url = Column(
        String,
        nullable=True
    )

    job_text = Column(
        Text,
        nullable=True
    )

    prediction = Column(
        String,
        nullable=True
    )

    risk_score = Column(
        Integer,
        nullable=True
    )

    reasons = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )