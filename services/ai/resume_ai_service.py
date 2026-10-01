"""
AI Resume Intelligence & ATS Matcher for Campus-Link.
Parses PDF resumes, evaluates section completeness, calculates ATS compliance,
and leverages Gemini to generate quantifiable XYZ bullet point improvements with
strict Pydantic structured output enforcement.
"""
from typing import Dict, Any, List, Optional
import io
import re
from pydantic import BaseModel, Field
from extensions import db
from models.student import Student
from models.job import Job
from models.ai_resume_analysis import AIResumeAnalysis
from services.ai.gemini_client import get_gemini_client

# Try importing pypdf
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


# --- Pydantic Schema Definitions for Resume Intelligence ---

class BulletPointRewriteSchema(BaseModel):
    original_pattern: str = Field(description="Original or generic resume bullet point pattern")
    improved_xyz_bullet: str = Field(description="Accomplished [X] measured by [Y] by doing [Z] impact bullet point")


class ResumeATSAnalysisSchema(BaseModel):
    ats_score: int = Field(description="Calculated ATS match score (0-100)")
    ats_verdict: str = Field(description="High Match (ATS Ready), Moderate Match (Needs Optimization), or Low Match (High Rejection Risk)")
    formatting_critique: str = Field(description="Analysis of parser readability, section hierarchy, and ATS compatibility")
    missing_critical_keywords: List[str] = Field(description="Top hard technical keywords missing from resume")
    bullet_point_rewrites: List[BulletPointRewriteSchema] = Field(description="High impact Google XYZ bullet rewrites")
    actionable_next_step: str = Field(description="The single most impactful revision to make today")


