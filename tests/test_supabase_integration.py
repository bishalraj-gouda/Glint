import pytest
from app import create_app
from extensions import db
from models.user import User
from models.student import Student
from models.company import Company
from models.job import Job
from models.ai_interview_session import AIInterviewSession, InterviewQuestion, InterviewAnswer, AIEvaluation
from models.resume import Resume
from models.career_goal import CareerGoal, SkillGapRecord, LearningRecommendation, JobMatch, AIActivityLog
from services.ai.interview_ai_service import InterviewAIService
from data.seed_data import seed_database


@pytest.fixture
def app_instance():
    """Create test application with in-memory SQLite for high-speed isolated validation."""
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        seed_database()
        yield app
        db.session.remove()
        db.drop_all()


def test_schema_models_completeness(app_instance):
    """Verify that all newly introduced models exist and can be persisted."""
    with app_instance.app_context():
        student = Student.query.first()
        assert student is not None, "Seed student must exist"

        # 1. Resume model
        resume = Resume(
            student_id=student.id,
            filename="Test_Resume.pdf",
            file_url="https://supabase.co/storage/v1/resumes/test.pdf",
            parsed_data={"skills": ["Python", "SQL"]}
        )
        db.session.add(resume)

        # 2. CareerGoal model
        goal = CareerGoal(
            student_id=student.id,
            target_role="Full Stack Architect",
            target_company="Nexus Technologies",
            target_industry="FinTech",
            target_skills="FastAPI, React, Kubernetes"
        )
        db.session.add(goal)

        # 3. SkillGapRecord
        gap = SkillGapRecord(
            student_id=student.id,
            target_role="Data Scientist",
            skill="TensorFlow",
            current_level="beginner",
            required_level="advanced",
            gap_score=65.0,
            recommendation="Build deep learning computer vision projects."
        )
        db.session.add(gap)

        # 4. LearningRecommendation
        rec = LearningRecommendation(
            student_id=student.id,
            skill="PostgreSQL",
            recommendation="Master indexing, EXPLAIN ANALYZE, and connection pooling.",
            resource_url="https://postgresqltutorial.com",
            priority="high",
            status="pending"
        )
        db.session.add(rec)

        # 5. JobMatch
        job = Job.query.first()
        assert job is not None
        match = JobMatch(
            student_id=student.id,
            job_id=job.id,
            match_score=92.5,
            explanation="Strong overlap in backend API development."
        )
        db.session.add(match)

        # 6. AIActivityLog
        log = AIActivityLog(
            student_id=student.id,
            action_type="interview_simulation",
            input_reference="session_start",
            result_summary="Generated 4 questions for SDE role."
        )
        db.session.add(log)

        db.session.commit()

        # Verify relationships
        reloaded_student = Student.query.get(student.id)
        assert len(reloaded_student.resumes) >= 1
        assert len(reloaded_student.career_goals) >= 1
        assert len(reloaded_student.skill_gap_analyses) >= 1
        assert len(reloaded_student.learning_recommendations) >= 1
        assert len(reloaded_student.job_matches) >= 1
        assert len(reloaded_student.ai_activity_logs) >= 1


def test_interview_simulator_relational_persistence(app_instance):
    """Verify that InterviewAIService persists questions, answers, and evaluations into relational tables."""
    with app_instance.app_context():
        student = Student.query.first()
        assert student is not None

        # 1. Start Session
        res = InterviewAIService.start_session(
            student_id=student.id,
            role_title="Senior Python Backend Engineer",
            interview_type="technical"
        )
        session_id = res.get("session_id")
        assert session_id is not None
        assert res.get("total_questions") > 0

        # Verify session and questions created in DB
        session = db.session.get(AIInterviewSession, session_id)
        assert session is not None
        assert len(session.questions) == res["total_questions"]
        first_q = session.questions[0]
        assert first_q.question_number == 1
        assert len(first_q.question) > 10

        # 2. Submit Answer
        ans_res = InterviewAIService.submit_answer(
            session_id=session_id,
            answer_text="B-Tree indexes speed up lookups from O(N) to O(log N) by maintaining a balanced search tree, but incur overhead on writes because the tree nodes must be rebalanced and updated."
        )
        assert ans_res.get("evaluation") is not None

        # Verify answer and evaluation rows in DB
        answers = InterviewAnswer.query.filter_by(session_id=session_id).all()
        assert len(answers) == 1
        eval_row = AIEvaluation.query.filter_by(answer_id=answers[0].id).first()
        assert eval_row is not None
        assert eval_row.overall_score >= 0
        assert eval_row.technical_accuracy >= 0
        assert eval_row.communication_clarity >= 0
        assert eval_row.depth_completeness >= 0
