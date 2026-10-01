import sys
from pathlib import Path

# Add project root to sys.path so script can be executed standalone
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import datetime
from extensions import db
from models.user import User
from models.department import Department
from models.company import Company
from models.recruiter import Recruiter
from models.student import Student
from models.skill import Skill, StudentSkill
from models.project import Project
from models.certification import Certification
from models.job import Job, JobSkill
from models.application import Application
from models.interview import Interview
from models.placement import Placement


def seed_database():
    """Populate database with comprehensive, internally consistent placement data."""
    # Prevent duplicate seed runs
    if User.query.filter_by(email="admin@placementiq.ai").first():
        print("Database already contains seed data. Skipping re-seed.")
        return

    print("Seeding Departments...")
    departments = [
        Department(code="CSE", name="Computer Science & Engineering"),
        Department(code="IT", name="Information Technology"),
        Department(code="DS", name="Data Science & Artificial Intelligence"),
        Department(code="ECE", name="Electronics & Communication Engineering"),
    ]
    db.session.add_all(departments)
    db.session.flush()

    dept_map = {d.code: d.id for d in departments}

    print("Seeding Skills Taxonomy (35+ skills)...")
    skill_definitions = [
        # Technical / Languages & Frameworks
        ("Python", "technical"),
        ("SQL", "technical"),
        ("Java", "technical"),
        ("Spring Boot", "technical"),
        ("JavaScript", "technical"),
        ("TypeScript", "technical"),
        ("React.js", "technical"),
        ("Node.js", "technical"),
        ("HTML5 & CSS3", "technical"),
        ("C++", "technical"),
        ("Go", "technical"),
        ("REST APIs", "technical"),
        ("GraphQL", "technical"),
        ("Data Structures & Algorithms", "technical"),
        
        # Data & AI/ML
        ("Power BI", "tool"),
        ("Tableau", "tool"),
        ("Advanced Excel", "tool"),
        ("Pandas & NumPy", "technical"),
        ("Scikit-Learn", "technical"),
        ("PyTorch", "technical"),
        ("TensorFlow", "technical"),
        ("Machine Learning", "domain"),
        ("Applied Statistics", "domain"),
        ("Data Modeling", "domain"),
        
        # Cloud, DevOps & Databases
        ("AWS", "tool"),
        ("Google Cloud Platform", "tool"),
        ("Docker", "tool"),
        ("Kubernetes", "tool"),
        ("Git & GitHub", "tool"),
        ("Linux", "tool"),
        ("PostgreSQL", "tool"),
        ("MongoDB", "tool"),
        ("Apache Kafka", "tool"),
        
        # Soft & Professional Skills
        ("Problem Solving", "soft"),
        ("Communication", "soft"),
        ("System Design", "domain"),
        ("Agile Methodology", "domain"),
    ]

    skill_objs = {}
    for name, cat in skill_definitions:
        sk = Skill(name=name, category=cat)
        db.session.add(sk)
        skill_objs[name] = sk
    db.session.flush()

    print("Seeding Companies...")
    companies = [
        Company(
            name="Nexus Technologies",
            website="https://nexustech.example.com",
            industry="Enterprise SaaS & AI",
            logo_url="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=100&auto=format&fit=crop&q=80",
            description="Leading AI-powered enterprise workflow and analytics platform.",
            location="Bangalore, India"
        ),
        Company(
            name="CloudScale Systems",
            website="https://cloudscale.example.com",
            industry="Cloud Infrastructure & DevOps",
            logo_url="https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=100&auto=format&fit=crop&q=80",
            description="High-performance multi-cloud observability and security platforms.",
            location="Hyderabad, India"
        ),
        Company(
            name="FinPulse Global",
            website="https://finpulse.example.com",
            industry="Fintech & Quantitative Analytics",
            logo_url="https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=100&auto=format&fit=crop&q=80",
            description="Algorithmic trading and payment rails infrastructure for financial institutions.",
            location="Mumbai, India"
        ),
        Company(
            name="HealthAI Labs",
            website="https://healthai.example.com",
            industry="HealthTech & BioInformatics",
            logo_url="https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=100&auto=format&fit=crop&q=80",
            description="Deep learning diagnostics and predictive medical analytics.",
            location="Bangalore, India"
        ),
        Company(
            name="Apex Consumer Tech",
            website="https://apextech.example.com",
            industry="E-Commerce & Digital Products",
            logo_url="https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=100&auto=format&fit=crop&q=80",
            description="Hyper-scale mobile commerce and real-time logistics network.",
            location="Gurugram, India"
        ),
    ]
    db.session.add_all(companies)
    db.session.flush()

    print("Seeding Users & Accounts...")
    # 1. Admin User
    admin_user = User(email="admin@placementiq.ai", role="admin")
    admin_user.set_password("Admin@123")
    db.session.add(admin_user)

    # 2. Recruiters (5 + Demo)
    recruiter_data = [
        ("recruiter@demo.com", "Demo Recruiter", companies[0].id, "Lead Technical Talent Partner", "+91 99999 88888"),
        ("priya.recruiter@nexustech.com", "Priya Nair", companies[0].id, "Principal Talent Partner", "+91 98765 43210"),
        ("vikram.hr@cloudscale.io", "Vikram Malhotra", companies[1].id, "Lead Tech Recruiter", "+91 98765 43211"),
        ("siddharth.talent@finpulse.com", "Siddharth Rao", companies[2].id, "Head of Campus Hiring", "+91 98765 43212"),
        ("neha.talent@healthai.com", "Neha Kapoor", companies[3].id, "Senior Talent Acquisition", "+91 98765 43213"),
        ("arjun.hr@apextech.com", "Arjun Mehta", companies[4].id, "University Recruiting Lead", "+91 98765 43214"),
    ]

    recruiter_objs = []
    for email, name, comp_id, desig, phone in recruiter_data:
        u = User(email=email, role="recruiter")
        u.set_password("Recruiter@123")
        db.session.add(u)
        db.session.flush()

        rec = Recruiter(user_id=u.id, company_id=comp_id, name=name, designation=desig, phone=phone)
        db.session.add(rec)
        recruiter_objs.append(rec)
    db.session.flush()

    print("Seeding 10 Job Postings with Skill Requirements...")
    job_templates = [
        # 1. Data Analyst (Nexus Tech)
        {
            "company_id": companies[0].id,
            "recruiter_id": recruiter_objs[0].id,
            "title": "Associate Data Analyst",
            "role_category": "Data Science & Analytics",
            "description": "Analyze business metrics, design executive dashboards, and build SQL transformation pipelines for enterprise clients.",
            "min_cgpa": 7.0,
            "experience_level": "Fresher (0-1 yrs)",
            "location": "Bangalore / Hybrid",
            "salary_min": 7.5,
            "salary_max": 11.0,
            "required": ["SQL", "Python", "Power BI", "Applied Statistics"],
            "preferred": ["Tableau", "Pandas & NumPy", "Problem Solving"]
        },
        # 2. Junior Machine Learning Engineer (Nexus Tech)
        {
            "company_id": companies[0].id,
            "recruiter_id": recruiter_objs[0].id,
            "title": "Junior Machine Learning Engineer",
            "role_category": "AI / Machine Learning",
            "description": "Develop supervised and unsupervised predictive models, feature extraction pipelines, and inference microservices.",
            "min_cgpa": 8.0,
            "experience_level": "Fresher (0-1 yrs)",
            "location": "Bangalore",
            "salary_min": 10.0,
            "salary_max": 16.0,
            "required": ["Python", "Machine Learning", "PyTorch", "Pandas & NumPy"],
            "preferred": ["Docker", "Applied Statistics", "Git & GitHub"]
        },
        # 3. Cloud DevOps Engineer (CloudScale)
        {
            "company_id": companies[1].id,
            "recruiter_id": recruiter_objs[1].id,
            "title": "Graduate Cloud DevOps Engineer",
            "role_category": "Cloud & Infrastructure",
            "description": "Automate CI/CD deployments, orchestrate Kubernetes clusters, and monitor high-availability cloud infrastructure on AWS.",
            "min_cgpa": 7.2,
            "experience_level": "Fresher (0-1 yrs)",
            "location": "Hyderabad",
            "salary_min": 8.5,
            "salary_max": 13.0,
            "required": ["Linux", "Docker", "AWS", "Git & GitHub"],
            "preferred": ["Kubernetes", "Python", "Problem Solving"]
        },
        # 4. Site Reliability Engineer (CloudScale)
        {
            "company_id": companies[1].id,
            "recruiter_id": recruiter_objs[1].id,
            "title": "Associate SRE",
            "role_category": "Cloud & Infrastructure",
            "description": "Maintain reliability, scalability, and disaster recovery pipelines for high-throughput microservices.",
            "min_cgpa": 7.5,
            "experience_level": "Fresher (0-1 yrs)",
            "location": "Remote",
            "salary_min": 9.0,
            "salary_max": 14.0,
            "required": ["Linux", "Go", "Docker", "System Design"],
            "preferred": ["Kubernetes", "AWS", "Apache Kafka"]
        },
        # 5. Full Stack Developer (Apex Consumer Tech)
        {
            "company_id": companies[4].id,
            "recruiter_id": recruiter_objs[4].id,
            "title": "Graduate Full Stack Developer",
            "role_category": "Software Engineering",
            "description": "Build high-performance web applications using modern React frontends and scalable Node.js/PostgreSQL microservices.",
            "min_cgpa": 7.0,
            "experience_level": "Fresher (0-1 yrs)",
            "location": "Gurugram / Hybrid",
            "salary_min": 8.0,
            "salary_max": 12.5,
            "required": ["React.js", "Node.js", "JavaScript", "SQL"],
            "preferred": ["TypeScript", "HTML5 & CSS3", "REST APIs"]
        },
        # 6. Frontend Engineer (Apex Consumer Tech)
        {
            "company_id": companies[4].id,
            "recruiter_id": recruiter_objs[4].id,
            "title": "Frontend UI/UX Engineer",
            "role_category": "Software Engineering",
            "description": "Craft responsive, accessible user interfaces with micro-animations and state management for consumer web platforms.",
            "min_cgpa": 6.8,
            "experience_level": "Fresher (0-1 yrs)",
            "location": "Gurugram",
            "salary_min": 7.0,
            "salary_max": 11.0,
            "required": ["React.js", "JavaScript", "HTML5 & CSS3"],
            "preferred": ["TypeScript", "REST APIs", "Communication"]
        },
        # 7. Backend Java Engineer (FinPulse Global)
        {
            "company_id": companies[2].id,
            "recruiter_id": recruiter_objs[2].id,
            "title": "Backend Java Engineer",
            "role_category": "Software Engineering",
            "description": "Architect mission-critical payment processing engines and distributed ledger ledger systems with Spring Boot.",
            "min_cgpa": 7.8,
            "experience_level": "Fresher (0-1 yrs)",
            "location": "Mumbai",
            "salary_min": 11.0,
            "salary_max": 18.0,
            "required": ["Java", "Spring Boot", "SQL", "Data Structures & Algorithms"],
            "preferred": ["PostgreSQL", "Apache Kafka", "System Design"]
        },
        # 8. Quantitative Software Analyst (FinPulse Global)
        {
            "company_id": companies[2].id,
            "recruiter_id": recruiter_objs[2].id,
            "title": "Quantitative Software Analyst",
            "role_category": "Fintech & Quantitative Analytics",
            "description": "Write numerical simulation algorithms, backtest portfolio strategies, and optimize low-latency calculation pipelines.",
            "min_cgpa": 8.2,
            "experience_level": "Fresher (0-1 yrs)",
            "location": "Mumbai",
            "salary_min": 12.0,
            "salary_max": 20.0,
            "required": ["Python", "Applied Statistics", "C++", "Pandas & NumPy"],
            "preferred": ["Advanced Excel", "Problem Solving", "Machine Learning"]
        },
        # 9. AI Research Associate (HealthAI Labs)
        {
            "company_id": companies[3].id,
            "recruiter_id": recruiter_objs[3].id,
            "title": "AI Bio-Data Research Associate",
            "role_category": "AI / Machine Learning",
            "description": "Train computer vision and biological sequence models for early pathology detection and clinical trials.",
            "min_cgpa": 8.0,
            "experience_level": "Fresher (0-1 yrs)",
            "location": "Bangalore",
            "salary_min": 9.5,
            "salary_max": 15.0,
            "required": ["Python", "PyTorch", "Machine Learning", "Applied Statistics"],
            "preferred": ["Linux", "Git & GitHub", "Communication"]
        },
        # 10. Software QA & Automation Engineer (HealthAI Labs)
        {
            "company_id": companies[3].id,
            "recruiter_id": recruiter_objs[3].id,
            "title": "Software Test & Automation Engineer",
            "role_category": "Software Quality",
            "description": "Design automated end-to-end integration and API tests for healthcare data compliance and stability.",
            "min_cgpa": 6.8,
            "experience_level": "Fresher (0-1 yrs)",
            "location": "Bangalore",
            "salary_min": 6.5,
            "salary_max": 9.5,
            "required": ["Python", "REST APIs", "Git & GitHub"],
            "preferred": ["SQL", "Linux", "Problem Solving"]
        },
    ]

    job_objs = []
    for jd in job_templates:
        job = Job(
            company_id=jd["company_id"],
            recruiter_id=jd["recruiter_id"],
            title=jd["title"],
            role_category=jd["role_category"],
            description=jd["description"],
            min_cgpa=jd["min_cgpa"],
            experience_level=jd["experience_level"],
            location=jd["location"],
            salary_min=jd["salary_min"],
            salary_max=jd["salary_max"],
            status="active",
            deadline=datetime.date.today() + datetime.timedelta(days=30)
        )
        db.session.add(job)
        db.session.flush()
        job_objs.append(job)

        for req_skill in jd["required"]:
            if req_skill in skill_objs:
                db.session.add(JobSkill(job_id=job.id, skill_id=skill_objs[req_skill].id, is_required=True, importance_weight=1.5))
        for pref_skill in jd["preferred"]:
            if pref_skill in skill_objs:
                db.session.add(JobSkill(job_id=job.id, skill_id=skill_objs[pref_skill].id, is_required=False, importance_weight=1.0))

    db.session.flush()

    print("Seeding 20 Students with Diverse Profiles...")
    student_profiles = [
        # 0. Demo Student (Primary demo evaluation user)
        {
            "email": "student@demo.com",
            "name": "Demo Student",
            "roll": "DEMO-2026",
            "dept": "CSE",
            "year": 4,
            "cgpa": 8.75,
            "role": "Full Stack Developer",
            "headline": "Full Stack Engineer & AI Systems Developer",
            "github_url": "https://github.com/octocat",
            "linkedin_url": "https://linkedin.com/in/demostudent",
            "portfolio_url": "https://demostudent.dev",
            "bio": "Passionate full-stack software engineer with expertise in React, Flask, and distributed cloud microservices.",
            "readiness": 90.0,
            "skills": [("Python", "advanced"), ("JavaScript", "advanced"), ("React.js", "advanced"), ("SQL", "advanced"), ("Docker", "intermediate"), ("REST APIs", "advanced"), ("Git & GitHub", "advanced")],
            "projects": [
                ("PlacementIQ Intelligent Recruitment Engine", "Full-stack placement preparation portal with AI ATS analysis, vector candidate matcher, and mock interview studio.", "Python, Flask, React, PostgreSQL"),
                ("Microservices Event Stream Engine", "Distributed real-time task processing engine using Redis pub/sub and containerized worker nodes.", "Python, Docker, Redis")
            ],
            "certs": [("AWS Certified Solutions Architect", "AWS", "2024-04-10")]
        },
        # 1. Rahul Sharma (Data Analyst archetype - primary demo user)
        {
            "email": "rahul.sharma@campus.edu",
            "name": "Rahul Sharma",
            "roll": "21CS001",
            "dept": "DS",
            "year": 4,
            "cgpa": 8.4,
            "role": "Data Analyst",
            "bio": "Passionate data analyst skilled in SQL, Python data munging, and interactive business intelligence storytelling.",
            "readiness": 82.0,
            "skills": [("Python", "advanced"), ("SQL", "advanced"), ("Power BI", "intermediate"), ("Pandas & NumPy", "advanced"), ("Advanced Excel", "advanced"), ("Applied Statistics", "intermediate"), ("Communication", "intermediate")],
            "projects": [
                ("Sales Performance & Churn BI Dashboard", "End-to-end Power BI report tracking monthly recurring revenue, customer churn vectors, and SQL pipeline extraction.", "Power BI, SQL, Python"),
                ("Retail Market Basket Analysis", "Association rule mining using Apriori algorithm on 500k grocery records to discover cross-selling opportunities.", "Python, Pandas, Scikit-Learn")
            ],
            "certs": [("Google Data Analytics Professional Certificate", "Google", "2024-05-15")]
        },
        # 2. Ananya Verma (Full Stack Developer archetype - secondary demo user)
        {
            "email": "ananya.verma@campus.edu",
            "name": "Ananya Verma",
            "roll": "21CS002",
            "dept": "CSE",
            "year": 4,
            "cgpa": 8.8,
            "role": "Full Stack Developer",
            "bio": "Full stack engineer passionate about sleek responsive interfaces, scalable microservices, and modern web architectures.",
            "readiness": 88.0,
            "skills": [("React.js", "advanced"), ("JavaScript", "advanced"), ("TypeScript", "intermediate"), ("Node.js", "advanced"), ("HTML5 & CSS3", "advanced"), ("SQL", "intermediate"), ("REST APIs", "advanced"), ("Git & GitHub", "advanced")],
            "projects": [
                ("Campus Event Management Hub", "Full stack portal with real-time seat reservation, JWT authentication, and responsive UI.", "React.js, Node.js, PostgreSQL"),
                ("Collaborative Markdown Workspace", "WebSocket-based live markdown document editing tool with version rollback.", "TypeScript, React.js, Express")
            ],
            "certs": [("Meta Front-End Developer Specialization", "Meta", "2024-03-20")]
        },
        # 3. Rohit Kumar (Java Backend archetype - third demo user)
        {
            "email": "rohit.kumar@campus.edu",
            "name": "Rohit Kumar",
            "roll": "21CS003",
            "dept": "IT",
            "year": 4,
            "cgpa": 8.1,
            "role": "Backend Engineer",
            "bio": "Backend system developer focused on robust Java, Spring Boot microservices, high concurrency, and distributed caching.",
            "readiness": 79.0,
            "skills": [("Java", "advanced"), ("Spring Boot", "advanced"), ("SQL", "advanced"), ("Data Structures & Algorithms", "advanced"), ("PostgreSQL", "intermediate"), ("Docker", "intermediate"), ("Problem Solving", "advanced")],
            "projects": [
                ("High-Throughput Order Processing API", "Event-driven Spring Boot service processing 2,000 requests/sec with Redis caching and PostgreSQL persistence.", "Java, Spring Boot, PostgreSQL, Docker"),
                ("Distributed Key-Value Store", "Lightweight custom replicated key-value storage engine implementing consistent hashing.", "Java, Data Structures")
            ],
            "certs": [("Oracle Certified Professional: Java SE 17", "Oracle", "2023-11-10")]
        },
        # 4. Sneha Patel (AI/ML archetype)
        {
            "email": "sneha.patel@campus.edu",
            "name": "Sneha Patel",
            "roll": "21CS004",
            "dept": "DS",
            "year": 4,
            "cgpa": 9.2,
            "role": "Machine Learning Engineer",
            "bio": "Deep learning and computer vision researcher with publications in medical imaging and edge AI inference.",
            "readiness": 91.0,
            "skills": [("Python", "advanced"), ("PyTorch", "advanced"), ("Machine Learning", "advanced"), ("Pandas & NumPy", "advanced"), ("Applied Statistics", "advanced"), ("Linux", "intermediate"), ("Git & GitHub", "intermediate")],
            "projects": [
                ("Chest X-Ray Pneumonia Classifier", "ResNet50 convolutional neural network achieving 96.4% test AUC for multi-label thoracic pathology detection.", "Python, PyTorch, Scikit-Learn"),
                ("Automated Document Information Extractor", "BERT-based named entity recognition for automated clinical summary parsing.", "Python, Transformers, PyTorch")
            ],
            "certs": [("Deep Learning Specialization", "DeepLearning.AI", "2024-01-18")]
        },
        # 5. Aditi Rao (DevOps & Cloud archetype)
        {
            "email": "aditi.rao@campus.edu",
            "name": "Aditi Rao",
            "roll": "21CS005",
            "dept": "IT",
            "year": 4,
            "cgpa": 7.6,
            "role": "Cloud DevOps Engineer",
            "bio": "Cloud and infrastructure automation enthusiast who loves Docker containers, Terraform, and resilient CI/CD pipelines.",
            "readiness": 76.0,
            "skills": [("Linux", "advanced"), ("Docker", "advanced"), ("AWS", "intermediate"), ("Kubernetes", "beginner"), ("Git & GitHub", "advanced"), ("Python", "intermediate")],
            "projects": [
                ("Multi-Tier Automated Kubernetes Deployment", "Automated deployment of microservices using Helm charts and GitHub Actions CI/CD onto AWS EKS.", "AWS, Docker, Kubernetes, Linux"),
                ("Serverless Log Ingestion Pipeline", "AWS Lambda and S3 based log collection pipeline with alert notifications via SNS.", "AWS, Python, Linux")
            ],
            "certs": [("AWS Certified Solutions Architect – Associate", "Amazon Web Services", "2024-04-12")]
        },
        # 6. Karthik Nair (Embedded & ECE Systems)
        {
            "email": "karthik.nair@campus.edu",
            "name": "Karthik Nair",
            "roll": "21EC006",
            "dept": "ECE",
            "year": 4,
            "cgpa": 7.9,
            "role": "Embedded Software Engineer",
            "bio": "ECE student specializing in low-level C++, microcontroller firmware, and IoT edge devices.",
            "readiness": 72.0,
            "skills": [("C++", "advanced"), ("Linux", "intermediate"), ("Python", "intermediate"), ("Problem Solving", "intermediate")],
            "projects": [
                ("Smart Microgrid Energy Monitor", "ESP32-based energy telemetry node sending power factor statistics over MQTT to cloud dashboard.", "C++, Linux, MQTT")
            ],
            "certs": []
        },
        # 7. Meera Iyer (UI/UX Frontend)
        {
            "email": "meera.iyer@campus.edu",
            "name": "Meera Iyer",
            "roll": "21CS007",
            "dept": "CSE",
            "year": 4,
            "cgpa": 7.8,
            "role": "Frontend Developer",
            "bio": "Frontend designer-developer with a keen eye for typography, micro-interactions, and accessibility standards.",
            "readiness": 80.0,
            "skills": [("React.js", "advanced"), ("HTML5 & CSS3", "advanced"), ("JavaScript", "advanced"), ("TypeScript", "intermediate"), ("Communication", "advanced")],
            "projects": [
                ("Minimalist Design System & Component Library", "Accessible UI system with 30+ reusable React components adhering to WCAG 2.1 AA.", "React.js, HTML5 & CSS3")
            ],
            "certs": []
        },
        # 8. Tanmay Joshi (Quantitative Finance)
        {
            "email": "tanmay.joshi@campus.edu",
            "name": "Tanmay Joshi",
            "roll": "21CS008",
            "dept": "CSE",
            "year": 4,
            "cgpa": 9.4,
            "role": "Quantitative Analyst",
            "bio": "Mathematics and algorithms geek building fast quantitative trading backtesting engines.",
            "readiness": 90.0,
            "skills": [("Python", "advanced"), ("C++", "advanced"), ("Applied Statistics", "advanced"), ("Pandas & NumPy", "advanced"), ("Data Structures & Algorithms", "advanced"), ("Problem Solving", "advanced")],
            "projects": [
                ("High-Frequency Backtesting Simulator", "Vectorized Python backtesting suite simulating order book slippage and execution costs across 10 years of tick data.", "Python, Pandas & NumPy, C++")
            ],
            "certs": [("Financial Engineering and Risk Management", "Columbia University / Coursera", "2024-02-10")]
        },
        # 9. Pooja Kulkarni (QA & Automation)
        {
            "email": "pooja.kulkarni@campus.edu",
            "name": "Pooja Kulkarni",
            "roll": "21IT009",
            "dept": "IT",
            "year": 4,
            "cgpa": 7.3,
            "role": "QA Automation Engineer",
            "bio": "Dedicated QA engineer with expertise in automated regression testing, Selenium, and REST API validation.",
            "readiness": 71.0,
            "skills": [("Python", "intermediate"), ("REST APIs", "intermediate"), ("SQL", "intermediate"), ("Git & GitHub", "intermediate"), ("Problem Solving", "intermediate")],
            "projects": [
                ("API Regression Test Suite", "Automated PyTest and Postman collection verifying 120+ REST endpoints on every deployment.", "Python, REST APIs")
            ],
            "certs": []
        },
        # 10. Varun Singhania (Cloud SRE)
        {
            "email": "varun.singhania@campus.edu",
            "name": "Varun Singhania",
            "roll": "21CS010",
            "dept": "CSE",
            "year": 4,
            "cgpa": 8.0,
            "role": "Site Reliability Engineer",
            "bio": "System performance specialist interested in Linux internals, observability metrics, and Go microservices.",
            "readiness": 77.0,
            "skills": [("Linux", "advanced"), ("Go", "intermediate"), ("Docker", "intermediate"), ("System Design", "intermediate"), ("Git & GitHub", "intermediate")],
            "projects": [
                ("Distributed Metric Collector Daemon", "Lightweight daemon in Go collecting system load metrics and reporting to Prometheus.", "Go, Linux, Docker")
            ],
            "certs": []
        },
        # 11-20 Diverse additional students
        {
            "email": "sanya.mirza@campus.edu",
            "name": "Sanya Mirza",
            "roll": "21DS011",
            "dept": "DS",
            "year": 4,
            "cgpa": 8.3,
            "role": "Data Analyst",
            "bio": "Data enthusiast with strong analytical thinking and business problem structuring abilities.",
            "readiness": 75.0,
            "skills": [("Python", "intermediate"), ("SQL", "advanced"), ("Tableau", "intermediate"), ("Advanced Excel", "advanced")],
            "projects": [("Supply Chain Lead Time Predictor", "Predictive model for delivery lead times across fulfillment centers.", "Python, SQL")],
            "certs": []
        },
        {
            "email": "dev.bose@campus.edu",
            "name": "Dev Bose",
            "roll": "21CS012",
            "dept": "CSE",
            "year": 4,
            "cgpa": 7.5,
            "role": "Full Stack Developer",
            "bio": "Web developer with experience in Node, React, and MongoDB stack.",
            "readiness": 74.0,
            "skills": [("JavaScript", "advanced"), ("React.js", "intermediate"), ("Node.js", "intermediate"), ("MongoDB", "intermediate")],
            "projects": [("Fitness Activity Tracker", "MERN stack portal to log workouts and visualize calorie deficit curves.", "React.js, Node.js")],
            "certs": []
        },
        {
            "email": "harsh.vardhan@campus.edu",
            "name": "Harsh Vardhan",
            "roll": "21IT013",
            "dept": "IT",
            "year": 4,
            "cgpa": 7.1,
            "role": "Backend Engineer",
            "bio": "Java programmer learning Spring Boot and building clean modular APIs.",
            "readiness": 68.0,
            "skills": [("Java", "intermediate"), ("SQL", "intermediate"), ("REST APIs", "intermediate")],
            "projects": [("Banking Account Ledger", "Core banking transaction simulator with ACID compliance.", "Java, SQL")],
            "certs": []
        },
        {
            "email": "ritika.sen@campus.edu",
            "name": "Ritika Sen",
            "roll": "21DS014",
            "dept": "DS",
            "year": 4,
            "cgpa": 8.7,
            "role": "Machine Learning Engineer",
            "bio": "NLP enthusiast working on text summarization and sentiment analysis pipelines.",
            "readiness": 83.0,
            "skills": [("Python", "advanced"), ("Machine Learning", "advanced"), ("Pandas & NumPy", "advanced"), ("Scikit-Learn", "advanced")],
            "projects": [("Customer Review Sentiment Analyzer", "TF-IDF and Logistic Regression pipeline analyzing 50k hotel reviews.", "Python, Scikit-Learn")],
            "certs": []
        },
        {
            "email": "manish.tiwari@campus.edu",
            "name": "Manish Tiwari",
            "roll": "21EC015",
            "dept": "ECE",
            "year": 4,
            "cgpa": 6.9,
            "role": "Software Engineer",
            "bio": "ECE student transitioning to software development with strong C++ fundamentals.",
            "readiness": 66.0,
            "skills": [("C++", "advanced"), ("Data Structures & Algorithms", "intermediate"), ("Problem Solving", "intermediate")],
            "projects": [("Graph Shortest Path Navigator", "Implementation of Dijkstra and A* algorithms with graphical visualization.", "C++")],
            "certs": []
        },
        {
            "email": "divya.nambiar@campus.edu",
            "name": "Divya Nambiar",
            "roll": "21CS016",
            "dept": "CSE",
            "year": 4,
            "cgpa": 8.5,
            "role": "Cloud DevOps Engineer",
            "bio": "Aspiring cloud engineer passionate about continuous deployment and infrastructure monitoring.",
            "readiness": 78.0,
            "skills": [("Linux", "advanced"), ("AWS", "intermediate"), ("Docker", "intermediate"), ("Git & GitHub", "advanced")],
            "projects": [("Cloud Telemetry Dashboard", "Automated deployment of Prometheus and Grafana on AWS EC2.", "AWS, Linux")],
            "certs": []
        },
        {
            "email": "abhishek.yadav@campus.edu",
            "name": "Abhishek Yadav",
            "roll": "21IT017",
            "dept": "IT",
            "year": 4,
            "cgpa": 7.4,
            "role": "Full Stack Developer",
            "bio": "Enthusiastic web builder creating responsive SPAs and REST APIs.",
            "readiness": 72.0,
            "skills": [("JavaScript", "intermediate"), ("React.js", "intermediate"), ("HTML5 & CSS3", "advanced"), ("SQL", "intermediate")],
            "projects": [("Real-Time Polling App", "Live polling application with visual bar chart updates.", "JavaScript, HTML5 & CSS3")],
            "certs": []
        },
        {
            "email": "kavita.reddy@campus.edu",
            "name": "Kavita Reddy",
            "roll": "21DS018",
            "dept": "DS",
            "year": 4,
            "cgpa": 8.6,
            "role": "Data Analyst",
            "bio": "Data analyst focused on predictive dashboards, SQL querying, and executive KPI reporting.",
            "readiness": 81.0,
            "skills": [("SQL", "advanced"), ("Python", "intermediate"), ("Power BI", "advanced"), ("Advanced Excel", "advanced")],
            "projects": [("Healthcare Clinic Appointment Analytics", "Power BI dashboard tracking patient wait times and doctor utilization.", "Power BI, SQL")],
            "certs": []
        },
        {
            "email": "suresh.pandey@campus.edu",
            "name": "Suresh Pandey",
            "roll": "21CS019",
            "dept": "CSE",
            "year": 4,
            "cgpa": 8.0,
            "role": "Backend Engineer",
            "bio": "Backend engineer skilled in Java, Spring Boot, and relational database tuning.",
            "readiness": 77.0,
            "skills": [("Java", "advanced"), ("Spring Boot", "intermediate"), ("SQL", "advanced"), ("REST APIs", "intermediate")],
            "projects": [("Inventory Tracking Service", "Spring Boot microservice for warehouse item management.", "Java, Spring Boot, SQL")],
            "certs": []
        },
        {
            "email": "tarun.khanna@campus.edu",
            "name": "Tarun Khanna",
            "roll": "21EC020",
            "dept": "ECE",
            "year": 4,
            "cgpa": 7.2,
            "role": "Software Engineer",
            "bio": "Firmware and software developer with solid C++ and Linux experience.",
            "readiness": 69.0,
            "skills": [("C++", "advanced"), ("Linux", "intermediate"), ("Git & GitHub", "intermediate")],
            "projects": [("Serial Port Data Logger", "Cross-platform serial communication logger for hardware test benches.", "C++, Linux")],
            "certs": []
        },
    ]

    student_objs = []
    for sp in student_profiles:
        u = User(email=sp["email"], role="student")
        u.set_password("Student@123")
        db.session.add(u)
        db.session.flush()

        student = Student(
            user_id=u.id,
            roll_number=sp["roll"],
            name=sp["name"],
            department_id=dept_map[sp["dept"]],
            year=sp["year"],
            cgpa=sp["cgpa"],
            target_role=sp["role"],
            headline=sp.get("headline", f"{sp['role']} Specialist"),
            github_url=sp.get("github_url", "https://github.com/octocat"),
            linkedin_url=sp.get("linkedin_url", f"https://linkedin.com/in/{sp['roll'].lower()}"),
            portfolio_url=sp.get("portfolio_url", f"https://{sp['roll'].lower()}.dev"),
            bio=sp["bio"],
            readiness_score=sp["readiness"],
            avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={sp['roll']}"
        )
        db.session.add(student)
        db.session.flush()
        student_objs.append(student)

        # Attach skills
        for sk_name, level in sp["skills"]:
            if sk_name in skill_objs:
                ss = StudentSkill(
                    student_id=student.id,
                    skill_id=skill_objs[sk_name].id,
                    proficiency_level=level,
                    verified=True
                )
                db.session.add(ss)

        # Attach projects
        for title, desc, stack in sp["projects"]:
            p = Project(
                student_id=student.id,
                title=title,
                description=desc,
                tech_stack=stack,
                github_url="https://github.com/example/project"
            )
            db.session.add(p)

        # Attach certs
        for cname, org, dt in sp["certs"]:
            c = Certification(
                student_id=student.id,
                name=cname,
                issuing_org=org,
                issue_date=datetime.datetime.strptime(dt, "%Y-%m-%d").date()
            )
            db.session.add(c)

    db.session.flush()

    print("Seeding Realistic Applications, Interviews, and Placements...")
    # Student 0 (Rahul Sharma - Data Analyst) applies to Job 0 (Associate Data Analyst at Nexus Tech)
    app1 = Application(
        job_id=job_objs[0].id,
        student_id=student_objs[0].id,
        status="interview",
        match_score=87.0,
        match_breakdown_json='{"technical": 42, "projects": 18, "experience": 8, "education": 10, "reasons": ["Strong SQL & Python", "Relevant Power BI project"]}'
    )
    db.session.add(app1)
    db.session.flush()

    # Schedule upcoming interview for Rahul
    int1 = Interview(
        application_id=app1.id,
        scheduled_date=datetime.date.today() + datetime.timedelta(days=2),
        scheduled_time="10:30 AM",
        interview_type="technical",
        round_number=1,
        meeting_link_or_venue="https://meet.google.com/nex-data-round1",
        interviewer_name="Dr. Arvind Swaminathan (Lead Data Architect)",
        status="scheduled"
    )
    db.session.add(int1)

    # Student 1 (Ananya Verma - Full Stack) applied to Job 4 (Full Stack at Apex) and is Shortlisted
    app2 = Application(
        job_id=job_objs[4].id,
        student_id=student_objs[1].id,
        status="shortlisted",
        match_score=92.0,
        match_breakdown_json='{"technical": 48, "projects": 20, "experience": 9, "education": 10, "reasons": ["Advanced React & Node", "High GPA"]}'
    )
    db.session.add(app2)

    # Student 2 (Rohit Kumar - Java) applied to Job 6 (Backend Java at FinPulse) and is in Interview stage
    app3 = Application(
        job_id=job_objs[6].id,
        student_id=student_objs[2].id,
        status="interview",
        match_score=89.0,
        match_breakdown_json='{"technical": 45, "projects": 19, "experience": 8, "education": 10, "reasons": ["Strong Spring Boot & Concurrency"]}'
    )
    db.session.add(app3)
    db.session.flush()

    int3 = Interview(
        application_id=app3.id,
        scheduled_date=datetime.date.today() + datetime.timedelta(days=4),
        scheduled_time="02:00 PM",
        interview_type="technical",
        round_number=2,
        meeting_link_or_venue="https://finpulse.webex.com/meet/campus",
        interviewer_name="Siddharth Rao (VP Engineering)",
        status="scheduled"
    )
    db.session.add(int3)

    # Placed Students (Historical and current placements)
    # Student 3 (Sneha Patel - ML Engineer) placed at Nexus Technologies (Job 1)
    app4 = Application(
        job_id=job_objs[1].id,
        student_id=student_objs[3].id,
        status="placed",
        match_score=94.0
    )
    db.session.add(app4)
    db.session.flush()

    place1 = Placement(
        student_id=student_objs[3].id,
        job_id=job_objs[1].id,
        company_id=companies[0].id,
        package_lpa=14.5,
        placed_date=datetime.date.today() - datetime.timedelta(days=15),
        academic_year="2025-2026"
    )
    db.session.add(place1)

    # Student 7 (Tanmay Joshi) placed at FinPulse Global (Job 7)
    app5 = Application(
        job_id=job_objs[7].id,
        student_id=student_objs[7].id,
        status="placed",
        match_score=96.0
    )
    db.session.add(app5)
    db.session.flush()

    place2 = Placement(
        student_id=student_objs[7].id,
        job_id=job_objs[7].id,
        company_id=companies[2].id,
        package_lpa=18.0,
        placed_date=datetime.date.today() - datetime.timedelta(days=22),
        academic_year="2025-2026"
    )
    db.session.add(place2)

    # More applications to populate the pipeline
    app_configs = [
        (job_objs[2].id, student_objs[4].id, "shortlisted", 78.0), # Aditi at Cloud DevOps
        (job_objs[0].id, student_objs[10].id, "eligible", 72.0),   # Sanya at Data Analyst
        (job_objs[4].id, student_objs[11].id, "applied", 69.0),    # Dev at Full Stack
        (job_objs[6].id, student_objs[12].id, "applied", 64.0),    # Harsh at Backend Java
        (job_objs[1].id, student_objs[13].id, "shortlisted", 84.0),# Ritika at ML Engineer
        (job_objs[0].id, student_objs[17].id, "interview", 80.0),  # Kavita at Data Analyst
    ]

    for jid, sid, st, scr in app_configs:
        db.session.add(Application(job_id=jid, student_id=sid, status=st, match_score=scr))

    db.session.commit()
    print("Database seeding completed successfully!")


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_database()
