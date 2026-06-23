from django.db.models import Count, Sum
from apps.center.models import Center
from apps.subcenter.models import Subcenter
from apps.surveys.models import HealthSurvey, SurveyMember
from apps.accounts.models import CustomUser

class AnalyticsService:
    @staticmethod
    def get_hq_metrics():
        total_centers = Center.objects.count()
        total_subcenters = Subcenter.objects.count()
        total_surveys = HealthSurvey.objects.count()
        
        # Population Covered is the count of SurveyMember records
        total_population = SurveyMember.objects.count()
        
        # Disease Distribution
        disease_counts = {}
        members_with_diseases = SurveyMember.objects.exclude(diseases__isnull=True).exclude(diseases__exact='')
        for m in members_with_diseases:
            for d in m.get_diseases_list():
                disease_counts[d] = disease_counts.get(d, 0) + 1
        
        # Sort diseases by count descending
        sorted_diseases = sorted(disease_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        disease_labels = [x[0].capitalize() for x in sorted_diseases]
        disease_values = [x[1] for x in sorted_diseases]

        # Chronic conditions
        diabetes_count = SurveyMember.objects.filter(has_diabetes=True).count()
        cancer_count = SurveyMember.objects.filter(has_cancer=True).count()
        pregnant_count = SurveyMember.objects.filter(is_pregnant=True).count()
        
        disease_labels += ["Diabetes", "Cancer", "Pregnancy Cases"]
        disease_values += [diabetes_count, cancer_count, pregnant_count]
        
        # Monthly Trends (last 6 months)
        trends = HealthSurvey.objects.extra(
            select={'month': "strftime('%Y-%m', submitted_at)"}
        ).values('month').annotate(count=Count('id')).order_by('month')[:6]
        
        trend_labels = [t['month'] for t in trends]
        trend_values = [t['count'] for t in trends]

        return {
            'total_centers': total_centers,
            'total_subcenters': total_subcenters,
            'total_surveys': total_surveys,
            'total_population': total_population,
            'disease_labels': disease_labels,
            'disease_values': disease_values,
            'trend_labels': trend_labels,
            'trend_values': trend_values,
        }

    @staticmethod
    def get_center_metrics(center):
        subcenters = Subcenter.objects.filter(center=center)
        total_subcenters = subcenters.count()
        
        surveys = HealthSurvey.objects.filter(center=center)
        total_surveys = surveys.count()
        
        total_population = SurveyMember.objects.filter(survey__center=center).count()
        
        # Disease distribution for this Center
        disease_counts = {}
        members_with_diseases = SurveyMember.objects.filter(survey__center=center).exclude(diseases__isnull=True).exclude(diseases__exact='')
        for m in members_with_diseases:
            for d in m.get_diseases_list():
                disease_counts[d] = disease_counts.get(d, 0) + 1
        
        sorted_diseases = sorted(disease_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        disease_labels = [x[0].capitalize() for x in sorted_diseases]
        disease_values = [x[1] for x in sorted_diseases]
        
        # Compare Subcenters: surveys completed by each Subcenter
        subcenter_stats = Subcenter.objects.filter(center=center).annotate(
            survey_count=Count('health_surveys')
        ).values('name', 'survey_count')
        
        subcenter_names = [s['name'] for s in subcenter_stats]
        subcenter_surveys = [s['survey_count'] for s in subcenter_stats]

        return {
            'total_subcenters': total_subcenters,
            'total_surveys': total_surveys,
            'total_population': total_population,
            'disease_labels': disease_labels,
            'disease_values': disease_values,
            'subcenter_names': subcenter_names,
            'subcenter_surveys': subcenter_surveys
        }

    @staticmethod
    def get_subcenter_metrics(subcenter):
        surveys = HealthSurvey.objects.filter(subcenter=subcenter)
        total_surveys = surveys.count()
        
        # Surveys by Conductor
        conductor_stats = CustomUser.objects.filter(subcenter=subcenter, role=CustomUser.Role.CONDUCTOR).annotate(
            survey_count=Count('health_surveys')
        ).values('username', 'survey_count')
        
        conductor_names = [c['username'] for c in conductor_stats]
        conductor_surveys = [c['survey_count'] for c in conductor_stats]
        
        # Recent activity (last 5)
        recent_activities = surveys.select_related('submitted_by').order_by('-submitted_at')[:5]
        
        # Ward-wise Analysis
        ward_stats = HealthSurvey.objects.filter(subcenter=subcenter).values('ward').annotate(
            survey_count=Count('id')
        ).order_by('-survey_count')
        
        ward_names = [w['ward'] for w in ward_stats]
        ward_surveys = [w['survey_count'] for w in ward_stats]
        
        # Diseases statistics for this Subcenter
        disease_counts = {}
        members_with_diseases = SurveyMember.objects.filter(survey__subcenter=subcenter).exclude(diseases__isnull=True).exclude(diseases__exact='')
        for m in members_with_diseases:
            for d in m.get_diseases_list():
                disease_counts[d] = disease_counts.get(d, 0) + 1
        
        sorted_diseases = sorted(disease_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        disease_labels = [x[0].capitalize() for x in sorted_diseases]
        disease_values = [x[1] for x in sorted_diseases]

        return {
            'total_surveys': total_surveys,
            'conductor_names': conductor_names,
            'conductor_surveys': conductor_surveys,
            'recent_activities': recent_activities,
            'ward_names': ward_names,
            'ward_surveys': ward_surveys,
            'disease_labels': disease_labels,
            'disease_values': disease_values
        }
