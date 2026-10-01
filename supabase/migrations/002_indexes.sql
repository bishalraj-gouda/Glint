-- ==============================================================================
-- PlacementIQ AI (Campus-Link) - Supabase PostgreSQL Schema Migration 002
-- High-Performance Indexes for Foreign Keys, Searches, and Aggregates
-- ==============================================================================

-- Users & Profiles
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_students_user_id ON students(user_id);
CREATE INDEX IF NOT EXISTS idx_students_roll_number ON students(roll_number);
CREATE INDEX IF NOT EXISTS idx_students_department_id ON students(department_id);
CREATE INDEX IF NOT EXISTS idx_students_cgpa ON students(cgpa);
CREATE INDEX IF NOT EXISTS idx_students_readiness_score ON students(readiness_score);
CREATE INDEX IF NOT EXISTS idx_recruiters_user_id ON recruiters(user_id);
CREATE INDEX IF NOT EXISTS idx_recruiters_company_id ON recruiters(company_id);

-- Skills & Associations
CREATE INDEX IF NOT EXISTS idx_skills_name ON skills(name);
CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category);
CREATE INDEX IF NOT EXISTS idx_student_skills_student_id ON student_skills(student_id);
CREATE INDEX IF NOT EXISTS idx_student_skills_skill_id ON student_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_student_skills_verified ON student_skills(verified);
CREATE INDEX IF NOT EXISTS idx_job_skills_job_id ON job_skills(job_id);
CREATE INDEX IF NOT EXISTS idx_job_skills_skill_id ON job_skills(skill_id);

-- Jobs & Applications
CREATE INDEX IF NOT EXISTS idx_jobs_company_id ON jobs(company_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_role_category ON jobs(role_category);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_applications_student_id ON applications(student_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_match_score ON applications(match_score DESC);
CREATE INDEX IF NOT EXISTS idx_applications_applied_at ON applications(applied_at DESC);

-- Interviews & Placements
CREATE INDEX IF NOT EXISTS idx_interviews_application_id ON interviews(application_id);
CREATE INDEX IF NOT EXISTS idx_interviews_scheduled_date ON interviews(scheduled_date ASC);
CREATE INDEX IF NOT EXISTS idx_interviews_status ON interviews(status);
CREATE INDEX IF NOT EXISTS idx_placements_student_id ON placements(student_id);
CREATE INDEX IF NOT EXISTS idx_placements_job_id ON placements(job_id);
CREATE INDEX IF NOT EXISTS idx_placements_company_id ON placements(company_id);
CREATE INDEX IF NOT EXISTS idx_placements_placed_date ON placements(placed_date DESC);
CREATE INDEX IF NOT EXISTS idx_placements_package ON placements(package_lpa DESC);

-- AI Subsystems & Mock Simulator
CREATE INDEX IF NOT EXISTS idx_ai_career_twins_student_id ON ai_career_twins(student_id);
CREATE INDEX IF NOT EXISTS idx_ai_career_twins_readiness ON ai_career_twins(readiness_score DESC);
CREATE INDEX IF NOT EXISTS idx_ai_interview_sessions_student_id ON ai_interview_sessions(student_id);
CREATE INDEX IF NOT EXISTS idx_ai_interview_sessions_status ON ai_interview_sessions(status);
CREATE INDEX IF NOT EXISTS idx_ai_interview_sessions_created ON ai_interview_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_interview_questions_session ON interview_questions(session_id, question_number);
CREATE INDEX IF NOT EXISTS idx_interview_answers_session ON interview_answers(session_id);
CREATE INDEX IF NOT EXISTS idx_interview_answers_question ON interview_answers(question_id);
CREATE INDEX IF NOT EXISTS idx_ai_evaluations_answer ON ai_evaluations(answer_id);
CREATE INDEX IF NOT EXISTS idx_ai_evaluations_score ON ai_evaluations(overall_score DESC);
CREATE INDEX IF NOT EXISTS idx_ai_roadmaps_student ON ai_roadmaps(student_id, is_active);
CREATE INDEX IF NOT EXISTS idx_ai_resume_analyses_student ON ai_resume_analyses(student_id, analyzed_at DESC);
CREATE INDEX IF NOT EXISTS idx_resumes_student ON resumes(student_id);
CREATE INDEX IF NOT EXISTS idx_career_goals_student ON career_goals(student_id);
CREATE INDEX IF NOT EXISTS idx_skill_gap_student ON skill_gap_analyses(student_id, target_role);
CREATE INDEX IF NOT EXISTS idx_learning_recs_student ON learning_recommendations(student_id, priority, status);
CREATE INDEX IF NOT EXISTS idx_job_matches_student_job ON job_matches(student_id, job_id);
CREATE INDEX IF NOT EXISTS idx_ai_activity_logs_student ON ai_activity_logs(student_id, action_type, created_at DESC);
