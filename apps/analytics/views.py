from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from apps.analytics.services import AnalyticsService
from apps.accounts.models import CustomUser
from apps.ml_engine.services import MLEngineService

@login_required(login_url='/login/')
def dashboard_view(request):
    user = request.user
    if user.role == CustomUser.Role.HQ or user.is_superuser:
        data = AnalyticsService.get_hq_metrics()
        # Fetch outbreak alerts from ML engine
        outbreaks = MLEngineService.get_outbreak_alerts()
        return render(request, 'analytics/hq_dashboard.html', {
            'metrics': data,
            'outbreaks': outbreaks
        })
        
    elif user.role == CustomUser.Role.CENTER:
        if not user.center:
            return render(request, 'error.html', {'message': 'Your account is not assigned to any Center. Contact administrator.'})
        data = AnalyticsService.get_center_metrics(user.center)
        return render(request, 'analytics/center_dashboard.html', {'metrics': data})
        
    elif user.role in [CustomUser.Role.SUBCENTER, CustomUser.Role.CONDUCTOR]:
        if not user.subcenter:
            return render(request, 'error.html', {'message': 'Your account is not assigned to any Subcenter. Contact administrator.'})
        data = AnalyticsService.get_subcenter_metrics(user.subcenter)
        return render(request, 'analytics/subcenter_dashboard.html', {'metrics': data})
        
    return redirect('/login/')
