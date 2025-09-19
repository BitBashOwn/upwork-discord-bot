from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_id = Column(String, unique=True, index=True)
    title = Column(String)
    description = Column(Text)
    budget = Column(Float)
    skills = Column(Text)
    client = Column(String)
    posted_at = Column(DateTime, default=datetime.datetime.utcnow)
