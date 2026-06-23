import os
import django
import random
from datetime import datetime, timedelta

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'health_survey_system.settings')
django.setup()

from django.utils import timezone
from apps.accounts.models import CustomUser
from apps.center.models import Center
from apps.subcenter.models import Subcenter
from apps.surveys.models import HealthSurvey, SurveyMember
from apps.forms_engine.models import FormDefinition, FormField

def seed():
    print("Deleting old seed data...")
    # Clear tables
    SurveyMember.objects.all().delete()
    HealthSurvey.objects.all().delete()
    FormDefinition.objects.all().delete()
    CustomUser.objects.all().delete()
    Subcenter.objects.all().delete()
    Center.objects.all().delete()

    print("Seeding HQ, Centers, and Subcenters...")
    # 1. Create Centers
    c1 = Center.objects.create(name="Trivandrum Central CHC", code="CHC-TVM", address="Medical College, Trivandrum")
    c2 = Center.objects.create(name="Ernakulam General Hospital CHC", code="CHC-EKM", address="MG Road, Ernakulam")

    # 2. Create Subcenters
    sc1 = Subcenter.objects.create(center=c1, name="Vellanad Subcenter", code="SC-VLD", address="Vellanad Junction")
    sc2 = Subcenter.objects.create(center=c1, name="Aryanad Subcenter", code="SC-ARN", address="Aryanad Road")
    sc3 = Subcenter.objects.create(center=c2, name="Kadavanthra Subcenter", code="SC-KDV", address="Kadavanthra East")

    print("Seeding Users...")
    # 3. Create Users
    # HQ Admin
    hq_admin = CustomUser.objects.create_superuser(
        username="hq_admin",
        password="admin123",
        role=CustomUser.Role.HQ,
        email="hq@health.gov.in"
    )

    # Center Admin
    center_admin = CustomUser.objects.create_user(
        username="center_admin",
        password="admin123",
        role=CustomUser.Role.CENTER,
        center=c1,
        email="center@health.gov.in"
    )

    # Subcenter Admin
    subcenter_admin = CustomUser.objects.create_user(
        username="subcenter_admin",
        password="admin123",
        role=CustomUser.Role.SUBCENTER,
        subcenter=sc1,
        email="subcenter@health.gov.in"
    )

    # Survey Conductors
    cond1 = CustomUser.objects.create_user(
        username="conductor_asha",
        password="admin123",
        role=CustomUser.Role.CONDUCTOR,
        subcenter=sc1,
        conductor_role=CustomUser.ConductorRole.ASHA,
        email="asha@health.gov.in"
    )
    cond2 = CustomUser.objects.create_user(
        username="conductor_jhi",
        password="admin123",
        role=CustomUser.Role.CONDUCTOR,
        subcenter=sc1,
        conductor_role=CustomUser.ConductorRole.JHI,
        email="jhi@health.gov.in"
    )
    cond3 = CustomUser.objects.create_user(
        username="conductor_jphn",
        password="admin123",
        role=CustomUser.Role.CONDUCTOR,
        subcenter=sc2,
        conductor_role=CustomUser.ConductorRole.JPHN,
        email="jphn@health.gov.in"
    )

    print("Seeding Dynamic Form templates...")
    # 4. Create Dynamic Form Definition
    f_def = FormDefinition.objects.create(
        name="Maternal Immunization Survey",
        identifier="maternal-immunization",
        description="Tracks maternal health vaccination details and booster status.",
        created_by=hq_admin
    )
    FormField.objects.create(form=f_def, label="Mother Name", field_type=FormField.FieldType.TEXT, required=True, order=1)
    FormField.objects.create(form=f_def, label="Date of Last Vaccination", field_type=FormField.FieldType.DATE, required=True, order=2)
    FormField.objects.create(form=f_def, label="Dose Stage", field_type=FormField.FieldType.SELECT, required=True, options="Dose 1, Dose 2, Booster", order=3)
    FormField.objects.create(form=f_def, label="General Remarks", field_type=FormField.FieldType.TEXTAREA, required=False, order=4)

    print("Seeding Health Surveys & Family Members...")
    # 5. Create core health surveys and members
    wards = ["Ward 1", "Ward 2", "Ward 3", "Ward 4"]
    panchayats = ["Vellanad Panchayat", "Aryanad Panchayat"]
    occupations = ["Farmer", "Teacher", "Laborer", "Homemaker", "Shopkeeper", "Driver"]
    diseases_pool = ["Fever", "Tuberculosis", "Hypertension", "Dengue", "Asthma", "Cholera"]

    # We will generate 25 surveys across last 8 weeks to populate trends and ML forecasts
    for i in range(25):
        cond = random.choice([cond1, cond2, cond3])
        subcent = cond.subcenter
        cent = subcent.center
        
        # Stagger dates
        weeks_ago = random.randint(0, 7)
        submit_date = timezone.now() - timedelta(weeks=weeks_ago, days=random.randint(0, 6))

        survey = HealthSurvey.objects.create(
            submitted_by=cond,
            submitted_role=cond.conductor_role,
            center=cent,
            subcenter=subcent,
            house_number=f"{random.randint(1, 150)}/{random.choice(['A','B','C',''])}",
            ward=random.choice(wards),
            panchayat=random.choice(panchayats),
            address=f"House near Temple/Church, Ward {i % 4 + 1}",
            family_head_name=f"Head {i+1}",
            family_members_count=random.randint(1, 4)
        )
        # Update submitted_at directly (auto_now_add override)
        HealthSurvey.objects.filter(id=survey.id).update(submitted_at=submit_date)

        # Seed members for this survey
        for m_idx in range(survey.family_members_count):
            age = random.randint(1, 80)
            gender = random.choice([SurveyMember.Gender.MALE, SurveyMember.Gender.FEMALE])
            
            # Healthcare logic cases
            is_preg = False
            if gender == SurveyMember.Gender.FEMALE and 20 <= age <= 40:
                is_preg = random.choice([True, False, False, False]) # 25% chance

            # Vaccination status
            vac = random.choice([
                SurveyMember.VaccinationStatus.FULLY,
                SurveyMember.VaccinationStatus.FULLY,
                SurveyMember.VaccinationStatus.PARTIALLY,
                SurveyMember.VaccinationStatus.NOT
            ])

            # BP
            bp_sys = None
            bp_dia = None
            if age > 40:
                bp_sys = random.randint(110, 160)
                bp_dia = random.randint(70, 100)

            # Diseases
            has_db = random.choice([True, False, False, False]) if age > 35 else False
            has_cn = random.choice([True, False, False, False, False, False]) if age > 50 else False
            
            m_diseases = []
            if random.choice([True, False]):
                m_diseases.append(random.choice(diseases_pool))
            if has_db:
                m_diseases.append("Diabetes")
            
            SurveyMember.objects.create(
                survey=survey,
                name=f"Member {i+1}_{m_idx+1}",
                age=age,
                gender=gender,
                occupation=random.choice(occupations) if age > 18 else "Student",
                diseases=", ".join(m_diseases),
                disabilities="None" if random.choice([True, True, False]) else "Visual impairment",
                vaccination_status=vac,
                is_pregnant=is_preg,
                blood_pressure_systolic=bp_sys,
                blood_pressure_diastolic=bp_dia,
                has_diabetes=has_db,
                has_cancer=has_cn,
                mental_health_indicators="Good" if random.choice([True, False]) else "Mild anxiety"
            )

    print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed()
