from collections import Counter
from extensions import db
from models.student import Student
from models.placement import Placement
from models.application import Application
from models.job import Job, JobSkill
from models.skill import Skill, StudentSkill
from models.department import Department
from models.company import Company
from models.recruiter import Recruiter


class AnalyticsService:
    """Service computing dynamic campus metrics, placement analytics, and skill gap intelligence."""

    @staticmethod
    def get_summary_kpis():
        total_students = Student.query.count()
        placed_students = Placement.query.count()
        eligible_students = Student.query.filter(Student.cgpa >= 6.5).count()
        return {
            "total_students": total_students,
            "placed_students": placed_students,
            "eligible_students": eligible_students,
            "placement_rate": round((placed_students / total_students * 100), 1) if total_students > 0 else 0.0,
            "total_jobs": Job.query.filter_by(status="active").count(),
            "total_applications": Application.query.count(),
            "active_companies": Company.query.count(),
            "active_recruiters": Recruiter.query.count()
        }

    @staticmethod
    def get_placement_analytics():
        total_students = Student.query.count()
        eligible_students = Student.query.filter(Student.cgpa >= 6.5).count()
        placements = Placement.query.all()
        total_placed = len(placements)

        packages = [p.package_lpa for p in placements if p.package_lpa]
        avg_package = round(sum(packages) / len(packages), 2) if packages else 0.0
        highest_package = max(packages) if packages else 0.0
        lowest_package = min(packages) if packages else 0.0
        
        # Sort for median
        sorted_pkgs = sorted(packages)
        median_package = 0.0
        if sorted_pkgs:
            mid = len(sorted_pkgs) // 2
            median_package = sorted_pkgs[mid] if len(sorted_pkgs) % 2 != 0 else round((sorted_pkgs[mid - 1] + sorted_pkgs[mid]) / 2, 2)

        # Department Breakdown
        departments = Department.query.order_by(Department.code).all()
        dept_stats = []
        for d in departments:
            enrolled = d.students.count()
            dept_placements = Placement.query.join(Student).filter(Student.department_id == d.id).all()
            placed = len(dept_placements)
            dept_pkgs = [p.package_lpa for p in dept_placements if p.package_lpa]
            dept_avg = round(sum(dept_pkgs) / len(dept_pkgs), 1) if dept_pkgs else 0.0
            rate = round(placed / enrolled * 100, 1) if enrolled > 0 else 0.0
            dept_stats.append({
                "id": d.id,
                "code": d.code,
                "name": d.name,
                "enrolled": enrolled,
                "placed": placed,
                "placement_rate": rate,
                "avg_package": dept_avg
            })

        # Recruitment Pipeline Funnel
        all_apps = Application.query.all()
        funnel = {
            "enrolled": total_students,
            "eligible": eligible_students,
            "applied": len(set(a.student_id for a in all_apps)),
            "shortlisted": len(set(a.student_id for a in all_apps if a.status in ("shortlisted", "interview", "selected", "placed"))),
            "interviewed": len(set(a.student_id for a in all_apps if a.status in ("interview", "selected", "placed"))),
            "placed": total_placed
        }

        # CTC Tier Distribution
        ctc_tiers = {
            "Under 8 LPA": len([p for p in packages if p < 8.0]),
            "8 - 12 LPA": len([p for p in packages if 8.0 <= p < 12.0]),
            "12 - 16 LPA": len([p for p in packages if 12.0 <= p < 16.0]),
            "16+ LPA": len([p for p in packages if p >= 16.0])
        }

        # Company hiring summary
        companies = Company.query.all()
        company_stats = []
        for c in companies:
            c_placements = Placement.query.filter_by(company_id=c.id).all()
            c_jobs = Job.query.filter_by(company_id=c.id).count()
            if c_placements or c_jobs > 0:
                c_pkgs = [p.package_lpa for p in c_placements if p.package_lpa]
                company_stats.append({
                    "name": c.name,
                    "industry": c.industry,
                    "location": c.location,
                    "drives_posted": c_jobs,
                    "hires": len(c_placements),
                    "avg_ctc": round(sum(c_pkgs) / len(c_pkgs), 1) if c_pkgs else 0.0
                })
        company_stats.sort(key=lambda x: (x["hires"], x["drives_posted"]), reverse=True)

        return {
            "summary": {
                "total_students": total_students,
                "eligible_students": eligible_students,
                "total_placed": total_placed,
                "placement_rate": round((total_placed / total_students * 100), 1) if total_students > 0 else 0.0,
                "avg_package": avg_package,
                "highest_package": highest_package,
                "lowest_package": lowest_package,
                "median_package": median_package,
                "total_companies": len(companies),
                "total_jobs": Job.query.count()
            },
            "dept_stats": dept_stats,
            "funnel": funnel,
            "ctc_tiers": ctc_tiers,
            "company_stats": company_stats,
            "recent_placements": placements[:8]
        }

    @staticmethod
    def get_campus_skill_gaps():
        # Skill demand across active jobs
        job_skills = JobSkill.query.all()
        demand_counter = Counter([js.skill.name for js in job_skills if js.skill])
        demand_required = Counter([js.skill.name for js in job_skills if js.skill and js.is_required])

        # Skill supply across students
        student_skills = StudentSkill.query.all()
        supply_counter = Counter([ss.skill.name for ss in student_skills if ss.skill])
        verified_supply = Counter([ss.skill.name for ss in student_skills if ss.skill and ss.verified])

        # Total counts
        all_skills = Skill.query.order_by(Skill.name).all()
        skill_dict = {s.name: s for s in all_skills}

        gaps = []
        for s in all_skills:
            demand = demand_counter.get(s.name, 0)
            supply = supply_counter.get(s.name, 0)
            gap = demand - supply
            status = "Deficit" if gap > 0 else ("Balanced" if gap == 0 else "Surplus")
            
            # Coverage percentage: what % of demand is met by current students
            coverage = round((supply / demand * 100), 1) if demand > 0 else 100.0

            gaps.append({
                "id": s.id,
                "name": s.name,
                "category": s.category,
                "demand": demand,
                "required_demand": demand_required.get(s.name, 0),
                "supply": supply,
                "verified_supply": verified_supply.get(s.name, 0),
                "gap": gap,
                "coverage": min(coverage, 100.0),
                "status": status
            })

        # Deficit priority skills (Demand > Supply or low coverage with high demand)
        deficit_skills = [g for g in gaps if g["gap"] > 0 or (g["demand"] >= 2 and g["supply"] <= 1)]
        deficit_skills.sort(key=lambda x: (x["gap"], x["demand"]), reverse=True)

        # Top demanded skills
        top_demanded = sorted([g for g in gaps if g["demand"] > 0], key=lambda x: x["demand"], reverse=True)[:10]

        # Category distribution of demand
        categories = Counter()
        for js in job_skills:
            if js.skill:
                categories[js.skill.category] += 1

        # Curated recommendations based on critical gaps
        recommendations = []
        for ds in deficit_skills[:5]:
            recommendations.append({
                "skill": ds["name"],
                "category": ds["category"].capitalize(),
                "demand": ds["demand"],
                "supply": ds["supply"],
                "deficit": ds["gap"] if ds["gap"] > 0 else 1,
                "action": f"Organize hands-on 3-week bootcamp / certification drive on {ds['name']}",
                "priority": "Critical" if ds["demand"] >= 3 else "High"
            })

        return {
            "total_skills": len(all_skills),
            "skills_in_demand": len([g for g in gaps if g["demand"] > 0]),
            "deficit_count": len(deficit_skills),
            "surplus_count": len([g for g in gaps if g["gap"] < 0]),
            "all_gaps": gaps,
            "top_demanded": top_demanded,
            "deficit_skills": deficit_skills,
            "category_distribution": dict(categories),
            "recommendations": recommendations
        }

