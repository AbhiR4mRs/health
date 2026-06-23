from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.surveys.models import HealthSurvey, SurveyMember
from apps.accounts.permissions import get_scoped_queryset, CustomUser
from apps.accounts.models import AuditLog

@login_required(login_url='/login/')
def survey_list(request):
    # Apply row-level scoping to only show surveys this user is permitted to see
    queryset = get_scoped_queryset(request.user, HealthSurvey).select_related('center', 'subcenter', 'submitted_by')
    return render(request, 'surveys/survey_list.html', {'surveys': queryset})

@login_required(login_url='/login/')
def survey_detail(request, pk):
    queryset = get_scoped_queryset(request.user, HealthSurvey)
    survey = get_object_or_404(queryset, pk=pk)
    members = survey.members.all()
    return render(request, 'surveys/survey_detail.html', {'survey': survey, 'members': members})

@login_required(login_url='/login/')
def survey_create(request):
    if request.user.role not in [CustomUser.Role.SUBCENTER, CustomUser.Role.CONDUCTOR] and not request.user.is_superuser:
        return render(request, 'error.html', {'message': 'Only Subcenters and Survey Conductors can submit health surveys.'})
        
    if not request.user.subcenter and not request.user.is_superuser:
        return render(request, 'error.html', {'message': 'Your account is not assigned to any Subcenter. Contact administrator.'})

    if request.method == 'POST':
        try:
            house_number = request.POST.get('house_number')
            ward = request.POST.get('ward')
            panchayat = request.POST.get('panchayat')
            address = request.POST.get('address')
            family_head_name = request.POST.get('family_head_name')
            family_members_count = int(request.POST.get('family_members_count', 1))

            # Fallback center/subcenter for admin testing
            center = request.user.subcenter.center if request.user.subcenter else None
            subcenter = request.user.subcenter

            survey = HealthSurvey.objects.create(
                submitted_by=request.user,
                submitted_role=request.user.role if request.user.role != 'CONDUCTOR' else request.user.conductor_role,
                center=center,
                subcenter=subcenter,
                house_number=house_number,
                ward=ward,
                panchayat=panchayat,
                address=address,
                family_head_name=family_head_name,
                family_members_count=family_members_count
            )

            # Iterate through dynamic list of members
            member_index = 0
            while True:
                name_key = f'member_name_{member_index}'
                if name_key not in request.POST:
                    break
                    
                name = request.POST.get(name_key)
                if name:
                    age = int(request.POST.get(f'member_age_{member_index}', 0))
                    gender = request.POST.get(f'member_gender_{member_index}', 'M')
                    occupation = request.POST.get(f'member_occupation_{member_index}', '')
                    diseases = request.POST.get(f'member_diseases_{member_index}', '')
                    disabilities = request.POST.get(f'member_disabilities_{member_index}', '')
                    vaccination = request.POST.get(f'member_vaccination_{member_index}', 'NOT')
                    is_pregnant = request.POST.get(f'member_pregnant_{member_index}') == 'true'
                    bp_sys = request.POST.get(f'member_bp_sys_{member_index}')
                    bp_dia = request.POST.get(f'member_bp_dia_{member_index}')
                    diabetes = request.POST.get(f'member_diabetes_{member_index}') == 'true'
                    cancer = request.POST.get(f'member_cancer_{member_index}') == 'true'
                    mental = request.POST.get(f'member_mental_{member_index}', '')

                    SurveyMember.objects.create(
                        survey=survey,
                        name=name,
                        age=age,
                        gender=gender,
                        occupation=occupation,
                        diseases=diseases,
                        disabilities=disabilities,
                        vaccination_status=vaccination,
                        is_pregnant=is_pregnant,
                        blood_pressure_systolic=int(bp_sys) if bp_sys and bp_sys.isdigit() else None,
                        blood_pressure_diastolic=int(bp_dia) if bp_dia and bp_dia.isdigit() else None,
                        has_diabetes=diabetes,
                        has_cancer=cancer,
                        mental_health_indicators=mental
                    )
                member_index += 1

            # Log dynamic event creation
            AuditLog.objects.create(
                user=request.user,
                action=f"Created health survey for house {house_number} in {panchayat}/{ward}",
                ip_address=request.META.get('REMOTE_ADDR')
            )

            messages.success(request, 'Health survey record submitted successfully!')
            return redirect('/surveys/')
        except Exception as e:
            messages.error(request, f"Error saving survey: {str(e)}")
            
    return render(request, 'surveys/survey_create.html')
