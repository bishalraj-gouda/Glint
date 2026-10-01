-- ==============================================================================
-- PlacementIQ AI (Campus-Link) - Supabase PostgreSQL Schema Migration 001
-- Initial Relational Schema Definition
-- ==============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Roles Table (RBAC)
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255)
);

-- 2. Departments Table
CREATE TABLE IF NOT EXISTS departments (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(120) NOT NULL
);

-- 3. Users Table (Authentication & Identity)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'STUDENT',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Companies Table
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) UNIQUE NOT NULL,
    website VARCHAR(255),
    industry VARCHAR(100) NOT NULL,
    logo_url VARCHAR(255),
    description TEXT,
    location VARCHAR(150),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Recruiters Table
CREATE TABLE IF NOT EXISTS recruiters (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    designation VARCHAR(100) DEFAULT 'Talent Acquisition Specialist',
    phone VARCHAR(30),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Students Table (Academic & Career Profile)
CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    roll_number VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(120) NOT NULL,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    year INTEGER NOT NULL DEFAULT 4,
    cgpa DOUBLE PRECISION NOT NULL DEFAULT 7.5,
    target_role VARCHAR(100) NOT NULL DEFAULT 'Software Engineer',
    preferred_locations VARCHAR(255) DEFAULT 'Bangalore, Hyderabad, Remote',
    preferred_industries VARCHAR(255) DEFAULT 'Technology, AI, Fintech',
    phone VARCHAR(30),
    college VARCHAR(150) DEFAULT 'Campus Institute of Technology',
    degree VARCHAR(100) DEFAULT 'B.Tech',
    branch VARCHAR(100) DEFAULT 'Computer Science & Engineering',
    graduation_year INTEGER DEFAULT 2026,
    profile_completion DOUBLE PRECISION NOT NULL DEFAULT 80.0,
    experience_level VARCHAR(50) DEFAULT 'Fresher (0-1 yrs)',
    resume_url VARCHAR(255),
    resume_filename VARCHAR(255),
    bio TEXT,
    headline VARCHAR(255),
    github_url VARCHAR(255),
    linkedin_url VARCHAR(255),
    portfolio_url VARCHAR(255),
    github_data_json TEXT DEFAULT '{}',
    avatar_url VARCHAR(255),
    readiness_score DOUBLE PRECISION NOT NULL DEFAULT 70.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. Skills Taxonomy Table
CREATE TABLE IF NOT EXISTS skills (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'technical',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. Student Skills Association Table
CREATE TABLE IF NOT EXISTS student_skills (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    proficiency_level VARCHAR(20) NOT NULL DEFAULT 'intermediate',
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_student_skill UNIQUE (student_id, skill_id)
);

-- 9. Projects Table
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    tech_stack VARCHAR(255),
    github_url VARCHAR(255),
    live_url VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. Certifications Table
CREATE TABLE IF NOT EXISTS certifications (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    issuing_org VARCHAR(150) NOT NULL,
    issue_date DATE,
    credential_url VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 11. Resumes Table
CREATE TABLE IF NOT EXISTS resumes (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    file_url VARCHAR(255),
    filename VARCHAR(255),
    parsed_data_json TEXT DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 12. Career Goals Table
CREATE TABLE IF NOT EXISTS career_goals (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    target_role VARCHAR(100) NOT NULL,
    target_company VARCHAR(150),
    target_industry VARCHAR(100),
    target_skills VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 13. Skill Gap Analyses Table
CREATE TABLE IF NOT EXISTS skill_gap_analyses (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    target_role VARCHAR(100) NOT NULL,
    skill VARCHAR(100) NOT NULL,
    current_level VARCHAR(50) NOT NULL DEFAULT 'none',
    required_level VARCHAR(50) NOT NULL DEFAULT 'intermediate',
    gap_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    recommendation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 14. Learning Recommendations Table
CREATE TABLE IF NOT EXISTS learning_recommendations (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    skill VARCHAR(100) NOT NULL,
    recommendation TEXT NOT NULL,
    resource_url VARCHAR(255),
    priority VARCHAR(30) NOT NULL DEFAULT 'high',
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 15. Jobs Table
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    recruiter_id INTEGER REFERENCES recruiters(id) ON DELETE SET NULL,
    title VARCHAR(150) NOT NULL,
    role_category VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    min_cgpa DOUBLE PRECISION NOT NULL DEFAULT 6.5,
    experience_level VARCHAR(50) DEFAULT 'Fresher (0-1 yrs)',
    location VARCHAR(150) DEFAULT 'Bangalore / Hybrid',
    salary_min DOUBLE PRECISION DEFAULT 6.0,
    salary_max DOUBLE PRECISION DEFAULT 12.0,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    eligible_departments VARCHAR(255) DEFAULT 'CSE, IT, DS, ECE',
    deadline DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 16. Job Skills Association Table
CREATE TABLE IF NOT EXISTS job_skills (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    importance_weight DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    CONSTRAINT uq_job_skill UNIQUE (job_id, skill_id)
);

-- 17. Job Matches Table
CREATE TABLE IF NOT EXISTS job_matches (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    match_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    matched_skills_json TEXT DEFAULT '[]',
    missing_skills_json TEXT DEFAULT '[]',
    explanation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 18. Applications Table
CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    status VARCHAR(30) NOT NULL DEFAULT 'applied',
    match_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    match_breakdown_json TEXT,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_job_student_application UNIQUE (job_id, student_id)
);

-- 19. Interviews Table (Company scheduled rounds)
CREATE TABLE IF NOT EXISTS interviews (
    id SERIAL PRIMARY KEY,
    application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    scheduled_date DATE NOT NULL,
    scheduled_time VARCHAR(20) NOT NULL,
    interview_type VARCHAR(50) NOT NULL DEFAULT 'technical',
    round_number INTEGER NOT NULL DEFAULT 1,
    meeting_link_or_venue VARCHAR(255) DEFAULT 'https://meet.google.com/xyz-placementiq',
    interviewer_name VARCHAR(120) DEFAULT 'Technical Lead',
    status VARCHAR(30) NOT NULL DEFAULT 'scheduled',
    feedback TEXT,
    score DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 20. Placements Table
CREATE TABLE IF NOT EXISTS placements (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    package_lpa DOUBLE PRECISION NOT NULL,
    placed_date DATE NOT NULL,
    academic_year VARCHAR(20) NOT NULL DEFAULT '2025-2026',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 21. AI Career Twins Table
CREATE TABLE IF NOT EXISTS ai_career_twins (
    id SERIAL PRIMARY KEY,
    student_id INTEGER UNIQUE NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    readiness_score DOUBLE PRECISION NOT NULL DEFAULT 50.0,
    academic_score DOUBLE PRECISION NOT NULL DEFAULT 50.0,
    skill_score DOUBLE PRECISION NOT NULL DEFAULT 50.0,
    project_score DOUBLE PRECISION NOT NULL DEFAULT 50.0,
    interview_score DOUBLE PRECISION NOT NULL DEFAULT 50.0,
    target_role VARCHAR(100) NOT NULL DEFAULT 'Software Engineer',
    career_level VARCHAR(50) NOT NULL DEFAULT 'Emerging Talent',
    market_competitiveness VARCHAR(100) NOT NULL DEFAULT 'Premium Product Companies',
    verified_strengths_json TEXT NOT NULL DEFAULT '[]',
    skill_gaps_json TEXT NOT NULL DEFAULT '[]',
    portfolio_gaps_json TEXT NOT NULL DEFAULT '[]',
    interview_gaps_json TEXT NOT NULL DEFAULT '[]',
    recommended_action VARCHAR(255) NOT NULL DEFAULT 'Complete profile skills and projects',
    ai_explanation TEXT,
    metadata_json_str TEXT NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 22. AI Interview Sessions Table
CREATE TABLE IF NOT EXISTS ai_interview_sessions (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
    target_role VARCHAR(100) NOT NULL DEFAULT 'Software Engineer',
    interview_type VARCHAR(50) NOT NULL DEFAULT 'technical',
    difficulty VARCHAR(30) NOT NULL DEFAULT 'intermediate',
    total_questions INTEGER NOT NULL DEFAULT 5,
    current_question_index INTEGER NOT NULL DEFAULT 0,
    average_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status VARCHAR(30) NOT NULL DEFAULT 'in_progress',
    transcript_json TEXT NOT NULL DEFAULT '[]',
    feedback_json TEXT NOT NULL DEFAULT '{}',
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 23. Normalized Interview Questions Table
CREATE TABLE IF NOT EXISTS interview_questions (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES ai_interview_sessions(id) ON DELETE CASCADE,
    question_number INTEGER NOT NULL,
    category VARCHAR(100) NOT NULL,
    question TEXT NOT NULL,
    hint TEXT,
    difficulty VARCHAR(50) NOT NULL DEFAULT 'intermediate',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 24. Normalized Interview Answers Table
CREATE TABLE IF NOT EXISTS interview_answers (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES ai_interview_sessions(id) ON DELETE CASCADE,
    question_id INTEGER UNIQUE NOT NULL REFERENCES interview_questions(id) ON DELETE CASCADE,
    answer TEXT NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 25. Normalized AI Evaluations Table
CREATE TABLE IF NOT EXISTS ai_evaluations (
    id SERIAL PRIMARY KEY,
    answer_id INTEGER UNIQUE NOT NULL REFERENCES interview_answers(id) ON DELETE CASCADE,
    technical_accuracy INTEGER NOT NULL DEFAULT 70,
    communication_clarity INTEGER NOT NULL DEFAULT 70,
    confidence_delivery INTEGER NOT NULL DEFAULT 70,
    depth_completeness INTEGER NOT NULL DEFAULT 70,
    overall_score INTEGER NOT NULL DEFAULT 70,
    feedback TEXT,
    exemplary_model_answer TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 26. AI Roadmaps Table
CREATE TABLE IF NOT EXISTS ai_roadmaps (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    target_role VARCHAR(100) NOT NULL,
    horizon_days INTEGER NOT NULL DEFAULT 90,
    progress_percentage INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    milestones_json TEXT NOT NULL DEFAULT '[]',
    current_week_focus VARCHAR(255) NOT NULL DEFAULT 'Core Fundamentals',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 27. AI Resume Analyses Table
CREATE TABLE IF NOT EXISTS ai_resume_analyses (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
    filename VARCHAR(255),
    target_role VARCHAR(100) NOT NULL DEFAULT 'Software Engineer',
    ats_score DOUBLE PRECISION NOT NULL DEFAULT 70.0,
    role_alignment_score DOUBLE PRECISION NOT NULL DEFAULT 70.0,
    strengths_json TEXT NOT NULL DEFAULT '[]',
    missing_skills_json TEXT NOT NULL DEFAULT '[]',
    missing_keywords_json TEXT NOT NULL DEFAULT '[]',
    project_suggestions_json TEXT NOT NULL DEFAULT '[]',
    summary TEXT,
    raw_text_snippet TEXT,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 28. AI Activity / Audit Logs Table
CREATE TABLE IF NOT EXISTS ai_activity_logs (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    action_type VARCHAR(100) NOT NULL,
    input_reference VARCHAR(255),
    result_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
