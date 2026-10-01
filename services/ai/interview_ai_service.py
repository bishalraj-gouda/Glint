"""
AI Interview Simulator Service for Campus-Link.
Conducts multi-turn adaptive mock interviews with live scoring,
confidence delivery assessment, constructive critiques, and exemplary model answer suggestions.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from extensions import db
from models.student import Student
from models.job import Job
from models.ai_interview_session import AIInterviewSession, InterviewQuestion, InterviewAnswer, AIEvaluation
from services.ai.gemini_client import get_gemini_client


# --- Pydantic Schema Definitions for Interview Simulation ---

class InterviewQuestionItem(BaseModel):
    id: int
    category: str = Field(description="Specific domain (e.g., Database, Systems, Behavioral, Algorithms)")
    question: str = Field(description="Realistic placement interview question prompt")
    hint: str = Field(description="Guiding hint for the candidate")


class GeneratedQuestionsPoolSchema(BaseModel):
    questions: List[InterviewQuestionItem]


class AnswerEvaluationSchema(BaseModel):
    technical_accuracy: int = Field(ge=0, le=100, description="Correctness of algorithms and principles")
    communication_clarity: int = Field(ge=0, le=100, description="Clear articulation, structure, and professional tone")
    confidence_delivery: int = Field(ge=0, le=100, description="Assertiveness, lack of hesitation markers, and conviction")
    depth_completeness: int = Field(ge=0, le=100, description="Coverage of edge cases, trade-offs, and scalability")
    overall_score: int = Field(ge=0, le=100, description="Weighted composite score")
    constructive_feedback: str = Field(description="2-3 sentences explaining strengths and what was omitted")
    exemplary_model_answer: str = Field(description="Concise, high-caliber answer demonstrating ideal response")
    adaptive_followup_probe: Optional[str] = Field(default=None, description="Optional adaptive probe if candidate's answer was incomplete")


class InterviewAIService:
    """Manages interview simulation sessions, question generation, and answer scoring."""

    DEFAULT_QUESTIONS_MAP = {
        "technical": [
            {
                "id": 1,
                "category": "Data Structures & Algorithms",
                "question": "Explain the time and space complexity differences between an Array-based list and a Linked List when performing insertions, deletions, and random access.",
                "hint": "Consider memory locality and pointer traversal costs."
            },
            {
                "id": 2,
                "category": "Database Engineering",
                "question": "How do database indexes (e.g., B-Trees) accelerate query performance, and what are the trade-offs when performing high-frequency write or insert operations?",
                "hint": "Discuss write amplification and index tree maintenance."
            },
            {
                "id": 3,
                "category": "System Architecture",
                "question": "Describe how you would design an API rate limiter to protect an authentication endpoint from brute force attacks in a distributed system.",
                "hint": "Consider token bucket or sliding window algorithms with Redis."
            }
        ],
        "behavioral": [
            {
                "id": 1,
                "category": "Conflict & Ownership (STAR)",
                "question": "Tell me about a time when you and a team member disagreed on a technical design decision. How did you resolve the conflict and what was the outcome?",
                "hint": "Use Situation, Task, Action, Result framework."
            },
            {
                "id": 2,
                "category": "Overcoming Failure",
                "question": "Describe a project where something broke unexpectedly in production or during an evaluation. How did you diagnose the problem and recover?",
                "hint": "Focus on root cause analysis and proactive prevention."
            }
        ]
    }

    @staticmethod
    def start_session(
        student_id: int,
        role_title: str = "Software Development Engineer",
        interview_type: str = "technical",
        job_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Creates a new mock interview session and generates custom questions."""
        student = db.session.get(Student, student_id)
        if not student:
            return {"error": "Student not found"}

        # Dynamic question generation via Gemini
        student_skills = [s.name for s in (student.skills.all() if hasattr(student.skills, "all") else (student.skills or []))]
        
        prompt = f"""
You are an expert Senior Engineering Interviewer at a premier technology company.
Generate 4 targeted {interview_type} interview questions for candidate {student.full_name}.

Role: {role_title}
Candidate Department: {student.department.name if student.department else 'General'}, Year: {student.year}
Candidate Known Skills: {', '.join(student_skills[:6]) if student_skills else 'Standard Computer Science'}

Generate questions conforming strictly to GeneratedQuestionsPoolSchema.
"""
        def fallback_generator():
            q_list = InterviewAIService.DEFAULT_QUESTIONS_MAP.get(interview_type, InterviewAIService.DEFAULT_QUESTIONS_MAP["technical"])
            return {"questions": q_list}

        client = get_gemini_client()
        result = client.generate_structured(
            prompt=prompt,
            response_schema=GeneratedQuestionsPoolSchema,
            system_instruction="You are a principal technical interviewer conducting structured campus hiring rounds.",
            fallback_fn=fallback_generator
        )

        questions = result.get("questions", [])
        if not questions:
            questions = InterviewAIService.DEFAULT_QUESTIONS_MAP.get(interview_type, InterviewAIService.DEFAULT_QUESTIONS_MAP["technical"])

        # Persist Session in DB
        session = AIInterviewSession(
            student_id=student.id,
            job_id=job_id,
            role_title=role_title,
            interview_type=interview_type,
            status="in_progress",
            current_question_index=0,
            transcript=[],
            total_score=0
        )
        # Store questions in transcript metadata
        session.transcript = [{"questions_pool": questions, "answers": []}]
        db.session.add(session)
        db.session.flush()

        # Persist normalized relational interview questions
        for idx, q_data in enumerate(questions, start=1):
            if isinstance(q_data, dict):
                cat = q_data.get("category", "Technical")
                q_text = q_data.get("question", "")
                h_text = q_data.get("hint", "")
            else:
                cat = getattr(q_data, "category", "Technical")
                q_text = getattr(q_data, "question", "")
                h_text = getattr(q_data, "hint", "")
            q_row = InterviewQuestion(
                session_id=session.id,
                question_number=idx,
                category=cat,
                question=q_text,
                hint=h_text,
                difficulty=session.difficulty
            )
            db.session.add(q_row)

        db.session.commit()

        return {
            "session_id": session.id,
            "role_title": role_title,
            "interview_type": interview_type,
            "total_questions": len(questions),
            "current_question_index": 0,
            "current_question": questions[0]
        }

    @staticmethod
    def submit_answer(session_id: int, answer_text: str) -> Dict[str, Any]:
        """Evaluates student answer across technical accuracy, clarity, and confidence metrics."""
        session = db.session.get(AIInterviewSession, session_id)
        if not session or session.status == "completed":
            return {"error": "Active interview session not found or already completed"}

        meta = session.transcript[0] if session.transcript else {"questions_pool": [], "answers": []}
        questions = meta.get("questions_pool", [])
        answers = meta.get("answers", [])
        q_idx = session.current_question_index

        if q_idx >= len(questions):
            return {"error": "All questions have already been answered"}

        curr_q = questions[q_idx]

        # Call Gemini to score the answer with Pydantic structured output
        prompt = f"""
You are an expert technical interviewer evaluating an answer in a mock placement round.

Role Target: {session.role_title}
Interview Category: {curr_q.get('category')}
Question: {curr_q.get('question')}

Candidate's Answer:
"{answer_text.strip()}"

Evaluate the answer objectively across 4 axes (0-100):
1. technical_accuracy (0-100): Correctness of core principles, algorithms, and concepts
2. communication_clarity (0-100): Clear articulation, structure, and professional tone
3. confidence_delivery (0-100): Conviction, assertiveness, absence of timid hedging
4. depth_completeness (0-100): Coverage of edge cases, trade-offs, and scalability

Return strictly valid JSON matching AnswerEvaluationSchema.
"""
        def fallback_evaluator():
            words = answer_text.strip().split()
            word_count = len(words)
            
            base_score = 65
            if word_count > 50:
                base_score += 15
            elif word_count < 15:
                base_score -= 20

            base_score = max(35, min(92, base_score))

            return {
                "technical_accuracy": base_score,
                "communication_clarity": min(95, base_score + 5),
                "confidence_delivery": min(90, base_score + 2),
                "depth_completeness": max(30, base_score - 5),
                "overall_score": base_score,
                "constructive_feedback": "Good fundamental understanding conveyed. Elaborate more specifically on trade-offs, real-world edge cases, and architectural constraints.",
                "exemplary_model_answer": f"In an ideal response, start by clearly stating the core mechanism of {curr_q.get('category')}, contrast the algorithmic trade-offs (e.g. time vs space complexity), and finish with a practical production example.",
                "adaptive_followup_probe": None
            }

        client = get_gemini_client()
        evaluation = client.generate_structured(
            prompt=prompt,
            response_schema=AnswerEvaluationSchema,
            system_instruction="You are an uncompromising but encouraging engineering hiring manager. Grade candidly.",
            fallback_fn=fallback_evaluator
        )

        overall_score = evaluation.get("overall_score", 70)

        # Record answer and evaluation metrics
        recorded_entry = {
            "question_index": q_idx,
            "question": curr_q.get("question"),
            "category": curr_q.get("category"),
            "candidate_answer": answer_text,
            "technical_accuracy": evaluation.get("technical_accuracy", 70),
            "communication_clarity": evaluation.get("communication_clarity", 70),
            "confidence_delivery": evaluation.get("confidence_delivery", 70),
            "depth_completeness": evaluation.get("depth_completeness", 70),
            "score": overall_score,
            "feedback": evaluation.get("constructive_feedback", ""),
            "exemplary_model_answer": evaluation.get("exemplary_model_answer", ""),
            "followup_probe": evaluation.get("adaptive_followup_probe")
        }
        answers.append(recorded_entry)
        meta["answers"] = answers
        session.transcript = [meta]

        # Persist normalized InterviewAnswer and AIEvaluation records
        q_row = InterviewQuestion.query.filter_by(session_id=session.id, question_number=q_idx + 1).first()
        if not q_row:
            q_row = InterviewQuestion(
                session_id=session.id,
                question_number=q_idx + 1,
                category=curr_q.get("category", "Technical"),
                question=curr_q.get("question", ""),
                hint=curr_q.get("hint", ""),
                difficulty=session.difficulty
            )
            db.session.add(q_row)
            db.session.flush()

        ans_row = InterviewAnswer.query.filter_by(question_id=q_row.id).first()
        if not ans_row:
            ans_row = InterviewAnswer(
                session_id=session.id,
                question_id=q_row.id,
                answer=answer_text
            )
            db.session.add(ans_row)
            db.session.flush()
        else:
            ans_row.answer = answer_text

        eval_row = AIEvaluation.query.filter_by(answer_id=ans_row.id).first()
        if not eval_row:
            eval_row = AIEvaluation(
                answer_id=ans_row.id,
                technical_accuracy=int(evaluation.get("technical_accuracy", 70)),
                communication_clarity=int(evaluation.get("communication_clarity", 70)),
                confidence_delivery=int(evaluation.get("confidence_delivery", 70)),
                depth_completeness=int(evaluation.get("depth_completeness", 70)),
                overall_score=int(overall_score),
                feedback=evaluation.get("constructive_feedback", ""),
                exemplary_model_answer=evaluation.get("exemplary_model_answer", "")
            )
            db.session.add(eval_row)
        else:
            eval_row.technical_accuracy = int(evaluation.get("technical_accuracy", 70))
            eval_row.communication_clarity = int(evaluation.get("communication_clarity", 70))
            eval_row.confidence_delivery = int(evaluation.get("confidence_delivery", 70))
            eval_row.depth_completeness = int(evaluation.get("depth_completeness", 70))
            eval_row.overall_score = int(overall_score)
            eval_row.feedback = evaluation.get("constructive_feedback", "")
            eval_row.exemplary_model_answer = evaluation.get("exemplary_model_answer", "")

        # Advance question or complete session
        next_idx = q_idx + 1
        session.current_question_index = next_idx

        is_finished = next_idx >= len(questions)
        scorecard = None

        if is_finished:
            session.status = "completed"
            session.completed_at = datetime.now(timezone.utc)
            all_scores = [a["score"] for a in answers]
            avg_score = int(sum(all_scores) / len(all_scores)) if all_scores else 0
            session.total_score = avg_score

            avg_tech = int(sum(a.get("technical_accuracy", 70) for a in answers) / len(answers)) if answers else 70
            avg_clarity = int(sum(a.get("communication_clarity", 70) for a in answers) / len(answers)) if answers else 70
            avg_conf = int(sum(a.get("confidence_delivery", 70) for a in answers) / len(answers)) if answers else 70
            avg_depth = int(sum(a.get("depth_completeness", 70) for a in answers) / len(answers)) if answers else 70

            scorecard = {
                "final_summary": f"Completed {len(questions)} interview questions with an average composite score of {avg_score}/100.",
                "readiness_verdict": "Interview Ready" if avg_score >= 80 else ("Competitive with Practice" if avg_score >= 60 else "Requires Core Revision"),
                "metrics": {
                    "technical_accuracy": avg_tech,
                    "communication_clarity": avg_clarity,
                    "confidence_delivery": avg_conf,
                    "depth_completeness": avg_depth,
                    "composite_score": avg_score
                },
                "key_strengths": [
                    "Effective foundational conceptual explanation" if avg_tech >= 75 else "Prompt answers without stalling",
                    "Clear professional vocabulary" if avg_clarity >= 75 else "Willingness to articulate reasoning"
                ],
                "recommended_focus": [
                    "Deepen trade-off analysis between algorithmic structures" if avg_depth < 80 else "Quantify past project achievements",
                    "Eliminate tentative sentence phrasing to elevate confidence" if avg_conf < 80 else "Practice live whiteboard design drills"
                ]
            }
            session.feedback = scorecard

        db.session.commit()

        return {
            "completed": is_finished,
            "evaluation": recorded_entry,
            "next_question_index": next_idx,
            "next_question": questions[next_idx] if not is_finished else None,
            "scorecard": scorecard
        }

    @staticmethod
    def get_session_history(student_id: int) -> List[Dict[str, Any]]:
        """Retrieves list of past mock interview sessions."""
        sessions = AIInterviewSession.query.filter_by(student_id=student_id).order_by(AIInterviewSession.created_at.desc()).all()
        return [s.to_dict() for s in sessions]
