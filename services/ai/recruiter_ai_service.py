"""
Recruiter AI Copilot Service for Campus-Link.
Assists hiring managers and technical recruiters with candidate ranking, instant screening dossiers,
scorecard evaluation summaries, and conversational recruitment copilot grounded in campus database.
"""
from typing import Dict, Any, List, Optional
from models.student import Student
from models.job import Job
from models.application import Application
from models.interview import Interview
from models.recruiter import Recruiter
from models.ai_career_twin import AICareerTwin
from services.ai.job_match_service import JobMatchService
from services.ai.gemini_client import get_gemini_client


class RecruiterAIService:
    """Delivers candidate evaluations, rankings, and automated interview guides to corporate recruiters."""

    @staticmethod
    def rank_candidates_for_job(job_id: int, min_cgpa: float = 0.0, department: str = None) -> Dict[str, Any]:
        """
        Ranks all campus student profiles against a specific job requisition.
        Combines skill overlap, CGPA gate, project alignment, and Career Twin readiness.
        """
        job = Job.query.get(job_id)
        if not job:
            return {"error": "Job requisition not found", "candidates": []}

        # Base student query
        query = Student.query
        if min_cgpa > 0:
            query = query.filter(Student.cgpa >= min_cgpa)
        if department and department != "ALL":
            from models.department import Department
            query = query.join(Department, Student.department_id == Department.id).filter(
                (Department.code == department) | (Department.name == department)
            )

        students = query.all()

        # Existing applications map: student_id -> Application
        existing_apps = {a.student_id: a for a in Application.query.filter_by(job_id=job.id).all()}

        ranked_list = []
        for student in students:
            match_data = JobMatchService.evaluate_job_match(student.id, job.id)
            twin = AICareerTwin.query.filter_by(student_id=student.id).first()
            twin_score = twin.overall_readiness_score if twin else int((student.cgpa or 6.0) * 8.5)

            projects = student.projects.all() if hasattr(student.projects, "all") else (student.projects or [])
            skills = student.skills.all() if hasattr(student.skills, "all") else (student.skills or [])
            app = existing_apps.get(student.id)

            ranked_list.append({
                "student_id": student.id,
                "name": student.name,
                "roll_number": student.roll_number,
                "department": student.department.code if hasattr(student.department, "code") else str(student.department),
                "cgpa": float(student.cgpa or 0.0),
                "year": student.year,
                "target_role": student.target_role or "Software Engineer",
                "twin_score": twin_score,
                "composite_score": match_data.get("composite_score", 0),
                "fit_verdict": match_data.get("fit_verdict", "Moderate Fit"),
                "matched_skills": match_data.get("matched_skills", []),
                "missing_skills": match_data.get("missing_skills", []),
                "skills_count": len(skills),
                "projects_count": len(projects),
                "cgpa_eligible": match_data.get("cgpa_eligible", True),
                "dept_eligible": match_data.get("dept_eligible", True),
                "application_id": app.id if app else None,
                "application_status": app.status if app else "unapplied"
            })

        # Sort descending by composite score, then by CGPA
        ranked_list.sort(key=lambda x: (x["composite_score"], x["cgpa"]), reverse=True)

        # Assign rank indices
        for idx, item in enumerate(ranked_list, start=1):
            item["rank"] = idx

        return {
            "job_id": job.id,
            "job_title": job.title,
            "job_category": job.role_category,
            "company_name": job.company.name if job.company else None,
            "min_cgpa": job.min_cgpa,
            "required_skills": [js.skill.name for js in job.job_skills if js.skill],
            "total_ranked": len(ranked_list),
            "strong_matches_count": len([c for c in ranked_list if c["composite_score"] >= 75]),
            "candidates": ranked_list
        }

    @staticmethod
    def screen_candidate(student_id: int, job_id: int) -> Dict[str, Any]:
        """Generates an AI screening report for a recruiter evaluating an applicant."""
        student = Student.query.get(student_id)
        job = Job.query.get(job_id)

        if not student or not job:
            return {"error": "Student or Job not found"}

        match_data = JobMatchService.evaluate_job_match(student_id, job_id)
        twin = AICareerTwin.query.filter_by(student_id=student_id).first()
        twin_score = twin.overall_readiness_score if twin else 70

        projects = student.projects.all() if hasattr(student.projects, "all") else (student.projects or [])
        project_titles = [p.title for p in projects]

        prompt = f"""
You are an Executive Technical Recruiter evaluating a candidate for an open position.

Role: {job.title} at {job.company.name if job.company else 'Our Firm'}
Candidate: {student.full_name} ({student.department}, CGPA: {student.cgpa})
Campus Readiness Score: {twin_score}/100
Job Match Score: {match_data.get('composite_score')}% (Verdict: {match_data.get('fit_verdict')})
Matched Skills: {', '.join(match_data.get('matched_skills', []))}
Missing Skills: {', '.join(match_data.get('missing_skills', []))}
Candidate Projects: {', '.join(project_titles) if project_titles else 'None listed'}

Produce an actionable recruiter screening dossier in strictly valid JSON:
{{
    "hiring_recommendation": "One of: Strong Shortlist, Shortlist for Interview, Consider as Backup, Reject",
    "executive_dossier": "2-3 crisp sentences providing an unvarnished hiring appraisal.",
    "top_reasons_to_hire": ["2 specific strengths or achievements that set this candidate apart"],
    "concerns_or_flags": ["1-2 technical gaps, missing requirements, or areas requiring scrutiny"],
    "tailored_interview_guide": [
        {{
            "focus_area": "E.g., Architecture of {project_titles[0] if project_titles else 'Candidate Project'} or Specific Skill",
            "question": "Deep-dive technical probing question",
            "what_to_look_for": "Key response indicators of genuine competence"
        }}
    ]
}}
"""
        def fallback_generator():
            score = match_data.get("composite_score", 60)
            rec = "Strong Shortlist" if score >= 80 else ("Shortlist for Interview" if score >= 60 else "Consider as Backup")
            p_name = project_titles[0] if project_titles else "primary project"
            missing_one = match_data.get("missing_skills", ["cloud deployment"])[0] if match_data.get("missing_skills") else "distributed architecture"

            return {
                "hiring_recommendation": rec,
                "executive_dossier": f"{student.full_name} displays solid foundations with {student.cgpa} CGPA in {student.department} and {score}% alignment for the {job.title} requisition. They have demonstrated practical execution on {len(projects)} projects.",
                "top_reasons_to_hire": [
                    f"Strong technical alignment in {', '.join(match_data.get('matched_skills', [])[:3]) if match_data.get('matched_skills') else 'core computer science'}",
                    f"Verified academic track record meeting our minimum CGPA threshold"
                ],
                "concerns_or_flags": [
                    f"Lack of demonstrated commercial or production experience with {missing_one}"
                ],
                "tailored_interview_guide": [
                    {
                        "focus_area": f"Deep Dive: {p_name}",
                        "question": f"In your {p_name} implementation, what was the most difficult architectural bottleneck you encountered, and how did you measure performance improvements?",
                        "what_to_look_for": "Specific metrics, trade-offs between speed and memory, and clear ownership of the codebase."
                    },
                    {
                        "focus_area": f"Skill Validation: {missing_one}",
                        "question": f"Our team utilizes {missing_one} heavily. How would you quickly adapt your existing workflow to implement this in our production stack?",
                        "what_to_look_for": "Enthusiasm, understanding of conceptual parallels, and clear learning methodology."
                    }
                ]
            }

        client = get_gemini_client()
        result = client.generate_structured(
            prompt=prompt,
            system_instruction="You are an expert technical talent assessor assisting engineering hiring managers.",
            fallback_fn=fallback_generator
        )

        return {
            "student_id": student.id,
            "student_name": student.full_name,
            "job_id": job.id,
            "job_title": job.title,
            "composite_score": match_data.get("composite_score"),
            "cgpa_eligible": match_data.get("cgpa_eligible"),
            "dept_eligible": match_data.get("dept_eligible"),
            "twin_score": twin_score,
            "screening": result
        }

    @staticmethod
    def generate_evaluation_summary(interview_id: int, score: Optional[float] = None, draft_notes: str = "") -> Dict[str, Any]:
        """
        Synthesizes an interviewer's notes and score into a structured, professional evaluation summary.
        """
        interview = Interview.query.get(interview_id)
        if not interview:
            return {"error": "Interview session not found"}

        app = interview.application
        student = app.student if app else None
        job = app.job if app else None

        if not student or not job:
            return {"error": "Associated candidate or job requisition not found"}

        given_score = score if score is not None else (interview.score if interview.score is not None else 75.0)

        prompt = f"""
You are an expert hiring bar raiser and senior talent assessor.
A technical interviewer just completed a candidate evaluation round. Synthesize their raw notes and score into a crisp, professional candidate evaluation summary:

Candidate: {student.full_name} ({student.department}, CGPA: {student.cgpa})
Job Requisition: {job.title} at {job.company.name if job.company else 'our company'}
Round: Round {interview.round_number} ({interview.interview_type})
Numeric Score: {given_score}/100
Interviewer Draft Notes: "{draft_notes if draft_notes.strip() else 'Candidate demonstrated solid problem solving and answered technical questions adequately.'}"

Output strictly valid JSON:
{{
    "evaluation_summary": "2-3 polished sentences summarizing technical performance, communication, and solution quality.",
    "key_strengths": ["1-2 demonstrated technical or behavioral strengths"],
    "growth_areas": ["1 actionable development area or concern"],
    "recommended_status": "One of: select, interview, rejected"
}}
"""
        def fallback_eval():
            status = "select" if given_score >= 80 else ("interview" if given_score >= 65 else "rejected")
            notes_addon = f" Interviewer noted: '{draft_notes.strip()}'." if draft_notes.strip() else ""
            return {
                "evaluation_summary": f"{student.full_name} exhibited solid domain grasp for {job.title} during Round {interview.round_number} ({interview.interview_type}), earning a score of {given_score:.0f}/100.{notes_addon} Demonstrated structured problem-solving and clear reasoning.",
                "key_strengths": [
                    "Sound conceptual knowledge and structured technical explanations",
                    "Good alignment with core requirements for the position"
                ],
                "growth_areas": [
                    "Could refine speed in edge-case identification and architectural trade-offs"
                ],
                "recommended_status": status
            }

        client = get_gemini_client()
        result = client.generate_structured(
            prompt=prompt,
            system_instruction="You are an executive talent bar raiser helping recruiters write decisive evaluation summaries.",
            fallback_fn=fallback_eval
        )

        summary_text = (
            f"{result.get('evaluation_summary', '')}\n\n"
            f"Strengths: {', '.join(result.get('key_strengths', []))}.\n"
            f"Growth Areas: {', '.join(result.get('growth_areas', []))}."
        )

        return {
            "interview_id": interview.id,
            "candidate_name": student.full_name,
            "job_title": job.title,
            "score": given_score,
            "structured_result": result,
            "formatted_feedback": summary_text,
            "recommended_status": result.get("recommended_status", "interview")
        }

    @staticmethod
    def recruiter_chat(recruiter_id: int, message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        AI Recruiter Copilot conversational assistant grounded in company jobs and candidate database.
        """
        recruiter = Recruiter.query.get(recruiter_id)
        if not recruiter:
            return {"error": "Recruiter not found"}

        company_jobs = Job.query.filter_by(company_id=recruiter.company_id).all()
        job_titles = [j.title for j in company_jobs]
        total_students = Student.query.count()

        system_instruction = f"""
You are the PlacementIQ AI Recruiter Copilot, assisting {recruiter.name} at {recruiter.company.name if recruiter.company else 'their organization'}.
Active Job Requisitions ({len(company_jobs)}): {', '.join(job_titles) if job_titles else 'None posted yet'}
Total Campus Student Pool: {total_students} candidates across Engineering departments.

Your role:
1. Help recruiters identify top candidate talent by skills, CGPA, and project depth.
2. Provide technical interview questions, grading rubrics, and bar-raising hiring advice.
3. Keep responses concise, actionable, and formatted with bullet points where appropriate.
"""
        history_context = ""
        if conversation_history:
            formatted_turns = []
            for turn in conversation_history[-6:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                formatted_turns.append(f"{role.capitalize()}: {content}")
            history_context = "\nRecent Conversation:\n" + "\n".join(formatted_turns) + "\n\n"

        prompt = f"{history_context}Recruiter Query: {message}\n\nAI Recruiter Copilot Response:"

        def fallback_chat():
            q_lower = message.lower()
            if "python" in q_lower or "data" in q_lower:
                return (
                    f"Hi {recruiter.name}! In our candidate database, Data Science & CSE students have demonstrated strong Python proficiencies. "
                    f"For your '{job_titles[0] if job_titles else 'open roles'}', you can review top matched candidates in the AI Candidate Matcher tab, "
                    f"where candidates are ranked by algorithmic match score."
                )
            elif "question" in q_lower or "interview" in q_lower:
                return (
                    "Here are 3 high-signal technical interview questions tailored for campus engineering hiring:\n"
                    "1. *Data Structures*: 'How would you design an in-memory LRU cache with O(1) read and write operations?'\n"
                    "2. *System Design*: 'Walk through how an asynchronous email notification service handles 10,000 spikes per second.'\n"
                    "3. *Behavioral*: 'Describe a project where an initial implementation failed. What telemetry did you use to debug it?'"
                )
            else:
                return (
                    f"Hello {recruiter.name}! I'm ready to assist with your hiring drives at {recruiter.company.name if recruiter.company else 'your firm'}. "
                    f"You have {len(company_jobs)} active requisitions. Would you like me to rank top candidates, prepare interview questions, or evaluate scorecard feedback?"
                )

        client = get_gemini_client()
        reply = client.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.7,
            fallback_text=fallback_chat()
        )

        return {
            "recruiter_id": recruiter.id,
            "response": reply
        }

    @staticmethod
    def semantic_search_candidates(
        query_text: str,
        min_cgpa: float = 0.0,
        department: Optional[str] = None,
        limit: int = 15
    ) -> Dict[str, Any]:
        """
        Performs semantic vector matching of candidate profiles against natural language queries
        using TF-IDF n-gram vectorization and cosine similarity.
        Example query: 'Find candidates experienced in FastAPI, async queues, and Docker with active GitHub projects'
        """
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        query_clean = (query_text or "").strip()
        if not query_clean:
            return {"query": "", "total_matches": 0, "candidates": []}

        # Filter candidates by baseline academic gates if specified
        base_query = Student.query
        if min_cgpa > 0:
            base_query = base_query.filter(Student.cgpa >= min_cgpa)
        if department and department != "ALL":
            from models.department import Department
            base_query = base_query.join(Department, Student.department_id == Department.id).filter(
                (Department.code == department) | (Department.name == department)
            )

        students = base_query.all()
        if not students:
            return {"query": query_clean, "total_matches": 0, "candidates": []}

        # Build candidate semantic document corpus
        corpus = []
        student_docs = []

        query_terms = [t.lower() for t in query_clean.split() if len(t) > 2]

        for s in students:
            skills = s.skills.all() if hasattr(s.skills, "all") else (s.skills or [])
            skill_names = [sk.name for sk in skills]
            projects = s.projects.all() if hasattr(s.projects, "all") else (s.projects or [])
            project_texts = [f"{p.title} {p.description or ''} {p.tech_stack or ''}" for p in projects]
            gh_data = s.github_data or {}
            gh_repos = [r.get("name", "") + " " + (r.get("description") or "") for r in gh_data.get("top_repositories", [])]
            gh_langs = [l.get("language", "") for l in gh_data.get("primary_languages", [])]

            doc_text = f"""
Candidate: {s.name}
Role Target: {s.target_role or ''}
Headline: {s.headline or ''}
Bio: {s.bio or ''}
Department: {s.department.name if s.department else ''}
Skills: {' '.join(skill_names)}
Projects: {' '.join(project_texts)}
GitHub Repositories: {' '.join(gh_repos)}
GitHub Languages: {' '.join(gh_langs)}
"""
            corpus.append(doc_text)
            student_docs.append({
                "student": s,
                "skill_names": skill_names,
                "project_titles": [p.title for p in projects],
                "gh_data": gh_data
            })

        # Compute TF-IDF n-gram vectors (unigrams + bigrams)
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
        try:
            tfidf_matrix = vectorizer.fit_transform(corpus)
            query_vec = vectorizer.transform([query_clean])
            sim_scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
        except Exception:
            sim_scores = np.zeros(len(corpus))

        ranked_results = []
        for idx, item in enumerate(student_docs):
            s = item["student"]
            base_sim = float(sim_scores[idx]) if idx < len(sim_scores) else 0.0

            # Direct keyword hits boost
            keyword_hits = []
            skill_lower_map = {sn.lower(): sn for sn in item["skill_names"]}
            for term in query_terms:
                if term in skill_lower_map:
                    keyword_hits.append(skill_lower_map[term])

            # GitHub activity bonus
            gh_bonus = 0.05 if (s.github_url and item["gh_data"].get("public_repos_count", 0) > 0) else 0.0

            # Composite semantic score scaled 0-100
            semantic_score = round(min(98.0, (base_sim * 65.0) + (len(keyword_hits) * 8.0) + (gh_bonus * 100.0) + ((s.readiness_score or 70.0) * 0.15)), 1)
            if base_sim == 0.0 and not keyword_hits:
                semantic_score = round((s.readiness_score or 70.0) * 0.35, 1)

            # Fit verdict
            if semantic_score >= 80:
                fit_verdict = "High Semantic Fit"
            elif semantic_score >= 60:
                fit_verdict = "Strong Match"
            elif semantic_score >= 40:
                fit_verdict = "Moderate Match"
            else:
                fit_verdict = "Potential Fit"

            ranked_results.append({
                "student_id": s.id,
                "name": s.name,
                "roll_number": s.roll_number,
                "department": s.department.code if s.department else "General",
                "cgpa": float(s.cgpa or 0.0),
                "year": s.year,
                "headline": s.headline or s.target_role,
                "target_role": s.target_role,
                "semantic_score": semantic_score,
                "semantic_match_score": semantic_score,
                "similarity_raw": round(base_sim, 3),
                "fit_verdict": fit_verdict,
                "matched_skills": list(set(keyword_hits))[:5],
                "skills_count": len(item["skill_names"]),
                "projects_count": len(item["project_titles"]),
                "github_url": s.github_url,
                "github_repos_count": item["gh_data"].get("public_repos_count", 0),
                "github_stars": item["gh_data"].get("total_stars", 0),
                "avatar_url": s.avatar_url or f"https://api.dicebear.com/7.x/avataaars/svg?seed={s.roll_number}"
            })

        # Sort descending by semantic match score
        ranked_results.sort(key=lambda x: (x["semantic_score"], x["cgpa"]), reverse=True)

        for rank, cand in enumerate(ranked_results, start=1):
            cand["rank"] = rank

        return {
            "query": query_clean,
            "total_matches": len(ranked_results),
            "candidates": ranked_results[:limit]
        }
