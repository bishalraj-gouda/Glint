"""
AI Skill Gap Engine for Campus-Link.
Performs deterministic mathematical skill set comparison between student skills and
industry/target job requirements, enriched by Gemini AI for gap severity and actionable interview questions
with strict Pydantic structured output enforcement.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from extensions import db
from models.student import Student
from models.job import Job
from models.skill import Skill
from services.ai.gemini_client import get_gemini_client


ROLE_BENCHMARKS = {
    "Full Stack Developer": [
        "Python", "JavaScript", "React", "Node.js", "SQL", "Git", "REST APIs", "Docker", "Data Structures"
    ],
    "Data Science & AI Engineer": [
        "Python", "SQL", "Machine Learning", "Pandas", "NumPy", "TensorFlow", "Statistics", "Data Visualization", "Git"
    ],
    "Cloud & Backend Engineer": [
        "Java", "Python", "SQL", "Docker", "Kubernetes", "AWS", "REST APIs", "Microservices", "System Design", "Git"
    ],
    "Frontend Engineer": [
        "JavaScript", "TypeScript", "React", "HTML/CSS", "State Management", "Tailwind CSS", "REST APIs", "Git"
    ],
    "Cybersecurity Analyst": [
        "Network Security", "Linux", "Python", "Ethical Hacking", "Cryptography", "SIEM", "Firewalls", "Git"
    ]
}


# --- Pydantic Schema Definitions for Structured AI Output ---

class ProbingQuestionSchema(BaseModel):
    skill: str = Field(description="Name of the evaluated skill or competency")
    question: str = Field(description="Realistic placement interview question testing this competency")
    concept_tested: str = Field(description="Underlying principle, algorithmic complexity, or system constraint tested")


class SkillGapEngineOutputSchema(BaseModel):
    gap_severity: str = Field(description="One of: High, Moderate, Low")
    market_urgency_summary: str = Field(description="Recruiter urgency appraisal regarding these gaps in current placement cycles")
    priority_focus: List[str] = Field(description="Top 2-3 missing skills that will produce the highest impact if learned first")
    practice_interview_questions: List[ProbingQuestionSchema] = Field(description="List of targeted probing questions")
    quick_win_milestone: str = Field(description="Concrete 7-day challenge to eliminate the highest-yield gap")


class SkillGapService:
    """Computes exact skill coverage and generates actionable remediation blueprints."""

    @staticmethod
    def _dynamically_determine_role_requirements(target_role: str) -> List[str]:
        """Uses Gemini to deduce the top 8 standard skills required for custom target roles."""
        if target_role in ROLE_BENCHMARKS:
            return ROLE_BENCHMARKS[target_role]

        prompt = f"""
