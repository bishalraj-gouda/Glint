"""
AI Career Twin Service for Campus-Link.
Creates, updates, and analyzes the digital career twin for each student.
Combines deterministic scoring algorithms with Google Gemini generative intelligence.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from extensions import db
from models.student import Student
from models.ai_career_twin import AICareerTwin
from services.profile_service import ProfileService
from services.ai.gemini_client import get_gemini_client


class CareerTwinService:
    """Core intelligence engine for Student AI Career Twin."""

    @staticmethod
    def get_or_create_twin(student_id: int, refresh: bool = False) -> Dict[str, Any]:
        """
        Retrieves existing Career Twin or generates a fresh one.
        If refresh=True, re-computes deterministic metrics and calls Gemini for updated insights.
        """
        student = Student.query.get(student_id)
        if not student:
            return {"error": "Student not found"}

        twin = AICareerTwin.query.filter_by(student_id=student_id).first()

        # If twin exists and refresh not requested, return serialized twin
        if twin and not refresh:
            return CareerTwinService._serialize_twin(twin, student)

        # Otherwise synthesize twin
        return CareerTwinService._synthesize_twin(student, twin)

    @staticmethod
    def _synthesize_twin(student: Student, existing_twin: Optional[AICareerTwin] = None) -> Dict[str, Any]:
        """Calculates deterministic breakdown and calls Gemini for strategic reasoning."""
        # 1. Deterministic Scoring
        deterministic_score = ProfileService.calculate_readiness_score(student)
        
        # Calculate sub-factor percentages
        cgpa_score = min(100, int((float(student.cgpa or 0) / 10.0) * 100))
        
        skills = student.skills.all() if hasattr(student.skills, "all") else (student.skills or [])
        verified_skills = [s for s in skills if getattr(s, "verified", False)]
        skill_score = min(100, int((len(verified_skills) / 6.0) * 100))
        
        projects = student.projects.all() if hasattr(student.projects, "all") else (student.projects or [])
        project_score = min(100, int((len(projects) / 3.0) * 100))
        
        certs = student.certifications.all() if hasattr(student.certifications, "all") else (student.certifications or [])
        cert_score = min(100, int((len(certs) / 2.0) * 100))

        # Skill strength & gap detection
        skill_names = [s.name for s in skills]
        core_benchmark = ["Python", "Java", "SQL", "React", "Data Structures", "Git", "REST APIs", "Docker"]
        matched_benchmarks = [s for s in core_benchmark if any(s.lower() in sn.lower() for sn in skill_names)]
        missing_benchmarks = [s for s in core_benchmark if not any(s.lower() in sn.lower() for sn in skill_names)]

        # Prepare rich AI context
        student_context = student.build_ai_context()
        student_context["sub_scores"] = {
            "academic": cgpa_score,
            "skills": skill_score,
            "projects": project_score,
            "certifications": cert_score,
            "deterministic_total": deterministic_score
        }

        # 2. AI Generative Synthesis with Fallback
        prompt = f"""
You are the AI Career Twin Engine for Campus-Link.
Analyze this student's verified profile data and provide a deep career intelligence synthesis:

Student Profile:
- Name: {student.full_name}
- Department: {student.department}, Year: {student.year}
- CGPA: {student.cgpa}
- Verified Skills ({len(skills)}): {', '.join(skill_names) if skill_names else 'None listed'}
- Projects ({len(projects)}): {', '.join([p.title for p in projects]) if projects else 'None listed'}
- Certifications ({len(certs)}): {', '.join([c.name for c in certs]) if certs else 'None listed'}
- Deterministic Readiness Score: {deterministic_score}/100
- Core Benchmarks Matched: {', '.join(matched_benchmarks)}
- Core Benchmarks Missing: {', '.join(missing_benchmarks[:4])}

