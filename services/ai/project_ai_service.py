"""
AI Project Generator ("Build My Next Project") for Campus-Link.
Synthesizes end-to-end portfolio project blueprints that directly eliminate
a student's detected skill gaps and impress technical recruiters.
"""
from typing import Dict, Any, List, Optional
from models.student import Student
from services.ai.skill_gap_service import SkillGapService
from services.ai.gemini_client import get_gemini_client


class ProjectAIService:
    """Generates production-grade project specifications mapped to recruiter rubrics."""

    @staticmethod
    def generate_project_idea(
        student_id: int,
        target_role: Optional[str] = None,
        preferred_domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synthesizes a project blueprint engineered to fill student's top skill gaps."""
        student = Student.query.get(student_id)
        if not student:
            return {"error": "Student not found"}

        gap_analysis = SkillGapService.analyze_skill_gaps(student.id, target_role=target_role)
        resolved_role = gap_analysis.get("benchmark_role", "Full Stack Developer")
        missing_skills = gap_analysis.get("missing_skills", ["Docker", "Redis", "System Design"])
        matched_skills = [m["name"] for m in gap_analysis.get("matched_skills", [])]

        domain_clause = f" focused on {preferred_domain}" if preferred_domain else ""

        prompt = f"""
You are a Principal Software Architect and Engineering Mentor.
Design a stellar, non-trivial, production-grade portfolio project blueprint for student {student.full_name}{domain_clause}.

Candidate Profile:
- Target Career Track: {resolved_role}
- Strengths: {', '.join(matched_skills[:5]) if matched_skills else 'Python, Web Basics'}
- Gaps to Bridge in this Project: {', '.join(missing_skills[:4]) if missing_skills else 'Docker, Microservices, Caching'}

Requirements for the Project:
- Must NOT be a trivial todo app, blog, or weather app.
- Must solve a real-world enterprise problem.
- Must integrate at least 2 of their missing skills ({', '.join(missing_skills[:3]) if missing_skills else 'Docker, Redis'}).

Return strictly valid JSON conforming to this schema:
{{
    "title": "Inspiring Project Title (e.g., CloudScale: Distributed Log Aggregator & Alerting Engine)",
    "tagline": "A punchy one-sentence summary of what the system achieves.",
    "target_industry_domain": "Domain (e.g. Fintech, Healthcare, Developer Tools, Logistics)",
    "problem_statement": "2-3 sentences explaining the tangible business problem and why existing solutions are bottlenecked.",
    "recommended_tech_stack": {{
        "frontend": "Modern UI tech",
        "backend": "High-performance framework",
        "database": "Primary data store & cache",
        "devops_cloud": "Deployment, containerization, and observability"
    }},
    "key_architectural_features": [
        "Feature 1 with technical detail",
        "Feature 2 with technical detail",
        "Feature 3 with technical detail"
    ],
    "implementation_phases": [
        {{"phase": 1, "name": "MVP Core API", "tasks": ["Task A", "Task B"]}},
        {{"phase": 2, "name": "Scalability & Caching", "tasks": ["Task C", "Task D"]}},
        {{"phase": 3, "name": "Containerization & CI/CD", "tasks": ["Task E", "Task F"]}}
    ],
    "resume_bullet_point": "Engineered [Project] using [Tech], achieving [Quantifiable Outcome] across [Metric].",
    "interview_pitch_hook": "How to introduce this project in 30 seconds during an interview."
}}
"""
        def fallback_generator():
            g1 = missing_skills[0] if len(missing_skills) > 0 else "Docker"
            g2 = missing_skills[1] if len(missing_skills) > 1 else "Redis"
            
            return {
                "title": "SentinelFlow: Real-Time Event Driven Monitoring Engine",
                "tagline": f"An asynchronous pipeline processing distributed telemetry streams with sub-second alerting and {g1} orchestration.",
                "target_industry_domain": "Cloud Infrastructure & Reliability Engineering",
                "problem_statement": "Modern distributed microservices struggle with fragmented error telemetry and notification storms. SentinelFlow provides localized deduplication and automated alert dispatch.",
                "recommended_tech_stack": {
                    "frontend": "React 19 with Tailwind CSS and Recharts live stream dashboards",
                    "backend": "Python FastAPI with asynchronous background worker queues",
                    "database": f"PostgreSQL with {g2} for sub-millisecond sliding-window rate limiting",
                    "devops_cloud": f"{g1} containerized multi-service topology with GitHub Actions CI/CD"
                },
                "key_architectural_features": [
                    f"Asynchronous event ingestion queue utilizing {g2} for high-throughput buffering",
                    "Sliding-window threshold computation to suppress duplicate alert floods by 80%",
                    f"Automated health probes and zero-downtime rolling updates via {g1} Compose"
                ],
                "implementation_phases": [
                    {"phase": 1, "name": "Core Ingestion API", "tasks": ["Define event JSON schema with Pydantic", "Build REST endpoints with JWT authentication"]},
                    {"phase": 2, "name": "Distributed Caching & Queues", "tasks": [f"Integrate {g2} pub/sub pipeline", "Implement token-bucket rate limiter"]},
                    {"phase": 3, "name": "Containerization & Observability", "tasks": [f"Author multi-stage Dockerfile and docker-compose.yml", "Set up Prometheus health metrics"]}
                ],
                "resume_bullet_point": f"Architected SentinelFlow event processing pipeline using FastAPI, {g2}, and {g1}, processing 5,000+ events/sec with <45ms p99 latency.",
                "interview_pitch_hook": f"I built SentinelFlow because I wanted to master distributed event streaming and {g1} orchestration. It solved the problem of telemetry noise by implementing an asynchronous sliding-window filter."
            }

        client = get_gemini_client()
        result = client.generate_structured(
            prompt=prompt,
            system_instruction="You are an elite software architect designing standout portfolio projects for engineering candidates.",
            fallback_fn=fallback_generator
        )

        return {
            "student_id": student.id,
            "target_role": resolved_role,
            "blueprint": result
        }
