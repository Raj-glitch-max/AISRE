from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)

    # Incident lifecycle
    status = Column(String, default="open", nullable=False)

    # Service that generated the incident
    service_name = Column(String, default="victim-app", nullable=False)

    # Incident timestamps
    opened_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Structured RCA fields populated by the SRE agent
    root_cause = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    evidence = Column(Text, nullable=True)
    recommended_action = Column(Text, nullable=True)
    risk = Column(String, nullable=True)
