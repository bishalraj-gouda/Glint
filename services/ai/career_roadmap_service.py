"""
AI Career Roadmap Service for Campus-Link.
Synthesizes personalized, timeline-based learning journeys (7, 30, 60, 90 days)
targeting a student's exact skill deficits and placement goals.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from extensions import db
from models.student import Student
from models.ai_roadmap import AIRoadmap
from services.ai.skill_gap_service import SkillGapService
from services.ai.gemini_client import get_gemini_client


class CareerRoadmapService:
    """Manages generation, progress tracking, and persistence of AI learning roadmaps."""

    @staticmethod
    def get_or_generate_roadmap(student_id: int, target_role: Optional[str] = None, regenerate: bool = False) -> Dict[str, Any]:
        """Retrieves existing active roadmap or creates a new targeted roadmap."""
        student = db.session.get(Student, student_id)
        if not student:
            return {"error": "Student not found"}

        existing = AIRoadmap.query.filter_by(student_id=student_id, is_active=True).first()
        if existing and not regenerate:
            if not target_role or existing.target_role.lower() == target_role.lower():
                return CareerRoadmapService._serialize_roadmap(existing)

        # Deactivate previous active roadmap if regenerating
        if existing:
            existing.is_active = False
            db.session.commit()

        return CareerRoadmapService._create_roadmap(student, target_role)

    @staticmethod
    def _create_roadmap(student: Student, target_role: Optional[str] = None) -> Dict[str, Any]:
        """Uses SkillGap analysis + Gemini to construct an adaptive multi-phase roadmap."""
        gap_analysis = SkillGapService.analyze_skill_gaps(student.id, target_role=target_role)
        resolved_role = gap_analysis.get("benchmark_role", "Software Development Engineer")
        missing_skills = gap_analysis.get("missing_skills", ["Docker", "REST APIs", "System Design"])
        matched_skills = [m["name"] for m in gap_analysis.get("matched_skills", [])]

        prompt = f"""
You are the Lead Technical Mentor for the Glint Career Acceleration Program.
Design a high-yield, structured 4-phase placement preparation roadmap for student {student.full_name}.

Candidate Context:
- Target Role: {resolved_role}
- Current Department: {student.department}, Year: {student.year}
- Known Foundation Skills: {', '.join(matched_skills[:5]) if matched_skills else 'Basic programming'}
- Critical Gaps to Bridge: {', '.join(missing_skills[:5]) if missing_skills else 'Advanced system design, cloud'}

Create a structured 4-phase roadmap covering:
Phase 1: Sprint 1 (Days 1-14) - Core Gap Elimination & Practical Syntax
Phase 2: Sprint 2 (Days 15-30) - Advanced Architecture & Database Optimization
Phase 3: Sprint 3 (Days 31-60) - Capstone Production Project with Testing & Deployment
Phase 4: Sprint 4 (Days 61-90) - Placement Drills, LeetCode / DSA Patterns, Mock Interviews

