import uuid
from datetime import datetime, timezone

from app import db


class AIRequest(db.Model):
    __tablename__ = 'ai_requests'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    task = db.Column(db.String(100), nullable=False)
    input_text = db.Column(db.Text)
    provider = db.Column(db.String(50))
    latency_ms = db.Column(db.Integer)
    status = db.Column(db.String(20))
    result_summary = db.Column(db.Text)
    user_id = db.Column(db.String(100), default='anonymous')
    error_message = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'task': self.task,
            'input_text': self.input_text,
            'provider': self.provider,
            'latency_ms': self.latency_ms,
            'status': self.status,
            'result_summary': self.result_summary,
            'user_id': self.user_id,
            'error_message': self.error_message,
        }


def init_db():
    db.create_all()
