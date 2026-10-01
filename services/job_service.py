from extensions import db
from models.job import Job, JobSkill
from models.skill import Skill


class JobService:
    """Service handling job requisitions and candidate criteria."""

    @staticmethod
    def get_active_jobs():
        return Job.query.filter_by(status="active").order_by(Job.created_at.desc()).all()

    @staticmethod
    def add_skill_requirement(job_id: int, skill_id: int, is_required: bool = True, weight: float = 1.0):
        js = JobSkill(job_id=job_id, skill_id=skill_id, is_required=is_required, importance_weight=weight)
        db.session.add(js)
        db.session.commit()
        return js
