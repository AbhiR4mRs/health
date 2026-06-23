from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from apps.surveys.models import HealthSurvey, SurveyMember
from apps.forms_engine.models import FormDefinition, FormResponse, Answer
from apps.center.models import Center
from apps.subcenter.models import Subcenter
from apps.accounts.models import CustomUser
from apps.accounts.permissions import get_scoped_queryset
from apps.reports.services import filter_health_surveys, export_to_csv, export_to_excel, export_to_pdf
import pandas as pd
from io import BytesIO

@login_required(login_url='/login/')
def reports_list_view(request):
    """
    Form List: Displays all reports (Primary Health Survey + active dynamic custom forms).
    """
    # 1. Predefined Core Health Survey
    reports = [{
        'id': 0,
        'type': 'core',
        'name': 'Primary Health Survey',
        'description': 'Main family health, household vaccination, and chronic disease diagnostic survey.'
    }]
    
    # 2. Dynamic Custom Forms (filter based on active status)
    user = request.user
    if user.role == CustomUser.Role.HQ or user.is_superuser:
        dyn_forms = FormDefinition.objects.filter(active=True)
    elif user.role == CustomUser.Role.CENTER:
        # Templates created by subcenters in this center
        dyn_forms = FormDefinition.objects.filter(active=True).filter(
            created_by__subcenter__center=user.center
        ) | FormDefinition.objects.filter(active=True, created_by__role=CustomUser.Role.HQ)
    else: # Subcenter or Conductor
        if user.subcenter:
            dyn_forms = FormDefinition.objects.filter(active=True).filter(
                created_by__subcenter=user.subcenter
            ) | FormDefinition.objects.filter(active=True, created_by__role=CustomUser.Role.HQ)
        else:
            dyn_forms = FormDefinition.objects.none()
            
    dyn_forms = dyn_forms.distinct()
    
    for df in dyn_forms:
        reports.append({
            'id': df.id,
            'type': 'dynamic',
            'name': df.name,
            'description': df.description or 'Custom Subcenter dynamic survey.'
        })
        
    return render(request, 'reports/reports_list.html', {'reports': reports})

