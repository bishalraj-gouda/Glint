"""
AI Career Copilot Chat Service for Glint.
Context-aware conversational assistant grounded in the student's live Career Twin data.
"""
from typing import Dict, Any, List, Optional
from models.student import Student
from models.ai_career_twin import AICareerTwin
from services.ai.gemini_client import get_gemini_client


class CareerChatService:
    """Delivers contextual career advising directly tied to the student's real profile."""

    @staticmethod
    def chat(student_id: int, message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Provides a personalized, context-rich response to the student's query."""
        student = Student.query.get(student_id)
        if not student:
            return {"error": "Student not found"}

        twin = AICareerTwin.query.filter_by(student_id=student_id).first()
        readiness_score = twin.overall_readiness_score if twin else 65

        skills = [s.name for s in (student.skills.all() if hasattr(student.skills, "all") else (student.skills or []))]
        projects = [p.title for p in (student.projects.all() if hasattr(student.projects, "all") else (student.projects or []))]

        # Construct persona-grounded prompt
        system_instruction = f"""
You are the Glint AI Career Copilot, an elite placement mentor dedicated to {student.full_name}.
You know everything about their academic and career profile:
- Department: {student.department}, Year: {student.year}, CGPA: {student.cgpa}
- Skills ({len(skills)}): {', '.join(skills) if skills else 'None listed yet'}
- Projects: {', '.join(projects) if projects else 'None listed yet'}
- Placement Readiness Score: {readiness_score}/100

Guidelines:
1. Always give specific, hyper-personalized advice based on their real skills and department.
2. Be encouraging, highly practical, and direct. Focus on high-yield placement strategies.
3. Suggest concrete actions (e.g. projects, LeetCode patterns, resume fixes) rather than vague platitudes.
4. Keep answers readable with crisp formatting (bullet points, bold text).
"""

        # Build history context
        history_context = ""
        if conversation_history:
            formatted_turns = []
            for turn in conversation_history[-6:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                formatted_turns.append(f"{role.capitalize()}: {content}")
            history_context = "\nRecent Conversation:\n" + "\n".join(formatted_turns) + "\n\n"

        prompt = f"{history_context}Student Query: {message}\n\nGlint AI Copilot Response:"

        def fallback_generator():
            q_lower = message.lower()
            if "resume" in q_lower or "ats" in q_lower:
                return (
                    f"Hi {student.full_name}! For your {student.department} profile, ensure your resume highlights quantifiable outcomes. "
                    f"With your skills in {', '.join(skills[:3]) if skills else 'software development'}, use the Google XYZ formula: "
                    f"'Accomplished [X], as measured by [Y], by doing [Z]'. You can test your score right now in our Resume Intelligence tab!"
                )
            elif "interview" in q_lower or "mock" in q_lower:
                return (
                    f"To prepare for upcoming campus drives, start by practicing our AI Interview Simulator! "
                    f"Since your CGPA is {student.cgpa}, recruiters will probe deeply into your practical projects like "
                    f"'{projects[0] if projects else 'your coursework'}'. Make sure you can explain architectural trade-offs with clarity."
                )
            else:
                return (
                    f"Great question, {student.full_name}! Based on your current Career Twin readiness of {readiness_score}%, "
                    f"your highest leverage move right now is building end-to-end containerized projects and polishing your DSA patterns. "
                    f"Check out your personalized Roadmap and Project Generator for step-by-step guidance."
                )

        client = get_gemini_client()
        reply_text = client.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.7,
            fallback_text=fallback_generator()
        )

        return {
            "student_id": student.id,
            "response": reply_text,
            "readiness_score": readiness_score
        }
