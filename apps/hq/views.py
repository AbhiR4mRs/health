from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from apps.accounts.permissions import CustomUser
from apps.center.models import Center
from apps.subcenter.models import Subcenter
from apps.accounts.models import CustomUser
from apps.surveys.models import HealthSurvey, SurveyMember

@login_required(login_url='/login/')
def hq_management_view(request):
    if request.user.role != CustomUser.Role.HQ and not request.user.is_superuser:
        return render(request, 'error.html', {'message': 'HQ access permissions required.'})
        
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Add Center
        if action == 'add_center':
            name = request.POST.get('name')
            code = request.POST.get('code')
            address = request.POST.get('address')
            try:
                Center.objects.create(name=name, code=code, address=address)
                messages.success(request, f"Center '{name}' added successfully!")
            except Exception as e:
                messages.error(request, f"Error adding Center: {str(e)}")
                
        # Add Subcenter
        elif action == 'add_subcenter':
            center_id = request.POST.get('center_id')
            name = request.POST.get('name')
            code = request.POST.get('code')
            address = request.POST.get('address')
            try:
                center = Center.objects.get(id=center_id)
                Subcenter.objects.create(center=center, name=name, code=code, address=address)
                messages.success(request, f"Subcenter '{name}' added successfully under '{center.name}'!")
            except Exception as e:
                messages.error(request, f"Error adding Subcenter: {str(e)}")
                
        return redirect('/management/')

    centers = Center.objects.all()
    subcenters = Subcenter.objects.all().select_related('center')
    users = CustomUser.objects.all().select_related('center', 'subcenter')

    return render(request, 'hq/management.html', {
        'centers': centers,
        'subcenters': subcenters,
        'users': users
    })

@login_required(login_url='/login/')
def center_detail_view(request, pk):
    user = request.user
    if user.role != CustomUser.Role.HQ and not user.is_superuser:
        return render(request, 'error.html', {'message': 'HQ access permissions required.'})
        
    center = get_object_or_404(Center, pk=pk)
    subcenters = Subcenter.objects.filter(center=center).annotate(
        survey_count=Count('health_surveys')
    )
    users = CustomUser.objects.filter(center=center) | CustomUser.objects.filter(subcenter__center=center)
    users = users.distinct().select_related('subcenter')
    
    total_surveys = HealthSurvey.objects.filter(center=center).count()
    total_population = SurveyMember.objects.filter(survey__center=center).count()
    
    return render(request, 'hq/center_detail.html', {
        'center': center,
        'subcenters': subcenters,
        'users': users,
        'total_surveys': total_surveys,
        'total_population': total_population
    })

@login_required(login_url='/login/')
def subcenter_detail_view(request, pk):
    user = request.user
    subcenter = get_object_or_404(Subcenter.objects.select_related('center'), pk=pk)
    
    # Restrict Center Admin to subcenters belonging to their own Center
    if user.role == CustomUser.Role.CENTER:
        if subcenter.center != user.center:
            return render(request, 'error.html', {'message': 'You can only view details of subcenters belonging to your own Center.'})
    # Restrict Subcenter/Conductor to their own Subcenter
    elif user.role in [CustomUser.Role.SUBCENTER, CustomUser.Role.CONDUCTOR]:
        if subcenter != user.subcenter:
            return render(request, 'error.html', {'message': 'You can only view details of your own Subcenter.'})
    # Restrict HQ/Superuser to see all
    elif user.role != CustomUser.Role.HQ and not user.is_superuser:
        return render(request, 'error.html', {'message': 'Access permissions required.'})
        
    conductors = CustomUser.objects.filter(subcenter=subcenter).annotate(
        survey_count=Count('health_surveys')
    )
    
    total_surveys = HealthSurvey.objects.filter(subcenter=subcenter).count()
    total_population = SurveyMember.objects.filter(survey__subcenter=subcenter).count()
    recent_surveys = HealthSurvey.objects.filter(subcenter=subcenter).select_related('submitted_by').order_by('-submitted_at')[:10]
    
    return render(request, 'hq/subcenter_detail.html', {
        'subcenter': subcenter,
        'conductors': conductors,
        'total_surveys': total_surveys,
        'total_population': total_population,
        'recent_surveys': recent_surveys
    })
