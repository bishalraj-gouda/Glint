-- ==============================================================================
-- PlacementIQ AI (Campus-Link) - Supabase PostgreSQL Schema Migration 004
-- Foundational Reference Taxonomy, Skills, and Sample Opportunities
-- ==============================================================================

-- 1. Base RBAC Roles
INSERT INTO roles (name, description) VALUES
('STUDENT', 'Campus candidate accessing career twins, simulator, and job applications'),
('RECRUITER', 'Enterprise talent partner publishing requisitions and scheduling rounds'),
('ADMIN', 'Campus placement director and institutional analytics officer')
ON CONFLICT (name) DO NOTHING;

-- 2. Academic Departments
INSERT INTO departments (code, name) VALUES
('CSE', 'Computer Science & Engineering'),
('IT', 'Information Technology'),
('DS', 'Data Science & Artificial Intelligence'),
('ECE', 'Electronics & Communication Engineering')
ON CONFLICT (code) DO NOTHING;

-- 3. Core Skills Taxonomy (37 standardized skills)
INSERT INTO skills (name, category) VALUES
-- Languages & Frameworks
('Python', 'technical'),
('SQL', 'technical'),
('Java', 'technical'),
('Spring Boot', 'technical'),
('JavaScript', 'technical'),
('TypeScript', 'technical'),
('React.js', 'technical'),
('Node.js', 'technical'),
('HTML5 & CSS3', 'technical'),
('C++', 'technical'),
('Go', 'technical'),
('REST APIs', 'technical'),
('GraphQL', 'technical'),
('Data Structures & Algorithms', 'technical'),

-- Data, Analytics & AI/ML
('Power BI', 'tool'),
('Tableau', 'tool'),
('Advanced Excel', 'tool'),
('Pandas & NumPy', 'technical'),
('Scikit-Learn', 'technical'),
('PyTorch', 'technical'),
('TensorFlow', 'technical'),
('Machine Learning', 'domain'),
('Applied Statistics', 'domain'),
('Data Modeling', 'domain'),

-- Cloud, DevOps & Databases
('AWS', 'tool'),
('Google Cloud Platform', 'tool'),
('Docker', 'tool'),
('Kubernetes', 'tool'),
('Git & GitHub', 'tool'),
('Linux', 'tool'),
('PostgreSQL', 'tool'),
('MongoDB', 'tool'),
('Apache Kafka', 'tool'),

-- Professional & Domain Competencies
('Problem Solving', 'soft'),
('Communication', 'soft'),
('System Design', 'domain'),
('Agile Methodology', 'domain')
ON CONFLICT (name) DO NOTHING;

-- 4. Benchmark Companies
INSERT INTO companies (name, website, industry, logo_url, description, location) VALUES
('Nexus Technologies', 'https://nexustech.example.com', 'Enterprise SaaS & Cloud', 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=100', 'Global cloud computing and enterprise platform solutions.', 'Bangalore, India'),
('Apex FinTech Solutions', 'https://apexfintech.example.com', 'Financial Technology', 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=100', 'Next-generation algorithmic trading and payment systems.', 'Hyderabad, India'),
('FinPulse Global', 'https://finpulse.example.com', 'Banking & AI Automation', 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=100', 'Institutional banking automation and risk intelligence platforms.', 'Mumbai, India'),
('CloudScale Systems', 'https://cloudscale.example.com', 'Infrastructure & DevOps', 'https://images.unsplash.com/photo-1542744094-3a31f272c490?w=100', 'High-throughput distributed systems and Kubernetes infrastructure.', 'Pune, India'),
('Dataminds Analytics', 'https://dataminds.example.com', 'AI & Big Data', 'https://images.unsplash.com/photo-1551836022-d5d88e9218df?w=100', 'Predictive modeling, data lakes, and generative AI analytics.', 'Bangalore / Remote')
ON CONFLICT (name) DO NOTHING;
