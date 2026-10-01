-- ==============================================================================
-- PlacementIQ AI (Campus-Link) - Supabase PostgreSQL Schema Migration 003
-- Row Level Security (RLS) Strategy & Defense-in-Depth Policies
-- ==============================================================================

-- 1. Enable RLS on all relational tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE recruiters ENABLE ROW LEVEL SECURITY;
ALTER TABLE students ENABLE ROW LEVEL SECURITY;
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE certifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE resumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE career_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_gap_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE interviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE placements ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_career_twins ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_interview_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE interview_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE interview_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_roadmaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_resume_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_activity_logs ENABLE ROW LEVEL SECURITY;

-- 2. Backend Service-Role Bypass Policy
-- Guarantees the Flask backend (connecting via service role or direct connection pooler)
-- retains full CRUD capability across all tables.
CREATE OR REPLACE FUNCTION is_service_role() RETURNS BOOLEAN AS $$
BEGIN
    RETURN (CURRENT_USER = 'postgres' OR CURRENT_USER = 'service_role' OR auth.jwt() ->> 'role' = 'service_role');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Universal Service Role Policies
DO $$
DECLARE
    tbl text;
    tables text[] := ARRAY[
        'users', 'departments', 'roles', 'companies', 'recruiters', 'students',
        'skills', 'student_skills', 'projects', 'certifications', 'resumes',
        'career_goals', 'skill_gap_analyses', 'learning_recommendations', 'jobs',
        'job_skills', 'job_matches', 'applications', 'interviews', 'placements',
        'ai_career_twins', 'ai_interview_sessions', 'interview_questions',
        'interview_answers', 'ai_evaluations', 'ai_roadmaps', 'ai_resume_analyses',
        'ai_activity_logs'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        EXECUTE format('DROP POLICY IF EXISTS service_role_all_%I ON %I;', tbl, tbl);
        EXECUTE format('CREATE POLICY service_role_all_%I ON %I FOR ALL USING (is_service_role()) WITH CHECK (is_service_role());', tbl, tbl);
    END LOOP;
END;
$$;

-- 3. Public Reference Data Read Policies
DROP POLICY IF EXISTS public_read_departments ON departments;
CREATE POLICY public_read_departments ON departments FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS public_read_skills ON skills;
CREATE POLICY public_read_skills ON skills FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS public_read_roles ON roles;
CREATE POLICY public_read_roles ON roles FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS public_read_companies ON companies;
CREATE POLICY public_read_companies ON companies FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS public_read_jobs ON jobs;
CREATE POLICY public_read_jobs ON jobs FOR SELECT USING (status = 'active');

DROP POLICY IF EXISTS public_read_job_skills ON job_skills;
CREATE POLICY public_read_job_skills ON job_skills FOR SELECT USING (TRUE);

-- 4. Student Private Profile Policies
DROP POLICY IF EXISTS student_manage_own_profile ON students;
CREATE POLICY student_manage_own_profile ON students FOR ALL USING (
    is_service_role() OR user_id = (SELECT id FROM users WHERE email = auth.jwt() ->> 'email')
);

DROP POLICY IF EXISTS student_manage_skills ON student_skills;
CREATE POLICY student_manage_skills ON student_skills FOR ALL USING (
    is_service_role() OR student_id = (SELECT s.id FROM students s JOIN users u ON s.user_id = u.id WHERE u.email = auth.jwt() ->> 'email')
);

DROP POLICY IF EXISTS student_manage_projects ON projects;
CREATE POLICY student_manage_projects ON projects FOR ALL USING (
    is_service_role() OR student_id = (SELECT s.id FROM students s JOIN users u ON s.user_id = u.id WHERE u.email = auth.jwt() ->> 'email')
);

DROP POLICY IF EXISTS student_manage_certifications ON certifications;
CREATE POLICY student_manage_certifications ON certifications FOR ALL USING (
    is_service_role() OR student_id = (SELECT s.id FROM students s JOIN users u ON s.user_id = u.id WHERE u.email = auth.jwt() ->> 'email')
);

-- 5. Student AI Simulator & Career Twin Policies
DROP POLICY IF EXISTS student_manage_interview_sessions ON ai_interview_sessions;
CREATE POLICY student_manage_interview_sessions ON ai_interview_sessions FOR ALL USING (
    is_service_role() OR student_id = (SELECT s.id FROM students s JOIN users u ON s.user_id = u.id WHERE u.email = auth.jwt() ->> 'email')
);

DROP POLICY IF EXISTS student_manage_career_twin ON ai_career_twins;
CREATE POLICY student_manage_career_twin ON ai_career_twins FOR ALL USING (
    is_service_role() OR student_id = (SELECT s.id FROM students s JOIN users u ON s.user_id = u.id WHERE u.email = auth.jwt() ->> 'email')
);

DROP POLICY IF EXISTS student_manage_roadmaps ON ai_roadmaps;
CREATE POLICY student_manage_roadmaps ON ai_roadmaps FOR ALL USING (
    is_service_role() OR student_id = (SELECT s.id FROM students s JOIN users u ON s.user_id = u.id WHERE u.email = auth.jwt() ->> 'email')
);

DROP POLICY IF EXISTS student_manage_resume_analyses ON ai_resume_analyses;
CREATE POLICY student_manage_resume_analyses ON ai_resume_analyses FOR ALL USING (
    is_service_role() OR student_id = (SELECT s.id FROM students s JOIN users u ON s.user_id = u.id WHERE u.email = auth.jwt() ->> 'email')
);
