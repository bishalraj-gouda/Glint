"""
Batch Resume Parser Service for Campus-Link PlacementIQ AI.
Extracts candidate information, skills, and experience from PDF, DOCX, and TXT files,
and computes match scores against target job requisitions.
"""
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from extensions import db
from models.student import Student
from models.job import Job
from models.user import User
from models.application import Application
from services.ai.gemini_client import get_gemini_client


COMMON_SKILLS = [
    "Python", "JavaScript", "TypeScript", "React", "Node.js", "Flask", "Django",
    "FastAPI", "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker",
    "Kubernetes", "AWS", "Azure", "GCP", "Git", "GitHub", "CI/CD", "Linux",
    "HTML", "CSS", "TailwindCSS", "Next.js", "Vue.js", "Java", "C++", "C#",
    ".NET", "Spring Boot", "Machine Learning", "Deep Learning", "TensorFlow",
    "PyTorch", "Pandas", "NumPy", "Scikit-Learn", "NLP", "LLM", "REST API",
    "GraphQL", "Microservices", "System Design", "Data Structures", "Algorithms"
]


class BatchResumeService:
    """Processes multi-file candidate resumes in batch and enriches candidate profiles."""

    @staticmethod
    def extract_text(file_bytes: bytes, filename: str) -> str:
        """Extracts text content from PDF, DOCX, or text files."""
        fn = filename.lower()
        if fn.endswith(".pdf"):
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(file_bytes))
                return "\n".join([page.extract_text() or "" for page in reader.pages]).strip()
            except Exception as e:
                print(f"[BatchResumeService] PDF parsing error for {filename}: {e}")
                return ""
        elif fn.endswith(".docx"):
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                    if "word/document.xml" in z.namelist():
                        xml_content = z.read("word/document.xml")
                        tree = ET.fromstring(xml_content)
                        texts = [node.text for node in tree.iter() if node.tag.endswith("}t") and node.text]
                        return " ".join(texts).strip()
            except Exception as e:
                print(f"[BatchResumeService] DOCX parsing error for {filename}: {e}")
                return ""
        else:
            try:
                return file_bytes.decode("utf-8", errors="ignore").strip()
            except Exception:
                return ""

    @staticmethod
    def parse_resume_content(text: str, filename: str, target_job: Optional[Job] = None) -> Dict[str, Any]:
        """Parses resume text using Gemini or deterministic pattern matching."""
        if not text:
            return {
                "filename": filename,
                "name": filename.rsplit(".", 1)[0].replace("_", " ").title(),
                "email": "",
                "phone": "",
                "headline": "Candidate",
                "skills": [],
                "experience_years": 0,
                "education": "University Degree",
                "summary": "Resume content was empty or unreadable.",
                "match_score": 50,
                "status": "error"
            }

        # Deterministic extraction via regex
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        email = email_match.group(0) if email_match else ""

        phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
        phone = phone_match.group(0) if phone_match else ""

        # Extract skills present in text
        matched_skills = [s for s in COMMON_SKILLS if re.search(rf"\b{re.escape(s)}\b", text, re.IGNORECASE)]

        # Guess name from first line or filename
        first_line = text.split("\n")[0].strip()
        guessed_name = first_line if len(first_line) < 40 and not any(c in first_line for c in "@:/\\{}") else filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()

        def fallback():
            # Calculate match score against job if available
            score = 65
            if target_job:
                job_desc = (target_job.description or "") + " " + (target_job.title or "")
                job_skills = [s for s in COMMON_SKILLS if re.search(rf"\b{re.escape(s)}\b", job_desc, re.IGNORECASE)]
                if job_skills:
                    overlap = set(s.lower() for s in matched_skills).intersection(set(s.lower() for s in job_skills))
                    score = min(98, max(45, int((len(overlap) / max(len(job_skills), 1)) * 100)))

            return {
                "filename": filename,
                "name": guessed_name[:50],
                "email": email,
                "phone": phone,
                "headline": f"Candidate with {len(matched_skills)} core technical skills",
                "skills": matched_skills[:12],
                "experience_years": 1,
                "education": "Bachelor of Technology / Computer Science",
                "summary": text[:220] + "...",
                "match_score": score,
                "status": "parsed"
            }

        # Try Gemini structured extraction
        try:
            client = get_gemini_client()
            job_context = f"Target Job: {target_job.title}\nJob Description: {target_job.description[:400]}" if target_job else "No specific job specified."
            prompt = f"""
Analyze this candidate resume text and extract key profile details.
{job_context}

Resume text snippet:
\"\"\"{text[:2500]}\"\"\"

Return strictly JSON matching this schema:
{{
    "name": "Candidate Full Name",
    "email": "Email address",
    "phone": "Phone number or empty string",
    "headline": "1-line professional title or summary",
    "skills": ["Skill1", "Skill2", "Skill3"],
    "experience_years": 1.5,
    "education": "Degree and University",
    "summary": "2 sentence executive summary of candidate strengths",
    "match_score": 85
}}
"""
            res = client.generate_structured(
                prompt=prompt,
                system_instruction="You are an expert technical talent recruiter. Return valid JSON only.",
                fallback_fn=fallback
            )
            res["filename"] = filename
            res["status"] = "parsed"
            if not res.get("skills"):
                res["skills"] = matched_skills[:10]
            if not res.get("email"):
                res["email"] = email
            if not res.get("name"):
                res["name"] = guessed_name
            return res
        except Exception as e:
            print(f"[BatchResumeService] AI parsing fallback: {e}")
            return fallback()

    @staticmethod
    def process_batch(files: List[Any], target_job_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Processes multiple uploaded file objects."""
        target_job = db.session.get(Job, target_job_id) if target_job_id else None
        results = []

        for f in files:
            if not f or not f.filename:
                continue
            filename = f.filename
            file_bytes = f.read()
            text = BatchResumeService.extract_text(file_bytes, filename)
            parsed = BatchResumeService.parse_resume_content(text, filename, target_job=target_job)
            results.append(parsed)

        return results

    @staticmethod
    def import_candidate_to_database(parsed: Dict[str, Any], job_id: Optional[int] = None) -> Dict[str, Any]:
        """Creates or links a Student and Application record from parsed resume data."""
        email = parsed.get("email")
        name = parsed.get("name", "Candidate")
        if not email:
            import random
            clean_name = re.sub(r"[^a-zA-Z0-9]", "", name).lower() or "candidate"
            email = f"{clean_name}{random.randint(100, 999)}@applicant.glint.edu"

        # Check if user/student exists
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                email=email,
                role="STUDENT"
            )
            user.set_password("Student@123")
            db.session.add(user)
            db.session.flush()

        student = Student.query.filter_by(user_id=user.id).first()
        if not student:
            student = Student(
                user_id=user.id,
                name=name,
                roll_number=f"EXT-{user.id:04d}",
                department_id=1,  # Default CSE
                batch="2022-2026",
                year=4,
                cgpa=8.2,
                target_role=parsed.get("headline", "Software Developer")[:100],
                headline=parsed.get("headline", "Candidate")[:200],
                bio=parsed.get("summary", "")[:500]
            )
            db.session.add(student)
            db.session.flush()

        app_id = None
        if job_id:
            existing_app = Application.query.filter_by(job_id=job_id, student_id=student.id).first()
            if not existing_app:
                app = Application(
                    job_id=job_id,
                    student_id=student.id,
                    status="applied",
                    match_score=float(parsed.get("match_score", 75)),
                    applied_at=datetime.now(timezone.utc)
                )
                db.session.add(app)
                db.session.flush()
                app_id = app.id
            else:
                app_id = existing_app.id

        db.session.commit()
        return {
            "success": True,
            "student_id": student.id,
            "user_id": user.id,
            "application_id": app_id,
            "email": email,
            "name": name
        }