@login_required(login_url='/login/')
def submissions_list_view(request, form_type, form_id):
    """
    Submission List: Displays historical submissions for a selected report, scoped by user hierarchy.
    """
    user = request.user
    
    # Gather filtering params
    date_start = request.GET.get('date_start')
    date_end = request.GET.get('date_end')
    center_id = request.GET.get('center_id')
    subcenter_id = request.GET.get('subcenter_id')
    conductor_id = request.GET.get('conductor_id')
    export_format = request.GET.get('export')

    # Apply row-level scoping constraints on filters if user is Center, Subcenter or Conductor
    if user.role == CustomUser.Role.CENTER:
        center_id = user.center.id
    elif user.role in [CustomUser.Role.SUBCENTER, CustomUser.Role.CONDUCTOR]:
        if user.subcenter:
            center_id = user.subcenter.center.id
            subcenter_id = user.subcenter.id
        else:
            center_id = None
            subcenter_id = None

    filters = {
        'date_start': date_start,
        'date_end': date_end,
        'center_id': center_id,
        'subcenter_id': subcenter_id,
        'conductor_id': conductor_id
    }

    # Handle Core Health Survey submissions
    if form_type == 'core':
        queryset = get_scoped_queryset(user, HealthSurvey).select_related('center', 'subcenter', 'submitted_by')
        
        # Apply filters
        if date_start:
            queryset = queryset.filter(submitted_at__date__gte=date_start)
        if date_end:
            queryset = queryset.filter(submitted_at__date__lte=date_end)
        if center_id:
            queryset = queryset.filter(center_id=center_id)
        if subcenter_id:
            queryset = queryset.filter(subcenter_id=subcenter_id)
        if conductor_id:
            queryset = queryset.filter(submitted_by_id=conductor_id)

        # Handle exports for Core
        if export_format:
            member_qs = SurveyMember.objects.filter(survey__in=queryset).select_related(
                'survey', 'survey__center', 'survey__subcenter', 'survey__submitted_by'
            )
            if export_format == 'csv':
                csv_data = export_to_csv(member_qs)
                response = HttpResponse(csv_data, content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="health_survey_report.csv"'
                return response
            elif export_format == 'excel':
                excel_data = export_to_excel(member_qs)
                response = HttpResponse(excel_data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename="health_survey_report.xlsx"'
                return response
            elif export_format == 'pdf':
                pdf_data = export_to_pdf(member_qs)
                response = HttpResponse(pdf_data, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="health_survey_report.pdf"'
                return response

        records = [{
            'id': hs.id,
            'conductor': hs.submitted_by.username,
            'role': hs.submitted_role,
            'date': hs.submitted_at,
            'summary': f"House {hs.house_number}, {hs.panchayat} (Members: {hs.family_members_count})"
        } for hs in queryset]
        form_name = "Primary Health Survey"

    # Handle Dynamic Form submissions
    else:
        form_def = get_object_or_404(FormDefinition, id=form_id)
        queryset = get_scoped_queryset(user, FormResponse).filter(form=form_def).select_related('center', 'subcenter', 'submitted_by')
        
        # Apply filters
        if date_start:
            queryset = queryset.filter(submitted_at__date__gte=date_start)
        if date_end:
            queryset = queryset.filter(submitted_at__date__lte=date_end)
        if center_id:
            queryset = queryset.filter(center_id=center_id)
        if subcenter_id:
            queryset = queryset.filter(subcenter_id=subcenter_id)
        if conductor_id:
            queryset = queryset.filter(submitted_by_id=conductor_id)

        # Handle exports for Dynamic Form
        if export_format:
            fields = form_def.fields.all().order_by('order')
            data = []
            for res in queryset:
                row = {
                    'Submission ID': res.id,
                    'Conductor': res.submitted_by.username,
                    'Role': res.submitted_role,
                    'Center': res.center.name,
                    'Subcenter': res.subcenter.name,
                    'Date': res.submitted_at.strftime('%Y-%m-%d %H:%M')
                }
                # Map field values
                answers_dict = {ans.field.label: ans.value for ans in res.answers.all()}
                for f in fields:
                    row[f.label] = answers_dict.get(f.label, '')
                data.append(row)
                
            df = pd.DataFrame(data)
            
            if export_format == 'csv':
                response = HttpResponse(df.to_csv(index=False), content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{form_def.identifier}_report.csv"'
                return response
            elif export_format == 'excel':
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Submissions', index=False)
                output.seek(0)
                response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = f'attachment; filename="{form_def.identifier}_report.xlsx"'
                return response
            elif export_format == 'pdf':
                from reportlab.lib.pagesizes import letter, landscape
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib import colors
                
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
                story = []
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle('RepTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=15, textColor=colors.HexColor('#0f172a'))
                story.append(Paragraph(f"Custom Survey Report: {form_def.name}", title_style))
                story.append(Spacer(1, 10))
                
                headers = ["Conductor", "Role", "Subcenter", "Date"] + [f.label[:15] for f in fields[:4]]
                table_data = [headers]
                for res in queryset[:50]:
                    ans_map = {ans.field.label: ans.value for ans in res.answers.all()}
                    row = [
                        res.submitted_by.username,
                        res.submitted_role,
                        res.subcenter.name,
                        res.submitted_at.strftime('%Y-%m-%d')
                    ]
                    for f in fields[:4]:
                        row.append(ans_map.get(f.label, '')[:20])
                    table_data.append(row)
                    
                if len(table_data) == 1:
                    table_data.append(["No records found", "", "", ""] + [""] * len(fields[:4]))
                    
                t = Table(table_data)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                    ('FONTSIZE', (0,0), (-1,-1), 8),
                ]))
                story.append(t)
                doc.build(story)
                buffer.seek(0)
                response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{form_def.identifier}_report.pdf"'
                return response

        records = [{
            'id': fr.id,
            'conductor': fr.submitted_by.username,
            'role': fr.submitted_role,
            'date': fr.submitted_at,
            'summary': f"Completed by {fr.submitted_by.username} ({fr.submitted_role}) at {fr.subcenter.name}"
        } for fr in queryset]
        form_name = form_def.name

    # Load scoped filter lists based on user role
    if user.role == CustomUser.Role.HQ or user.is_superuser:
        centers = Center.objects.all()
        subcenters = Subcenter.objects.all()
        conductors = CustomUser.objects.filter(role=CustomUser.Role.CONDUCTOR)
    elif user.role == CustomUser.Role.CENTER:
        centers = Center.objects.filter(id=user.center.id)
        subcenters = Subcenter.objects.filter(center=user.center)
        conductors = CustomUser.objects.filter(subcenter__center=user.center, role=CustomUser.Role.CONDUCTOR)
    else: # Subcenter or Conductor
        if user.subcenter:
            centers = Center.objects.filter(id=user.subcenter.center.id)
            subcenters = Subcenter.objects.filter(id=user.subcenter.id)
            conductors = CustomUser.objects.filter(subcenter=user.subcenter, role=CustomUser.Role.CONDUCTOR)
        else:
            centers = Center.objects.none()
            subcenters = Subcenter.objects.none()
            conductors = CustomUser.objects.none()

    return render(request, 'reports/submissions_list.html', {
        'records': records,
        'total_count': len(records),
        'form_name': form_name,
        'form_type': form_type,
        'form_id': form_id,
        'centers': centers,
        'subcenters': subcenters,
        'conductors': conductors,
        'filters': filters
    })

@login_required(login_url='/login/')
def submission_detail_view(request, form_type, submission_id):
    """
    Submission Details: Displays full details of an individual submission.
    """
    user = request.user
    
    if form_type == 'core':
        queryset = get_scoped_queryset(user, HealthSurvey)
        survey = get_object_or_404(queryset, id=submission_id)
        members = survey.members.all()
        return render(request, 'reports/submission_detail.html', {
            'survey': survey,
            'members': members,
            'form_type': form_type,
            'form_name': 'Primary Health Survey'
        })
    else:
        queryset = get_scoped_queryset(user, FormResponse)
        response = get_object_or_404(queryset, id=submission_id)
        answers = response.answers.all().select_related('field')
        return render(request, 'reports/submission_detail.html', {
            'response': response,
            'answers': answers,
            'form_type': form_type,
            'form_name': response.form.name
        })
