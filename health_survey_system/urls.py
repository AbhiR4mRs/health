"""
URL configuration for health_survey_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

from apps.accounts.views import login_view, logout_view
from apps.analytics.views import dashboard_view
from apps.surveys.views import survey_list, survey_detail, survey_create
from apps.forms_engine.views import forms_list, form_fill, form_create, form_edit, form_toggle, form_delete
from apps.reports.views import reports_list_view, submissions_list_view, submission_detail_view
from apps.ml_engine.views import ml_insights_view
from apps.hq.views import hq_management_view

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Auth
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    
    # Dashboards & Redirection
    path('', lambda r: redirect('/dashboard/')),
    path('dashboard/', dashboard_view, name='dashboard'),
    
    # HQ Management
    path('management/', hq_management_view, name='hq_management'),
    
    # Core Health Surveys
    path('surveys/', survey_list, name='survey_list'),
    path('surveys/create/', survey_create, name='survey_create'),
    path('surveys/<int:pk>/', survey_detail, name='survey_detail'),
    
    # Dynamic Custom Forms
    path('forms/', forms_list, name='forms_list'),
    path('forms/create/', form_create, name='form_create'),
    path('forms/edit/<int:pk>/', form_edit, name='form_edit'),
    path('forms/toggle/<int:pk>/', form_toggle, name='form_toggle'),
    path('forms/delete/<int:pk>/', form_delete, name='form_delete'),
    path('forms/fill/<slug:identifier>/', form_fill, name='form_fill'),
    
    # Reports Flow: Form List -> Submissions List -> Submission Detail
    path('reports/', reports_list_view, name='reports_list'),
    path('reports/<slug:form_type>/<int:form_id>/', submissions_list_view, name='submissions_list'),
    path('reports/<slug:form_type>/submission/<int:submission_id>/', submission_detail_view, name='submission_detail'),
    
    # Machine Learning insights
    path('ml/', ml_insights_view, name='ml_insights'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