class ResumeAIService:
    """Performs deep ATS parsing, keyword frequency analysis, and AI resume critique."""

    @staticmethod
    def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
        """Extracts raw text stream from PDF file bytes."""
        if not PYPDF_AVAILABLE:
            return ""
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            text_pages = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_pages.append(page_text)
            return "\n\n".join(text_pages)
        except Exception:
            return ""

    @staticmethod
    def audit_resume(
        student_id: int,
        resume_text: str,
        job_id: Optional[int] = None,
        file_name: str = "Uploaded_Resume.pdf"
    ) -> Dict[str, Any]:
        """Runs comprehensive ATS audit and returns structured suggestions."""
        student = db.session.get(Student, student_id)
        if not student:
            return {"error": "Student not found"}

        # If resume text is empty, construct synthesized text from profile
        if not resume_text or len(resume_text.strip()) < 50:
            skills_str = ", ".join([ss.skill.name for ss in student.student_skills if ss.skill])
            projects_str = "\n".join([f"{p.title}: {p.description} (Tech: {p.tech_stack})" for p in student.projects])
            certs_str = ", ".join([f"{c.name} by {c.issuing_org}" for c in student.certifications])
            resume_text = f"""
Candidate: {student.name}
Target Role: {student.target_role}
Department: {student.department.name if student.department else 'Engineering'}, Year: {student.year}, CGPA: {student.cgpa}
Bio: {student.bio or ''}
Skills: {skills_str}
Projects:
{projects_str}
Certifications: {certs_str}
GitHub: {student.github_url or ''}
LinkedIn: {student.linkedin_url or ''}
"""

        # 1. Section Completeness Check
        sections_detected = {
            "contact_info": bool(re.search(r"(@|phone|email|linkedin|github)", resume_text, re.IGNORECASE)),
            "education": bool(re.search(r"(education|b\.?tech|bachelor|university|college|cgpa|gpa)", resume_text, re.IGNORECASE)),
            "skills": bool(re.search(r"(skills|technologies|proficiencies|languages|frameworks)", resume_text, re.IGNORECASE)),
            "projects": bool(re.search(r"(projects|portfolio|implementations)", resume_text, re.IGNORECASE)),
            "experience": bool(re.search(r"(experience|internship|work|employment)", resume_text, re.IGNORECASE)),
        }

        # 2. Target Job Keywords Comparison
        target_skills = []
        job_title = "General Software Engineering"
        if job_id:
            job = db.session.get(Job, job_id)
            if job:
                job_title = f"{job.title} at {job.company.name if job.company else 'Target Employer'}"
                job_skills = job.skills.all() if hasattr(job.skills, "all") else (job.skills or [])
                target_skills = [s.name for s in job_skills]

        if not target_skills:
            target_skills = ["Python", "SQL", "Git", "REST APIs", "Data Structures", "Docker", "JavaScript"]

        found_keywords = [kw for kw in target_skills if re.search(r"\b" + re.escape(kw) + r"\b", resume_text, re.IGNORECASE)]
        missing_keywords = [kw for kw in target_skills if kw not in found_keywords]

        # 3. Deterministic ATS Baseline Score
        section_score = sum(20 for val in sections_detected.values() if val)
        keyword_score = int((len(found_keywords) / len(target_skills) * 100)) if target_skills else 80
        deterministic_ats = int(0.40 * section_score + 0.60 * keyword_score)

        # 4. Gemini AI Deep Critique with Structured Pydantic Output
        prompt = f"""
You are a Principal Technical Recruiter and ATS Optimization Expert.
Analyze this student's resume text against the target benchmark '{job_title}'.

Target Required Keywords ({len(target_skills)}): {', '.join(target_skills)}
Found Keywords in Resume ({len(found_keywords)}): {', '.join(found_keywords)}
Missing Keywords ({len(missing_keywords)}): {', '.join(missing_keywords)}

Candidate Resume Content Snippet:
---
{resume_text[:2500]}
---

Generate an evaluation strictly matching the ResumeATSAnalysisSchema:
- ats_score: between 0 and 100 (benchmark: {deterministic_ats})
- ats_verdict: "High Match (ATS Ready)", "Moderate Match (Needs Optimization)", or "Low Match (High Rejection Risk)"
- formatting_critique: concise 2-sentence parser and layout critique
- missing_critical_keywords: 3-5 hard technical keywords
- bullet_point_rewrites: 2 concrete rewrites applying Google XYZ formula
- actionable_next_step: 1 high-priority revision action
"""
        def fallback_generator():
            ats_verdict = "High Match (ATS Ready)" if deterministic_ats >= 75 else ("Moderate Match (Needs Optimization)" if deterministic_ats >= 50 else "Low Match (High Rejection Risk)")
            return {
                "ats_score": deterministic_ats,
                "ats_verdict": ats_verdict,
                "formatting_critique": "Resume includes necessary standard sections. Ensure clean single-column layout without nested text-boxes or graphic tables to guarantee 100% parser readability.",
                "missing_critical_keywords": missing_keywords[:4] if missing_keywords else ["Automated Testing", "CI/CD", "Docker"],
                "bullet_point_rewrites": [
                    {
                        "original_pattern": "Developed web application using React and Flask.",
                        "improved_xyz_bullet": "Architected responsive full-stack platform using React & Flask, increasing user engagement by 40% and cutting average load time to <350ms."
                    },
                    {
                        "original_pattern": "Responsible for database queries and schema design.",
                        "improved_xyz_bullet": "Optimized PostgreSQL schema and indexed high-frequency queries, reducing report generation latency from 4.2s to 800ms."
                    }
                ],
                "actionable_next_step": f"Integrate quantifiable performance metrics and add missing keywords ({', '.join(missing_keywords[:2]) if missing_keywords else 'Docker, Testing'}) to project descriptions."
            }

        client = get_gemini_client()
        ai_data = client.generate_structured(
            prompt=prompt,
            response_schema=ResumeATSAnalysisSchema,
            system_instruction="You are a senior hiring manager. Grade resumes with high technical rigor.",
            fallback_fn=fallback_generator
        )

        final_ats_score = ai_data.get("ats_score", deterministic_ats)

        # 5. Persist Analysis Record
        analysis = AIResumeAnalysis(
            student_id=student.id,
            job_id=job_id,
            ats_score=final_ats_score,
            extracted_skills=found_keywords,
            missing_keywords=ai_data.get("missing_critical_keywords", missing_keywords),
            suggestions=ai_data.get("bullet_point_rewrites", []),
            raw_text_snippet=resume_text[:1000]
        )
        db.session.add(analysis)
        db.session.commit()

        return {
            "id": analysis.id,
            "student_id": student.id,
            "job_id": job_id,
            "job_title": job_title,
            "ats_score": final_ats_score,
            "ats_verdict": ai_data.get("ats_verdict", "Moderate Match"),
            "section_completeness": sections_detected,
            "found_keywords": found_keywords,
            "missing_keywords": ai_data.get("missing_critical_keywords", missing_keywords),
            "formatting_critique": ai_data.get("formatting_critique", ""),
            "bullet_point_rewrites": ai_data.get("bullet_point_rewrites", []),
            "actionable_next_step": ai_data.get("actionable_next_step", ""),
            "created_at": analysis.created_at.strftime("%b %d, %Y") if analysis.created_at else "Just now"
        }

    @staticmethod
    def get_latest_analysis(student_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves the most recent resume analysis for a student."""
        analysis = AIResumeAnalysis.query.filter_by(student_id=student_id).order_by(AIResumeAnalysis.created_at.desc()).first()
        if not analysis:
            return None
        return {
            "id": analysis.id,
            "ats_score": analysis.ats_score,
            "extracted_skills": analysis.extracted_skills or [],
            "missing_keywords": analysis.missing_keywords or [],
            "suggestions": analysis.suggestions or [],
            "created_at": analysis.created_at.strftime("%b %d, %Y") if analysis.created_at else "Recently"
        }
