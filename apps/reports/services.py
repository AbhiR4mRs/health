import pandas as pd
from io import BytesIO
from django.db.models import Q
from apps.surveys.models import HealthSurvey, SurveyMember
from apps.forms_engine.models import FormResponse, Answer

from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def filter_health_surveys(filters):
    """
    Filters the core health survey database records using specified query filters.
    """
    queryset = SurveyMember.objects.all().select_related(
        'survey', 'survey__center', 'survey__subcenter', 'survey__submitted_by'
    )
    
    if filters.get('date_start'):
        queryset = queryset.filter(survey__submitted_at__date__gte=filters['date_start'])
    if filters.get('date_end'):
        queryset = queryset.filter(survey__submitted_at__date__lte=filters['date_end'])
    if filters.get('center_id'):
        queryset = queryset.filter(survey__center_id=filters['center_id'])
    if filters.get('subcenter_id'):
        queryset = queryset.filter(survey__subcenter_id=filters['subcenter_id'])
    if filters.get('conductor_id'):
        queryset = queryset.filter(survey__submitted_by_id=filters['conductor_id'])
    if filters.get('disease'):
        disease_query = filters['disease'].strip().lower()
        if disease_query == 'diabetes':
            queryset = queryset.filter(has_diabetes=True)
        elif disease_query == 'cancer':
            queryset = queryset.filter(has_cancer=True)
        else:
            queryset = queryset.filter(diseases__icontains=disease_query)
            
    return queryset

def generate_health_survey_dataframe(queryset):
    """
    Converts a filtered SurveyMember queryset into a structured Pandas DataFrame.
    """
    data = []
    for member in queryset:
        data.append({
            'Survey ID': member.survey.id,
            'House Number': member.survey.house_number,
            'Ward': member.survey.ward,
            'Panchayat': member.survey.panchayat,
            'Conductor': member.survey.submitted_by.username,
            'Conductor Role': member.survey.submitted_role,
            'Center': member.survey.center.name,
            'Subcenter': member.survey.subcenter.name,
            'Date': member.survey.submitted_at.strftime('%Y-%m-%d %H:%M'),
            'Member Name': member.name,
            'Age': member.age,
            'Gender': member.get_gender_display(),
            'Occupation': member.occupation or 'N/A',
            'Vaccination Status': member.get_vaccination_status_display(),
            'Is Pregnant': 'Yes' if member.is_pregnant else 'No',
            'Blood Pressure': f"{member.blood_pressure_systolic}/{member.blood_pressure_diastolic}" if member.blood_pressure_systolic else 'N/A',
            'Has Diabetes': 'Yes' if member.has_diabetes else 'No',
            'Has Cancer': 'Yes' if member.has_cancer else 'No',
            'Diseases': member.diseases or 'None',
            'Disabilities': member.disabilities or 'None',
            'Mental Health': member.mental_health_indicators or 'None',
        })
    if not data:
        # Return empty dataframe with headers
        return pd.DataFrame(columns=[
            'Survey ID', 'House Number', 'Ward', 'Panchayat', 'Conductor', 'Conductor Role',
            'Center', 'Subcenter', 'Date', 'Member Name', 'Age', 'Gender', 'Occupation',
            'Vaccination Status', 'Is Pregnant', 'Blood Pressure', 'Has Diabetes', 'Has Cancer',
            'Diseases', 'Disabilities', 'Mental Health'
        ])
    return pd.DataFrame(data)

def export_to_csv(queryset):
    df = generate_health_survey_dataframe(queryset)
    return df.to_csv(index=False)

def export_to_excel(queryset):
    df = generate_health_survey_dataframe(queryset)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Surveys Report', index=False)
    output.seek(0)
    return output.getvalue()

def export_to_pdf(queryset):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=15,
        textColor=colors.HexColor('#0f172a')
    )
    story.append(Paragraph("Health Department Survey Report", title_style))
    story.append(Spacer(1, 10))
    
    # Compile table headers & data
    table_data = [[
        "Name", "Age", "Gender", "Center", "Subcenter", "Diseases", "Diabetes", "Cancer", "Vaccination"
    ]]
    
    # We display up to 100 entries on the PDF for neat layout, recommending CSV/Excel for full datasets
    for m in queryset[:100]:
        table_data.append([
            m.name[:20],
            str(m.age),
            m.get_gender_display(),
            m.survey.center.name[:15],
            m.survey.subcenter.name[:15],
            (m.diseases or "None")[:20],
            "Yes" if m.has_diabetes else "No",
            "Yes" if m.has_cancer else "No",
            m.get_vaccination_status_display()
        ])
        
    if len(table_data) == 1:
        table_data.append(["No records found matching filters", "", "", "", "", "", "", "", ""])

    t = Table(table_data, colWidths=[100, 30, 50, 90, 90, 110, 60, 60, 90])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
