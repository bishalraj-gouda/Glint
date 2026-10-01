"""
Multi-Factor Explainable Job Match Service for Campus-Link.
Calculates deterministic alignment scores and uses Gemini for transparent,
actionable hiring critique and interview talking points.
"""
from typing import Dict, Any, List, Optional
from models.student import Student
from models.job import Job
from services.ai.gemini_client import get_gemini_client


class JobMatchService:
    """Calculates factual fit metrics and generates transparent candidate critique."""

    @staticmethod
    def evaluate_job_match(student_id: int, job_id: int) -> Dict[str, Any]:
        """Evaluates student compatibility with a specific open Job posting."""
        student = Student.query.get(student_id)
        job = Job.query.get(job_id)

        if not student or not job:
            return {"error": "Student or Job record not found"}

        # 1. Deterministic Academic & Eligibility Checks
        student_cgpa = float(student.cgpa or 0)
        job_min_cgpa = float(job.min_cgpa or 0)
        cgpa_eligible = student_cgpa >= job_min_cgpa

        # Department Eligibility
        dept_eligible = True
        if getattr(job, "eligible_departments", None):
            allowed_depts = [d.strip().upper() for d in job.eligible_departments.split(",")]
            dept_obj = getattr(student, "department", None)
            student_dept = (dept_obj.code if hasattr(dept_obj, "code") else str(dept_obj or "")).strip().upper()
            dept_eligible = any(d in student_dept or student_dept in d for d in allowed_depts)

        # 2. Skill Match Ratio
        job_skills = job.skills.all() if hasattr(job.skills, "all") else (job.skills or [])
        job_skill_names = [s.name for s in job_skills]
        student_skills = student.skills.all() if hasattr(student.skills, "all") else (student.skills or [])
        student_skill_names = [s.name for s in student_skills]

        matched_skills = []
        missing_skills = []

        for req in job_skill_names:
            if any(req.lower() in sn.lower() or sn.lower() in req.lower() for sn in student_skill_names):
                matched_skills.append(req)
            else:
                missing_skills.append(req)

        skill_ratio = (len(matched_skills) / len(job_skill_names)) if job_skill_names else 1.0
        skill_score = round(skill_ratio * 100, 1)

        # CGPA Component
        cgpa_score = min(100, int((student_cgpa / 10.0) * 100))

        # Project Count Component
        projects = student.projects.all() if hasattr(student.projects, "all") else (student.projects or [])
        project_score = min(100, len(projects) * 35)

        # Composite Deterministic Fit Score: 50% Skills + 30% CGPA + 20% Projects
        composite_score = round((0.50 * skill_score) + (0.30 * cgpa_score) + (0.20 * project_score), 1)

        # If not eligible academically, cap score at 50 to avoid misleading candidate
        if not cgpa_eligible or not dept_eligible:
            composite_score = min(composite_score, 49.0)

        dept_code = student.department.code if student.department else ""

        # 3. AI Generative Explanation
        prompt = f"""
You are the Glint AI Job Matching Engine.
Provide an honest, explainable fit analysis for:

Candidate: {student.full_name} ({dept_code}, CGPA: {student.cgpa})
Job Opportunity: {job.title} at {job.company.name if job.company else 'Campus Recruiter'}
Job Requirements:
- Min CGPA: {job.min_cgpa} (Candidate meets: {cgpa_eligible})
- Eligible Departments: {job.eligible_departments or 'All'} (Candidate meets: {dept_eligible})
- Required Skills: {', '.join(job_skill_names) if job_skill_names else 'General technical proficiency'}
- Matched Skills ({len(matched_skills)}): {', '.join(matched_skills)}
- Missing Skills ({len(missing_skills)}): {', '.join(missing_skills)}
- Deterministic Match Score: {composite_score}%

Projects: {', '.join([p.title for p in projects]) if projects else 'No public projects'}

Return strictly JSON matching this schema:
{{
    "fit_verdict": "One of: Strong Fit (Top Match), Competitive Fit, Stretch Role, Ineligible",
    "reasoning_summary": "2 sentences explaining the mathematical and qualitative fit.",
    "standout_advantages": ["2 key aspects of candidate's background that recruiters will appreciate"],
    "critical_gaps_to_address": ["1-2 skills or requirements candidate needs to bridge"],
    "tailored_interview_talking_points": ["2 concrete talking points candidate should emphasize if invited to interview"]
}}
"""
        def fallback_generator():
            if not cgpa_eligible or not dept_eligible:
                verdict = "Ineligible (Criteria Mismatch)"
            elif composite_score >= 75:
                verdict = "Strong Fit (Top Match)"
            elif composite_score >= 55:
                verdict = "Competitive Fit"
            else:
                verdict = "Stretch Role"

            return {
                "fit_verdict": verdict,
                "reasoning_summary": f"Candidate aligns on {len(matched_skills)} of {len(job_skill_names)} target competencies with a verified {student.cgpa} CGPA against the {job.min_cgpa} benchmark.",
                "standout_advantages": [
                    f"Strong academic foundation ({student.cgpa} CGPA in {dept_code})",
                    f"Demonstrated hands-on experience in {', '.join(matched_skills[:2]) if matched_skills else 'core CS domains'}"
                ],
                "critical_gaps_to_address": [
                    f"Bridging proficiency in {missing_skills[0]}" if missing_skills else "Deepen unit testing and production metrics"
                ],
                "tailored_interview_talking_points": [
                    f"Discuss how your {projects[0].title if projects else 'coursework'} tackles high-throughput challenges relevant to {job.company.name if job.company else 'the role'}.",
                    f"Highlight adaptability and quick mastery demonstrated across {', '.join(matched_skills[:2]) if matched_skills else 'software tools'}."
                ]
            }

        client = get_gemini_client()
        ai_data = client.generate_structured(
            prompt=prompt,
            system_instruction="You are an expert technical talent evaluator. Provide transparent, explainable fit assessments without exaggeration.",
            fallback_fn=fallback_generator
        )

        return {
            "student_id": student.id,
            "job_id": job.id,
            "job_title": job.title,
            "company_name": job.company.name if job.company else "Campus Recruiter",
            "job_description": job.description or "",
            "salary_formatted": getattr(job, "salary_formatted", "Competitive"),
            "job_location": job.location or "Campus / Hybrid",
            "role_category": getattr(job, "role_category", "Technology"),
            "min_cgpa": job_min_cgpa,
            "student_cgpa": student_cgpa,
            "student_dept": dept_code,
            "eligible_departments": getattr(job, "eligible_departments", None) or "All Branches",
            "composite_score": composite_score,
            "skill_match_percentage": skill_score,
            "cgpa_eligible": cgpa_eligible,
            "dept_eligible": dept_eligible,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "fit_verdict": ai_data.get("fit_verdict", "Competitive Fit"),
            "reasoning_summary": ai_data.get("reasoning_summary", ""),
            "standout_advantages": ai_data.get("standout_advantages", []),
            "critical_gaps_to_address": ai_data.get("critical_gaps_to_address", []),
            "interview_talking_points": ai_data.get("tailored_interview_talking_points", [])
        }
