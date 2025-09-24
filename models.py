from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, DateTime, Text, Boolean

db = SQLAlchemy()


class Search(db.Model):
    __tablename__ = "searches"

    id = db.Column(Integer, primary_key=True)
    search_type = db.Column(String(32), nullable=False)

    # Inputs
    username = db.Column(String(80))
    subreddit = db.Column(String(120))
    keywords = db.Column(String(500))
    period_days = db.Column(Integer)
    limit_value = db.Column(Integer)
    captions_only = db.Column(Boolean)

    # Results stored as JSON string
    results_json = db.Column(Text, nullable=False)

    created_at = db.Column(DateTime, nullable=False)



