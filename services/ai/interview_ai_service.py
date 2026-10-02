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
                "hint": "Consider memory locality, CPU cache misses, and pointer traversal costs."
            },
            {
                "id": 2,
                "category": "Database Engineering & Indexing",
                "question": "How do database indexes (e.g., B-Trees vs Hash Indexes) accelerate query performance, and what are the trade-offs when performing high-frequency write operations?",
                "hint": "Discuss write amplification, index tree rebalancing, and read-write trade-offs."
            },
            {
                "id": 3,
                "category": "System Architecture & Scalability",
                "question": "Describe how you would design an API rate limiter to protect a high-traffic authentication endpoint from brute force and DDoS attacks in a distributed system.",
                "hint": "Consider token bucket or sliding window counter algorithms with Redis."
            },
            {
                "id": 4,
                "category": "Debugging & Production Trade-offs",
                "question": "Suppose a backend microservice experiences a sudden spike in latency and database connection pool exhaustion. Walk through your step-by-step diagnostic process to identify and resolve the root cause.",
                "hint": "Consider slow unindexed queries, connection leaks, connection pool sizing, and query profiling."
            }
        ],
        "behavioral": [
            {
                "id": 1,
                "category": "Conflict & Ownership (STAR)",
                "question": "Tell me about a time when you and a team member disagreed on a technical design decision. How did you resolve the conflict and what was the outcome?",
                "hint": "Use Situation, Task, Action, Result framework with emphasis on data-driven compromise."
            },
            {
                "id": 2,
                "category": "Overcoming Failure & Resilience",
                "question": "Describe a project where something broke unexpectedly in production or during an evaluation. How did you diagnose the problem and recover?",
                "hint": "Focus on root cause analysis, composure under pressure, and proactive prevention."
            },
            {
                "id": 3,
                "category": "Prioritization & Deadlines",
                "question": "How do you manage tight deadlines when project requirements change midway through a development sprint?",
                "hint": "Discuss scope negotiation, MVP prioritization, and clear stakeholder communication."
            },
            {
                "id": 4,
                "category": "Leadership & Mentorship",
                "question": "Share an experience where you helped a junior peer or teammate understand a complex technical concept or overcome a technical roadblock.",
                "hint": "Emphasize empathy, active listening, and structured explanation."
            }
        ]
    }

    LEETCODE_PROBLEMS_CATALOG = [
        {"title": "Two Sum", "difficulty": "Easy", "url": "https://leetcode.com/problems/two-sum/", "pattern": "Arrays & Hash Table", "tags": ["array", "hash-table", "python", "java", "c++", "sde", "software"]},
        {"title": "Best Time to Buy and Sell Stock", "difficulty": "Easy", "url": "https://leetcode.com/problems/best-time-to-buy-and-sell-stock/", "pattern": "Sliding Window / Dynamic Array", "tags": ["array", "sliding-window", "sde", "developer"]},
        {"title": "Valid Parentheses", "difficulty": "Easy", "url": "https://leetcode.com/problems/valid-parentheses/", "pattern": "Stack Evaluation", "tags": ["stack", "string", "algorithms", "software"]},
        {"title": "Merge Two Sorted Lists", "difficulty": "Easy", "url": "https://leetcode.com/problems/merge-two-sorted-lists/", "pattern": "Linked List Pointers", "tags": ["linked-list", "recursion", "dsa"]},
        {"title": "Maximum Subarray (Kadane's)", "difficulty": "Medium", "url": "https://leetcode.com/problems/maximum-subarray/", "pattern": "Dynamic Programming", "tags": ["dp", "array", "algorithms"]},
        {"title": "LRU Cache", "difficulty": "Medium", "url": "https://leetcode.com/problems/lru-cache/", "pattern": "System Design & Doubly Linked List", "tags": ["hash-table", "linked-list", "design", "system", "backend"]},
        {"title": "Number of Islands", "difficulty": "Medium", "url": "https://leetcode.com/problems/number-of-islands/", "pattern": "Graph DFS / BFS Traversal", "tags": ["graph", "bfs", "dfs", "matrix", "algorithms"]},
        {"title": "Course Schedule", "difficulty": "Medium", "url": "https://leetcode.com/problems/course-schedule/", "pattern": "Topological Sort / Directed Graph", "tags": ["graph", "topological-sort", "algorithms"]},
        {"title": "Coin Change", "difficulty": "Medium", "url": "https://leetcode.com/problems/coin-change/", "pattern": "Unbounded Knapsack DP", "tags": ["dp", "dynamic-programming", "algorithms"]},
        {"title": "Longest Substring Without Repeating Characters", "difficulty": "Medium", "url": "https://leetcode.com/problems/longest-substring-without-repeating-characters/", "pattern": "Sliding Window & Set", "tags": ["string", "sliding-window", "hash-table", "frontend", "full stack"]},
        {"title": "Search in Rotated Sorted Array", "difficulty": "Medium", "url": "https://leetcode.com/problems/search-in-rotated-sorted-array/", "pattern": "Modified Binary Search", "tags": ["binary-search", "array", "algorithms"]},
        {"title": "Binary Tree Level Order Traversal", "difficulty": "Medium", "url": "https://leetcode.com/problems/binary-tree-level-order-traversal/", "pattern": "Tree Breadth-First Search", "tags": ["tree", "bfs", "algorithms"]},
        {"title": "Kth Largest Element in an Array", "difficulty": "Medium", "url": "https://leetcode.com/problems/kth-largest-element-in-an-array/", "pattern": "Min-Heap / Quickselect", "tags": ["heap", "sorting", "array", "data"]},
        {"title": "Trapping Rain Water", "difficulty": "Hard", "url": "https://leetcode.com/problems/trapping-rain-water/", "pattern": "Two Pointers & Monotonic Stack", "tags": ["two-pointers", "stack", "algorithms", "amazon"]}
    ]

    CURATED_RESOURCES_CATALOG = [
        {
            "title": "NeetCode 150 Roadmap & Video Breakdowns",
            "url": "https://neetcode.io/practice",
            "category": "Interactive Guide",
            "type": "Interactive Guide",
            "badge": "Core Practice",
            "description": "Structured curriculum covering essential patterns asked by top campus recruiters."
        },
        {
            "title": "System Design Primer by Donne Martin",
            "url": "https://github.com/donnemartin/system-design-primer",
            "category": "Architecture Guide",
            "type": "Architecture Guide",
            "badge": "Top Rated",
            "description": "Learn how to build scalable systems, caching architectures, and resilient APIs."
        },
        {
            "title": "GeeksforGeeks Placement Preparation Archive",
            "url": "https://www.geeksforgeeks.org/must-do-coding-questions-for-companies-like-amazon-microsoft-adobe/",
            "category": "Company Archives",
            "type": "Company Archives",
            "badge": "Campus Favorite",
            "description": "Company-specific interview experience archives for Amazon, Microsoft, Infosys, and TCS."
        },
        {
            "title": "Tech Interview Handbook",
            "url": "https://www.techinterviewhandbook.org/",
            "category": "Cheatsheet",
            "type": "Cheatsheet",
            "badge": "Free Resource",
            "description": "Algorithm cheatsheets, behavioral STAR frameworks, and negotiation strategies."
        }
    ]

    @staticmethod
    def start_session(
        student_id: int,
        role_title: str = "Software Development Engineer",
        interview_type: str = "technical",
        job_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Creates a new mock interview session and generates custom questions calibrated to the company/job role."""
        student = db.session.get(Student, student_id)
        if not student:
            return {"error": "Student not found"}

        job = db.session.get(Job, job_id) if job_id else None
        if job:
            company_name = job.company.name if job.company else "Campus Recruiter"
            target_role = job.title or role_title
            required_skills = [s.name for s in (job.skills.all() if hasattr(job.skills, "all") else (job.skills or []))]
            job_desc_snippet = (job.description[:350] + "...") if job.description else ""
        else:
            company_name = "Premier Technology Firm"
            target_role = role_title
            required_skills = []
            job_desc_snippet = ""

        # Dynamic question generation via Gemini
        student_skills = [s.name for s in (student.skills.all() if hasattr(student.skills, "all") else (student.skills or []))]
        
        prompt = f"""
You are the Lead Recruitment Interviewer at {company_name} conducting a campus hiring round for the role of "{target_role}".

Recruitment Context:
- Hiring Company: {company_name}
- Target Role: {target_role}
- Interview Track: {interview_type} (e.g. Technical Depth, Architecture, Behavioral Leadership)
- Key Required Technologies/Skills: {', '.join(required_skills) if required_skills else 'Core Computer Science, Algorithms & System Design'}
{f'- Job Overview: {job_desc_snippet}' if job_desc_snippet else ''}

Candidate Profile:
- Candidate Name: {student.full_name}
- Academic Department: {student.department.name if student.department else 'Engineering'}, Year: {student.year}
- Known Student Skills: {', '.join(student_skills[:6]) if student_skills else 'General Software'}

Generate exactly 4 progressive, realistic {interview_type} interview questions calibrated to {company_name}'s hiring standard for {target_role}:
1. Question 1: Core technical competency or foundational concept in {', '.join(required_skills[:3]) if required_skills else target_role}.
2. Question 2: Practical scenario/implementation question testing hands-on engineering trade-offs.
3. Question 3: Deep-dive problem solving, system design, or edge-case handling typical of {company_name}'s interviews.
4. Question 4: Role-specific real-world scenario or behavioral STAR leadership question relevant to {company_name}.

Generate questions conforming strictly to GeneratedQuestionsPoolSchema.
"""
        def fallback_generator():
            base_list = InterviewAIService.DEFAULT_QUESTIONS_MAP.get(interview_type, InterviewAIService.DEFAULT_QUESTIONS_MAP["technical"])
            if job:
                company_q = {
                    "id": 1,
                    "category": f"{company_name} Fit & Domain",
                    "question": f"Why are you interested in joining {company_name} as a {target_role}, and how have your past technical projects prepared you for the core technologies ({', '.join(required_skills[:3]) if required_skills else 'required for this role'})?",
                    "hint": f"Demonstrate clear knowledge of {company_name}'s products and tech stack."
                }
                adapted = [company_q] + [
                    {**q, "id": i + 2} for i, q in enumerate(base_list[:3])
                ]
                return {"questions": adapted}
            return {"questions": base_list}

        client = get_gemini_client()
        result = client.generate_structured(
            prompt=prompt,
            response_schema=GeneratedQuestionsPoolSchema,
            system_instruction=f"You are a principal technical interviewer at {company_name} conducting rigorous campus hiring rounds.",
            fallback_fn=fallback_generator
        )

        questions = result.get("questions", [])
        if not questions:
            fallback_res = fallback_generator()
            questions = fallback_res.get("questions", [])

        # Persist Session in DB
        session = AIInterviewSession(
            student_id=student.id,
            job_id=job.id if job else None,
            role_title=target_role,
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
            "job_id": job.id if job else None,
            "company_name": company_name,
            "role_title": target_role,
            "interview_type": interview_type,
            "total_questions": len(questions),
            "current_question_index": 0,
            "current_question": questions[0] if questions else None,
            "questions": questions
        }

    @staticmethod
    def _evaluate_single_answer(role_title: str, question_dict: Dict[str, Any], answer_text: str) -> Dict[str, Any]:
        """Evaluates one answer against a question prompt using Gemini or fallback grading."""
        clean_ans = (answer_text or "").strip()
        category = question_dict.get("category", "Technical")
        q_text = question_dict.get("question", "")

        if not clean_ans or len(clean_ans) < 5:
            return {
                "technical_accuracy": 20,
                "communication_clarity": 20,
                "confidence_delivery": 30,
                "depth_completeness": 15,
                "overall_score": 20,
                "constructive_feedback": "Question was skipped or left blank. Practice writing out key concepts or structuring partial answers even when uncertain.",
                "exemplary_model_answer": f"For {category}, begin by defining core principles, compare alternative approaches (e.g. time/space trade-offs), and conclude with an illustrative real-world engineering example.",
                "adaptive_followup_probe": None
            }

        prompt = f"""
You are an expert technical interviewer evaluating an answer in a campus placement round.

Role Target: {role_title}
Interview Category: {category}
Question: {q_text}

Candidate's Answer:
"{clean_ans}"

Evaluate the answer objectively across 4 axes (0-100):
1. technical_accuracy (0-100): Correctness of core principles, algorithms, and concepts
2. communication_clarity (0-100): Clear articulation, structure, and professional tone
3. confidence_delivery (0-100): Conviction, assertiveness, absence of timid hedging
4. depth_completeness (0-100): Coverage of edge cases, trade-offs, and scalability

Return strictly valid JSON matching AnswerEvaluationSchema.
"""
        def fallback_evaluator():
            words = clean_ans.split()
            word_count = len(words)
            base_score = 65
            if word_count > 40:
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
                "constructive_feedback": f"Good fundamental grasp of {category}. Elaborate more on practical edge cases, constraints, and architecture trade-offs.",
                "exemplary_model_answer": f"An exemplary answer begins by stating the core mechanism of {category}, analyzes space-time trade-offs, and illustrates with an end-to-end implementation example.",
                "adaptive_followup_probe": None
            }

        client = get_gemini_client()
        result = client.generate_structured(
            prompt=prompt,
            response_schema=AnswerEvaluationSchema,
            system_instruction="You are an uncompromising but encouraging engineering hiring manager. Grade candidly.",
            fallback_fn=fallback_evaluator
        )
        return result

    @staticmethod
    def get_recommended_practice(job: Optional[Job], role_title: str, questions: List[Dict[str, Any]], avg_score: int) -> Dict[str, Any]:
        """Generates priority study topics, direct LeetCode links, and online learning resources."""
        role_lower = (role_title or "").lower()
        job_skills = [s.name.lower() for s in job.skills] if (job and job.skills) else []
        job_desc = (job.description or "").lower() if job else ""

        # 1. Direct LeetCode Links based on job skills & role
        is_coding_role = any(kw in role_lower for kw in ["software", "developer", "engineer", "sde", "backend", "frontend", "full stack", "data", "ml", "ai", "coding"]) or any(kw in job_desc for kw in ["dsa", "leetcode", "algorithm", "python", "java", "c++", "data structure"])
        
        selected_leetcode = []
        if is_coding_role or not job:
            all_lc = InterviewAIService.LEETCODE_PROBLEMS_CATALOG
            matched_lc = []
            for p in all_lc:
                if any(t in job_skills or t in job_desc or t in role_lower for t in p["tags"]):
                    matched_lc.append(p)
            
            seen_urls = set()
            for p in (matched_lc + all_lc):
                if p["url"] not in seen_urls:
                    seen_urls.add(p["url"])
                    selected_leetcode.append(p)
                if len(selected_leetcode) >= 6:
                    break

        # 2. Recommended Topics to Cover based on score and question categories
        topics_to_cover = []
        categories = [q.get("category", "") for q in questions if isinstance(q, dict)]
        
        if any("algorithm" in c.lower() or "data structure" in c.lower() for c in categories) or is_coding_role:
            topics_to_cover.append({
                "topic": "Array & Hash Map Patterns (Sliding Window, Two Pointers)",
                "priority": "High" if avg_score < 75 else "Medium",
                "reason": "Standard round-1 technical screening drill across top campus recruiters.",
                "why": "Standard round-1 technical screening drill across top campus recruiters."
            })
            topics_to_cover.append({
                "topic": "Trees, Graphs & BFS/DFS Traversal",
                "priority": "High" if avg_score < 70 else "Medium",
                "reason": "Crucial for clearing problem-solving rounds and technical architecture questions.",
                "why": "Crucial for clearing problem-solving rounds and technical architecture questions."
            })

        if any("database" in c.lower() or "system" in c.lower() or "architecture" in c.lower() for c in categories) or any(s in job_skills for s in ["sql", "postgresql", "mongodb", "database", "redis"]):
            topics_to_cover.append({
                "topic": "Database Indexing, B+ Trees & Write Amplification",
                "priority": "High" if avg_score < 80 else "Medium",
                "reason": "Recruiters test candidates on query performance, transaction isolation levels, and indexing trade-offs.",
                "why": "Recruiters test candidates on query performance, transaction isolation levels, and indexing trade-offs."
            })
            topics_to_cover.append({
                "topic": "Distributed Caching & Rate Limiting (Redis / Sliding Window)",
                "priority": "Medium",
                "reason": "Essential for system design rounds and scalable microservice APIs.",
                "why": "Essential for system design rounds and scalable microservice APIs."
            })

        topics_to_cover.append({
            "topic": "STAR Method (Situation, Task, Action, Measurable Result)",
            "priority": "Medium" if avg_score >= 70 else "High",
            "reason": "Structure behavioral stories to showcase ownership, technical leadership, and team collaboration.",
            "why": "Structure behavioral stories to showcase ownership, technical leadership, and team collaboration."
        })

        topics_to_cover = topics_to_cover[:4]

        # 3. Curated Online Resources
        resources = list(InterviewAIService.CURATED_RESOURCES_CATALOG)

        return {
            "leetcode_links": selected_leetcode,
            "topics_to_cover": topics_to_cover,
            "online_resources": resources
        }

    @staticmethod
    def submit_all_answers(session_id: int, answers_payload: Any) -> Dict[str, Any]:
        """Evaluates all interview questions at once, producing instant multi-axis scores,
        priority topics to cover, curated online resources, and direct LeetCode practice links."""
        session = db.session.get(AIInterviewSession, session_id)
        if not session:
            return {"error": "Interview session not found"}

        meta = session.transcript[0] if session.transcript else {"questions_pool": [], "answers": []}
        questions = meta.get("questions_pool", [])
        if not questions:
            return {"error": "No questions found in session"}

        # Normalize answers_payload into a dict: {question_index: answer_text}
        answers_map = {}
        if isinstance(answers_payload, list):
            for item in answers_payload:
                if isinstance(item, dict):
                    idx = item.get("question_index", item.get("index", 0))
                    text = item.get("answer", item.get("text", ""))
                    answers_map[int(idx)] = str(text)
        elif isinstance(answers_payload, dict):
            for k, v in answers_payload.items():
                try:
                    answers_map[int(k)] = str(v)
                except ValueError:
                    pass

        job = session.job
        recorded_answers = []
        all_scores = []
        tech_scores = []
        clarity_scores = []
        conf_scores = []
        depth_scores = []

        for q_idx, q_item in enumerate(questions):
            ans_text = answers_map.get(q_idx, "").strip()
            eval_res = InterviewAIService._evaluate_single_answer(session.role_title, q_item, ans_text)

            score = eval_res.get("overall_score", 65)
            tech = eval_res.get("technical_accuracy", 65)
            clarity = eval_res.get("communication_clarity", 70)
            conf = eval_res.get("confidence_delivery", 70)
            depth = eval_res.get("depth_completeness", 60)

            all_scores.append(score)
            tech_scores.append(tech)
            clarity_scores.append(clarity)
            conf_scores.append(conf)
            depth_scores.append(depth)

            recorded_entry = {
                "question_index": q_idx,
                "question": q_item.get("question", ""),
                "category": q_item.get("category", "Technical"),
                "candidate_answer": ans_text,
                "technical_accuracy": tech,
                "communication_clarity": clarity,
                "confidence_delivery": conf,
                "depth_completeness": depth,
                "score": score,
                "feedback": eval_res.get("constructive_feedback", ""),
                "exemplary_model_answer": eval_res.get("exemplary_model_answer", "")
            }
            recorded_answers.append(recorded_entry)

            # Persist relational InterviewAnswer & AIEvaluation
            q_row = InterviewQuestion.query.filter_by(session_id=session.id, question_number=q_idx + 1).first()
            if not q_row:
                q_row = InterviewQuestion(
                    session_id=session.id,
                    question_number=q_idx + 1,
                    category=q_item.get("category", "Technical"),
                    question=q_item.get("question", ""),
                    hint=q_item.get("hint", ""),
                    difficulty=session.difficulty
                )
                db.session.add(q_row)
                db.session.flush()

            ans_row = InterviewAnswer.query.filter_by(question_id=q_row.id).first()
            if not ans_row:
                ans_row = InterviewAnswer(
                    session_id=session.id,
                    question_id=q_row.id,
                    answer=ans_text
                )
                db.session.add(ans_row)
                db.session.flush()
            else:
                ans_row.answer = ans_text

            eval_row = AIEvaluation.query.filter_by(answer_id=ans_row.id).first()
            if not eval_row:
                eval_row = AIEvaluation(
                    answer_id=ans_row.id,
                    technical_accuracy=tech,
                    communication_clarity=clarity,
                    confidence_delivery=conf,
                    depth_completeness=depth,
                    overall_score=score,
                    feedback=eval_res.get("constructive_feedback", ""),
                    exemplary_model_answer=eval_res.get("exemplary_model_answer", "")
                )
                db.session.add(eval_row)
            else:
                eval_row.technical_accuracy = tech
                eval_row.communication_clarity = clarity
                eval_row.confidence_delivery = conf
                eval_row.depth_completeness = depth
                eval_row.overall_score = score
                eval_row.feedback = eval_res.get("constructive_feedback", "")
                eval_row.exemplary_model_answer = eval_res.get("exemplary_model_answer", "")

        # Compute composite scores
        avg_score = int(sum(all_scores) / len(all_scores)) if all_scores else 0
        avg_tech = int(sum(tech_scores) / len(tech_scores)) if tech_scores else 0
        avg_clarity = int(sum(clarity_scores) / len(clarity_scores)) if clarity_scores else 0
        avg_conf = int(sum(conf_scores) / len(conf_scores)) if conf_scores else 0
        avg_depth = int(sum(depth_scores) / len(depth_scores)) if depth_scores else 0

        # Generate Prep Recommendations
        prep_recommendations = InterviewAIService.get_recommended_practice(job, session.role_title, questions, avg_score)

        readiness_verdict = (
            "Highly Interview Ready (Top 10% Candidate)" if avg_score >= 82
            else ("Competitive Candidate (Targeted Revision Recommended)" if avg_score >= 65
            else "Needs Core Revision (Review Recommended Topics & LeetCode Drills)")
        )

        scorecard = {
            "final_summary": f"Completed all {len(questions)} interview questions with a composite score of {avg_score}/100.",
            "readiness_verdict": readiness_verdict,
            "metrics": {
                "technical_accuracy": avg_tech,
                "communication_clarity": avg_clarity,
                "confidence_delivery": avg_conf,
                "depth_completeness": avg_depth,
                "composite_score": avg_score
            },
            "topics_to_cover": prep_recommendations["topics_to_cover"],
            "leetcode_links": prep_recommendations["leetcode_links"],
            "online_resources": prep_recommendations["online_resources"],
            "answers_evaluations": recorded_answers
        }

        # Update Session
        meta["answers"] = recorded_answers
        session.transcript = [meta]
        session.current_question_index = len(questions)
        session.total_score = avg_score
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)
        session.feedback = scorecard

        db.session.commit()

        return {
            "success": True,
            "completed": True,
            "session_id": session.id,
            "composite_score": avg_score,
            "readiness_verdict": readiness_verdict,
            "metrics": scorecard["metrics"],
            "answers_evaluations": recorded_answers,
            "topics_to_cover": prep_recommendations["topics_to_cover"],
            "leetcode_links": prep_recommendations["leetcode_links"],
            "online_resources": prep_recommendations["online_resources"],
            "scorecard": scorecard
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

        evaluation = InterviewAIService._evaluate_single_answer(session.role_title, curr_q, answer_text)
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

            prep_recommendations = InterviewAIService.get_recommended_practice(session.job, session.role_title, questions, avg_score)

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
                "topics_to_cover": prep_recommendations["topics_to_cover"],
                "leetcode_links": prep_recommendations["leetcode_links"],
                "online_resources": prep_recommendations["online_resources"],
                "key_strengths": [
                    "Effective foundational conceptual explanation" if avg_tech >= 75 else "Prompt answers without stalling",
                    "Clear professional vocabulary" if avg_clarity >= 75 else "Willingness to articulate reasoning"
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