Given the technology role '{target_role}', output the top 8 essential technical skills, frameworks, or tools 
expected by campus hiring managers for fresh graduates.
Return strictly a JSON object: {{"skills": ["Skill1", "Skill2", "Skill3", "Skill4", "Skill5", "Skill6", "Skill7", "Skill8"]}}
"""
        def fallback():
            return {"skills": ROLE_BENCHMARKS["Full Stack Developer"]}

        client = get_gemini_client()
        res = client.generate_structured(prompt=prompt, fallback_fn=fallback)
        skills = res.get("skills", [])
        return skills if isinstance(skills, list) and skills else ROLE_BENCHMARKS["Full Stack Developer"]

    @staticmethod
    def analyze_skill_gaps(student_id: int, target_role: Optional[str] = None, job_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyzes gaps against a target role benchmark or a specific open Job posting.
        """
        student = db.session.get(Student, student_id)
        if not student:
            return {"error": "Student not found"}

        # 1. Determine Target Required Skills
        required_skills: List[str] = []
        benchmark_name = target_role or getattr(student, "target_role", None) or "Full Stack Developer"

        if job_id:
            job = db.session.get(Job, job_id)
            if job:
                benchmark_name = f"{job.title} at {job.company.name if job.company else 'Campus Partner'}"
                job_skills = job.skills.all() if hasattr(job.skills, "all") else (job.skills or [])
                required_skills = [s.name for s in job_skills]

        if not required_skills:
            if benchmark_name in ROLE_BENCHMARKS:
                required_skills = ROLE_BENCHMARKS[benchmark_name]
            else:
                required_skills = SkillGapService._dynamically_determine_role_requirements(benchmark_name)

        # 2. Extract Student Skills
        student_skills = student.skills.all() if hasattr(student.skills, "all") else (student.skills or [])
        student_skill_map = {s.name.lower(): s for s in student_skills}

        # 3. Deterministic Set Operations
        matched = []
        missing = []

        for req in required_skills:
            req_lower = req.lower()
            matched_obj = None
            for s_name_lower, s_obj in student_skill_map.items():
                if req_lower == s_name_lower or req_lower in s_name_lower or s_name_lower in req_lower:
                    matched_obj = s_obj
                    break
            
            if matched_obj:
                matched.append({
                    "name": req,
                    "proficiency": getattr(matched_obj, "proficiency", "Intermediate") or "Intermediate",
                    "verified": getattr(matched_obj, "verified", True)
                })
            else:
                missing.append(req)

        total_req = len(required_skills)
        match_percentage = round((len(matched) / total_req * 100), 1) if total_req > 0 else 100.0

        # 4. Gemini AI Enrichment with Structured Pydantic Output
        prompt = f"""
You are the Glint AI Placement Intelligence Engine.
Analyze the skill gap for student {student.full_name} targeting the role '{benchmark_name}'.

Student Skills ({len(student_skills)}): {', '.join([s.name for s in student_skills]) if student_skills else 'None'}
Target Benchmark Role: {benchmark_name}
Target Required Skills ({len(required_skills)}): {', '.join(required_skills)}
Matched Skills ({len(matched)}): {', '.join([m['name'] for m in matched])}
Missing Skills ({len(missing)}): {', '.join(missing)}
Deterministic Match Score: {match_percentage}%

Generate a structured diagnostic response strictly conforming to the SkillGapEngineOutputSchema:
- gap_severity: "High", "Moderate", or "Low"
- market_urgency_summary: 1-2 concise sentences
- priority_focus: list of 2-3 highest yield skills
- practice_interview_questions: 3 questions testing the missing or core competencies
- quick_win_milestone: a concrete 7-day milestone project
"""
        def fallback_generator():
            severity = "Low" if match_percentage >= 70 else ("Moderate" if match_percentage >= 45 else "High")
            top_priority = missing[:3] if missing else ["System Design", "Cloud Deployment"]
            
            sample_questions = []
            for skill_name in (top_priority[:3] or ["REST APIs"]):
                sample_questions.append({
                    "skill": skill_name,
                    "question": f"Explain the core architectural principles of {skill_name} and how you would apply it to optimize a production service.",
                    "concept_tested": f"{skill_name} fundamentals and system scalability"
                })

            return {
                "gap_severity": severity,
                "market_urgency_summary": f"Closing {len(missing)} gap(s) including {', '.join(top_priority[:2])} will elevate candidate suitability into the top quartile of campus applicants.",
                "priority_focus": top_priority,
                "practice_interview_questions": sample_questions,
                "quick_win_milestone": f"Build a micro-project implementing {top_priority[0] if top_priority else 'REST APIs'} with automated tests and CI/CD integration within 7 days."
            }

        client = get_gemini_client()
        ai_result = client.generate_structured(
            prompt=prompt,
            response_schema=SkillGapEngineOutputSchema,
            system_instruction="You are an expert technical interviewer and placement director. Base all gap analysis strictly on provided skill data.",
            fallback_fn=fallback_generator
        )

        return {
            "student_id": student.id,
            "student_name": student.full_name,
            "benchmark_role": benchmark_name,
            "target_role": benchmark_name,
            "match_percentage": match_percentage,
            "benchmark_match_ratio": match_percentage,
            "matched_skills": matched,
            "verified_matched_skills": matched,
            "missing_skills": missing,
            "critical_missing_competencies": missing,
            "total_required": total_req,
            "gap_severity": ai_result.get("gap_severity", "Moderate"),
            "market_urgency_summary": ai_result.get("market_urgency_summary", ""),
            "priority_focus": ai_result.get("priority_focus", missing[:3]),
            "practice_interview_questions": ai_result.get("practice_interview_questions", []),
            "probing_questions": ai_result.get("practice_interview_questions", []),
            "quick_win_milestone": ai_result.get("quick_win_milestone", "")
        }