Return strictly valid JSON conforming to this schema:
{{
    "target_role": "{resolved_role}",
    "estimated_weeks": 12,
    "strategy_overview": "2 sentences describing the pedagogical approach tailored to this student.",
    "milestones": [
        {{
            "phase": 1,
            "title": "Phase title",
            "timeframe": "Days 1-14",
            "focus_skills": ["Skill 1", "Skill 2"],
            "key_objectives": ["Objective 1", "Objective 2"],
            "action_tasks": [
                {{"id": "task_1_1", "description": "Specific task to complete", "completed": false}},
                {{"id": "task_1_2", "description": "Specific task to complete", "completed": false}},
                {{"id": "task_1_3", "description": "Specific task to complete", "completed": false}}
            ],
            "checkpoint_deliverable": "Tangible artifact (e.g. GitHub repo link, passing test suite)",
            "status": "in_progress"
        }},
        {{
            "phase": 2,
            "title": "Phase title",
            "timeframe": "Days 15-30",
            "focus_skills": ["Skill 3", "Skill 4"],
            "key_objectives": ["Objective 1", "Objective 2"],
            "action_tasks": [
                {{"id": "task_2_1", "description": "Specific task to complete", "completed": false}},
                {{"id": "task_2_2", "description": "Specific task to complete", "completed": false}}
            ],
            "checkpoint_deliverable": "Tangible artifact",
            "status": "not_started"
        }},
        {{
            "phase": 3,
            "title": "Phase title",
            "timeframe": "Days 31-60",
            "focus_skills": ["Skill 5"],
            "key_objectives": ["Objective 1", "Objective 2"],
            "action_tasks": [
                {{"id": "task_3_1", "description": "Specific task to complete", "completed": false}},
                {{"id": "task_3_2", "description": "Specific task to complete", "completed": false}}
            ],
            "checkpoint_deliverable": "Tangible artifact",
            "status": "not_started"
        }},
        {{
            "phase": 4,
            "title": "Phase title",
            "timeframe": "Days 61-90",
            "focus_skills": ["Interview Practice", "DSA"],
            "key_objectives": ["Objective 1", "Objective 2"],
            "action_tasks": [
                {{"id": "task_4_1", "description": "Specific task to complete", "completed": false}},
                {{"id": "task_4_2", "description": "Specific task to complete", "completed": false}}
            ],
            "checkpoint_deliverable": "Final Placement Readiness Audit",
            "status": "not_started"
        }}
    ]
}}
"""
        def fallback_generator():
            g1 = missing_skills[0] if len(missing_skills) > 0 else "System Architecture"
            g2 = missing_skills[1] if len(missing_skills) > 1 else "Docker & Containerization"
            g3 = missing_skills[2] if len(missing_skills) > 2 else "Cloud & CI/CD"

            return {
                "target_role": resolved_role,
                "estimated_weeks": 12,
                "strategy_overview": f"A progressive hands-on curriculum bridging {len(missing_skills)} target competencies through production project building and daily mock drills.",
                "milestones": [
                    {
                        "phase": 1,
                        "title": f"Foundation Sprint: {g1} Mastery",
                        "timeframe": "Days 1-14",
                        "focus_skills": [g1, "Core Design Patterns"],
                        "key_objectives": [f"Understand fundamental constructs of {g1}", "Build standalone CRUD microservice"],
                        "action_tasks": [
                            {"id": "task_1_1", "description": f"Complete official docs and core tutorial for {g1}", "completed": True},
                            {"id": "task_1_2", "description": "Build an isolated modular service implementing standard error handling", "completed": False},
                            {"id": "task_1_3", "description": "Write automated unit tests achieving >80% code coverage", "completed": False}
                        ],
                        "checkpoint_deliverable": "Working GitHub repo with verified CI badge and automated test run",
                        "status": "in_progress"
                    },
                    {
                        "phase": 2,
                        "title": f"Systems & Integration: {g2}",
                        "timeframe": "Days 15-30",
                        "focus_skills": [g2, "RESTful API Specs", "Database Optimization"],
                        "key_objectives": ["Containerize backend and database with docker-compose", "Implement caching and connection pooling"],
                        "action_tasks": [
                            {"id": "task_2_1", "description": f"Containerize multi-container stack using {g2}", "completed": False},
                            {"id": "task_2_2", "description": "Benchmark query performance and add composite database indexes", "completed": False}
                        ],
                        "checkpoint_deliverable": "Containerized application running with docker-compose up",
                        "status": "not_started"
                    },
                    {
                        "phase": 3,
                        "title": f"Full-Stack Capstone: {g3} & Cloud Deployment",
                        "timeframe": "Days 31-60",
                        "focus_skills": [g3, "Full-Stack Integration", "Cloud Deployment"],
                        "key_objectives": ["Ship full-stack application to public cloud environment", "Implement JWT auth and role-based access control"],
                        "action_tasks": [
                            {"id": "task_3_1", "description": "Deploy full application to Render/AWS/Vercel with public URL", "completed": False},
                            {"id": "task_3_2", "description": "Write comprehensive README with architectural diagrams and API documentation", "completed": False}
                        ],
                        "checkpoint_deliverable": "Live production URL and star-worthy GitHub portfolio project",
                        "status": "not_started"
                    },
                    {
                        "phase": 4,
                        "title": "Placement Simulation & Interview Readiness",
                        "timeframe": "Days 61-90",
                        "focus_skills": ["DSA Top 50 Patterns", "Behavioral (STAR)", "Live Coding Drills"],
                        "key_objectives": ["Complete 30 medium LeetCode/DSA problems across graphs, trees, DP", "Conduct 3 AI Mock Interview sessions on Glint"],
                        "action_tasks": [
                            {"id": "task_4_1", "description": "Complete Glint AI Technical Interview Preparation with score >80", "completed": False},
                            {"id": "task_4_2", "description": "Align ATS resume with project metrics and quantifiable outcomes", "completed": False}
                        ],
                        "checkpoint_deliverable": "Score 85%+ on Glint AI Readiness Evaluation",
                        "status": "not_started"
                    }
                ]
            }

        client = get_gemini_client()
        ai_data = client.generate_structured(
            prompt=prompt,
            system_instruction="You are a Principal Software Engineer and Technical Coach. Return pure JSON matching the requested roadmap schema.",
            fallback_fn=fallback_generator
        )

        milestones = ai_data.get("milestones", [])

        # Create Roadmap Record
        roadmap = AIRoadmap(
            student_id=student.id,
            target_role=resolved_role,
            milestones=milestones,
            progress_percentage=10,
            is_active=True
        )
        db.session.add(roadmap)
        db.session.commit()

        return CareerRoadmapService._serialize_roadmap(roadmap)

    @staticmethod
    def update_task_status(
        roadmap_id: int,
        task_id: str,
        completed: Optional[bool] = None,
        proof_url: Optional[str] = None,
        proof_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Updates completion status and proof-of-work link for a roadmap task."""
        roadmap = db.session.get(AIRoadmap, roadmap_id)
        if not roadmap:
            return {"error": "Roadmap not found"}

        milestones = [dict(m) for m in (roadmap.milestones or [])]
        total_tasks = 0
        completed_tasks = 0
        updated_task = None

        for milestone in milestones:
            tasks = [dict(t) for t in milestone.get("action_tasks", [])]
            for task in tasks:
                total_tasks += 1
                if task.get("id") == task_id:
                    if completed is not None:
                        task["completed"] = completed
                    elif proof_url is not None:
                        task["completed"] = True
                    else:
                        task["completed"] = not task.get("completed", False)

                    if proof_url is not None:
                        task["proof_url"] = proof_url.strip()
                    if proof_notes is not None:
                        task["proof_notes"] = proof_notes.strip()

                    updated_task = task

                if task.get("completed"):
                    completed_tasks += 1
            milestone["action_tasks"] = tasks

        new_progress = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
        roadmap.milestones = milestones
        roadmap.progress_percentage = new_progress
        db.session.commit()

        return {
            "success": True,
            "progress_percentage": new_progress,
            "task_id": task_id,
            "task": updated_task,
            "milestones": milestones
        }

    @staticmethod
    def toggle_task(roadmap_id: int, task_id: str) -> Dict[str, Any]:
        """Toggles completion of a task and recalculates progress percentage."""
        return CareerRoadmapService.update_task_status(roadmap_id, task_id)

    @staticmethod
    def _serialize_roadmap(roadmap: AIRoadmap) -> Dict[str, Any]:
        """Serializes roadmap object for web presentation."""
        return {
            "id": roadmap.id,
            "student_id": roadmap.student_id,
            "target_role": roadmap.target_role,
            "milestones": roadmap.milestones or [],
            "progress_percentage": roadmap.progress_percentage,
            "is_active": roadmap.is_active,
            "created_at": roadmap.created_at.strftime("%b %d, %Y") if roadmap.created_at else "Recently"
        }