Return a strictly valid JSON object matching this schema:
{{
    "twin_persona": "A professional 2-4 word persona title (e.g., Full-Stack Web Architect, Data & ML Engineer)",
    "executive_summary": "2-3 concise sentences providing an objective appraisal of their placement profile and competitive edge.",
    "predicted_readiness_tier": "One of: Campus Elite (Top 10%), Placement Ready, Emerging Contender, Foundational",
    "market_competitiveness": "One of: Tier-1 Tech & Unicorns, Premium Product Companies, Enterprise Tech Services",
    "strengths": ["3-4 specific strengths based on their actual skills and achievements"],
    "critical_gaps": ["2-3 specific technical or portfolio gaps holding them back from higher CTC"],
    "critical_gap_narrative": "A 1-2 sentence honest diagnostic explaining their single highest priority bottleneck.",
    "recommended_action_today": "A concrete 20-minute action they can execute right now to upgrade their profile."
}}
"""
        def fallback_generator():
            tier = "Placement Ready" if deterministic_score >= 75 else ("Emerging Contender" if deterministic_score >= 55 else "Foundational")
            market = "Tier-1 Tech & Unicorns" if deterministic_score >= 85 else ("Premium Product Companies" if deterministic_score >= 70 else "Enterprise Tech Services")
            
            dept_code = student.department.code if hasattr(student.department, "code") else str(student.department or "")
            primary_domain = "Full-Stack Software Engineer"
            if dept_code in ("DS", "Data Science", "AI"):
                primary_domain = "Data Science & AI Engineer"
            elif dept_code in ("IT", "Information Technology"):
                primary_domain = "Cloud & Backend Developer"
            elif dept_code in ("ECE", "ECE"):
                primary_domain = "Embedded & IoT Systems Engineer"

            return {
                "twin_persona": primary_domain,
                "executive_summary": f"{student.full_name} demonstrates solid foundational readiness with a verified {dept_code or 'Computer Science'} background and {deterministic_score}% benchmark alignment. Enhancing live deployment links and systems proficiency will unlock top-tier placement opportunities.",
                "predicted_readiness_tier": tier,
                "market_competitiveness": market,
                "strengths": [
                    f"Consistent academic standing with {student.cgpa} CGPA in {dept_code or 'Engineering'}",
                    f"Proficiency in core technologies: {', '.join(skill_names[:3]) if skill_names else 'Engineering fundamentals'}",
                    f"Active project portfolio with {len(projects)} practical implementations"
                ],
                "critical_gaps": [
                    f"Missing modern infrastructure & containerization skills ({missing_benchmarks[0] if missing_benchmarks else 'Docker/Kubernetes'})",
                    "Needs production deployment URLs and live demos for existing project repositories"
                ],
                "critical_gap_narrative": f"While core programming skills are demonstrated, the absence of {missing_benchmarks[0] if missing_benchmarks else 'system architecture'} experience prevents full competitiveness for senior product engineering bands.",
                "recommended_action_today": f"Containerize your best project using Docker and add an interactive architectural diagram to your GitHub README."
            }

        client = get_gemini_client()
        ai_result = client.generate_structured(
            prompt=prompt,
            system_instruction="You are an expert Chief Placement Officer and AI Career Advisor. Always base insights strictly on verified data. Never hallucinate skills or degrees.",
            fallback_fn=fallback_generator
        )

        # 3. Save or Update Twin in DB
        if not existing_twin:
            existing_twin = AICareerTwin(student_id=student.id)
            db.session.add(existing_twin)

        existing_twin.overall_readiness_score = deterministic_score
        existing_twin.academic_score = cgpa_score
        existing_twin.skill_score = skill_score
        existing_twin.project_score = project_score
        existing_twin.interview_score = cert_score  # mapped to portfolio & certs
        existing_twin.strengths = ai_result.get("strengths", [])
        existing_twin.gaps = ai_result.get("critical_gaps", [])
        existing_twin.recommendations = [ai_result.get("recommended_action_today", "")]
        existing_twin.market_competitiveness = ai_result.get("market_competitiveness", "Premium Product Companies")
        existing_twin.metadata_json = {
            "twin_persona": ai_result.get("twin_persona", "Software Engineer"),
            "executive_summary": ai_result.get("executive_summary", ""),
            "predicted_readiness_tier": ai_result.get("predicted_readiness_tier", "Placement Ready"),
            "critical_gap_narrative": ai_result.get("critical_gap_narrative", ""),
            "recommended_action_today": ai_result.get("recommended_action_today", ""),
            "matched_benchmarks": matched_benchmarks,
            "missing_benchmarks": missing_benchmarks,
            "last_synced_at": datetime.now(timezone.utc).isoformat() if hasattr(datetime, "now") else datetime.utcnow().isoformat()
        }
        existing_twin.last_calculated = datetime.now(timezone.utc)
        db.session.commit()

        return CareerTwinService._serialize_twin(existing_twin, student)

    @staticmethod
    def _serialize_twin(twin: AICareerTwin, student: Student) -> Dict[str, Any]:
        """Formats the twin object for API JSON and frontend consumption."""
        meta = twin.metadata_json or {}
        dept_val = student.department.code if hasattr(student.department, "code") else str(student.department or "General")
        return {
            "id": twin.id,
            "student_id": student.id,
            "student_name": student.full_name,
            "department": dept_val,
            "year": student.year,
            "cgpa": student.cgpa,
            "overall_score": twin.overall_readiness_score,
            "sub_scores": {
                "academic": twin.academic_score,
                "skills": twin.skill_score,
                "projects": twin.project_score,
                "interview": twin.interview_score
            },
            "twin_persona": meta.get("twin_persona", "Software Engineer"),
            "executive_summary": meta.get("executive_summary", ""),
            "predicted_readiness_tier": meta.get("predicted_readiness_tier", "Placement Ready"),
            "market_competitiveness": twin.market_competitiveness,
            "strengths": twin.strengths or [],
            "critical_gaps": twin.gaps or [],
            "critical_gap_narrative": meta.get("critical_gap_narrative", ""),
            "recommended_action_today": meta.get("recommended_action_today", ""),
            "matched_benchmarks": meta.get("matched_benchmarks", []),
            "missing_benchmarks": meta.get("missing_benchmarks", []),
            "last_calculated": twin.last_calculated.strftime("%b %d, %Y at %I:%M %p") if twin.last_calculated else "Just now"
        }
