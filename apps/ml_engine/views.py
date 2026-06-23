from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.ml_engine.services import MLEngineService

@login_required(login_url='/login/')
def ml_insights_view(request):
    disease_query = request.GET.get('disease', 'Fever')
    
    # 1. Disease trend prediction (Linear Regression)
    trends = MLEngineService.predict_disease_trends(disease_query, weeks_to_forecast=4)
    forecast_weeks = [f"Week {i+1} (Forecast)" for i in range(4)]
    
    # 2. High-Risk population profiling
    high_risk_members = MLEngineService.identify_high_risk_members(limit=15)
    
    # 3. Vaccination Gaps Analysis
    vaccination_gaps = MLEngineService.analyze_vaccination_gaps()
    
    # 4. K-Means Regional clustering
    high_risk_areas = MLEngineService.identify_high_risk_areas_clustering()
    
    return render(request, 'ml_engine/ml_insights.html', {
        'disease_query': disease_query,
        'trends': trends,
        'forecast_weeks': forecast_weeks,
        'high_risk_members': high_risk_members,
        'vaccination_gaps': vaccination_gaps,
        'high_risk_areas': high_risk_areas
    })
