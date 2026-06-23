import pandas as pd
import numpy as np
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.preprocessing import LabelEncoder
from apps.surveys.models import HealthSurvey, SurveyMember

class MLEngineService:
    @staticmethod
    def get_outbreak_alerts(disease_name=None, threshold_z_score=2.0):
        """
        Outbreak Detection:
        Groups weekly counts of disease reports by ward/panchayat.
        Flags weeks that exceed [mean + threshold_z_score * standard_deviation] as anomaly.
        """
        # Fetch all member records with some diseases
        members = SurveyMember.objects.exclude(diseases__isnull=True).exclude(diseases__exact='').select_related('survey')
        
        data = []
        for m in members:
            diseases_list = m.get_diseases_list()
            for d in diseases_list:
                if not disease_name or disease_name.lower() in d:
                    data.append({
                        'ward': m.survey.ward,
                        'panchayat': m.survey.panchayat,
                        'date': m.survey.submitted_at.date(),
                        'week': m.survey.submitted_at.isocalendar()[1],
                        'year': m.survey.submitted_at.year,
                    })
                    
        if not data:
            return []
            
        df = pd.DataFrame(data)
        # Group by location and week/year to get counts
        grouped = df.groupby(['panchayat', 'ward', 'year', 'week']).size().reset_index(name='cases')
        
        # Calculate historical stats (mean and std) per panchayat/ward
        stats = grouped.groupby(['panchayat', 'ward'])['cases'].agg(['mean', 'std']).reset_index()
        stats['std'] = stats['std'].fillna(0) # handle 1 week cases cases
        
        alerts = []
        # Merge stats back to calculate Z-score
        merged = pd.merge(grouped, stats, on=['panchayat', 'ward'])
        for _, row in merged.iterrows():
            mean = row['mean']
            std = row['std']
            cases = row['cases']
            
            z_score = (cases - mean) / std if std > 0 else 0
            if z_score >= threshold_z_score and cases > 2: # Alert if cases are significantly high
                alerts.append({
                    'panchayat': row['panchayat'],
                    'ward': row['ward'],
                    'week': f"Week {int(row['week'])}, {int(row['year'])}",
                    'cases': int(cases),
                    'average': round(mean, 2),
                    'z_score': round(z_score, 2),
                    'severity': 'Critical' if z_score > 3.0 else 'Warning'
                })
        return alerts

    @staticmethod
    def predict_disease_trends(disease_name, weeks_to_forecast=4):
        """
        Disease Trend Prediction:
        Predicts disease counts for the next N weeks using simple Linear Regression.
        """
        now = timezone.now()
        start_date = now - timedelta(weeks=24) # look at last 6 months
        
        members = SurveyMember.objects.filter(
            survey__submitted_at__gte=start_date
        ).exclude(diseases__isnull=True).exclude(diseases__exact='').select_related('survey')
        
        data = []
        for m in members:
            diseases_list = m.get_diseases_list()
            for d in diseases_list:
                if disease_name.lower() in d:
                    data.append({
                        'date': m.survey.submitted_at.date(),
                    })
                    
        if len(data) < 5:
            # Not enough data to model, return flat fallback forecasts
            return [0] * weeks_to_forecast
            
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        
        # Resample to weekly counts
        df_weekly = df.resample('W', on='date').size().reset_index(name='cases')
        df_weekly['week_index'] = np.arange(len(df_weekly))
        
        # Fit regression model
        X = df_weekly[['week_index']].values
        y = df_weekly['cases'].values
        
        model = LinearRegression()
        model.fit(X, y)
        
        # Forecast future weeks
        future_indices = np.arange(len(df_weekly), len(df_weekly) + weeks_to_forecast).reshape(-1, 1)
        predictions = model.predict(future_indices)
        predictions = np.clip(predictions, 0, None) # Cases cannot be negative
        
        return [int(round(p)) for p in predictions]

    @staticmethod
    def identify_high_risk_members(limit=100):
        """
        Population Risk Analysis:
        Calculates vulnerability health score dynamically for every member.
        """
        members = SurveyMember.objects.all().select_related('survey', 'survey__subcenter', 'survey__center')
        
        high_risk_list = []
        for m in members:
            score = 0
            factors = []
            
            # Age criteria
            if m.age >= 60:
                score += 3
                factors.append("Elderly (Age >= 60)")
            elif m.age <= 5:
                score += 1
                factors.append("Infant (Age <= 5)")
                
            # Chronic illnesses
            if m.has_diabetes:
                score += 3
                factors.append("Diabetic")
            if m.has_cancer:
                score += 4
                factors.append("Cancer Patient")
                
            # Blood pressure indicators
            if m.blood_pressure_systolic and m.blood_pressure_systolic > 140:
                score += 2
                factors.append(f"Systolic Hypertension ({m.blood_pressure_systolic})")
            if m.blood_pressure_diastolic and m.blood_pressure_diastolic > 90:
                score += 2
                factors.append(f"Diastolic Hypertension ({m.blood_pressure_diastolic})")
                
            # Pregnancy risk multiplier
            if m.is_pregnant:
                score += 2
                factors.append("Pregnancy")
                if m.has_diabetes or (m.blood_pressure_systolic and m.blood_pressure_systolic > 130):
                    score += 4
                    factors.append("High-Risk Pregnancy Factors")
                    
            if score >= 3:
                high_risk_list.append({
                    'id': m.id,
                    'name': m.name,
                    'age': m.age,
                    'gender': m.get_gender_display(),
                    'center': m.survey.center.name,
                    'subcenter': m.survey.subcenter.name,
                    'risk_score': score,
                    'factors': ", ".join(factors),
                    'risk_level': 'High' if score >= 7 else 'Medium'
                })
                
        # Sort by risk score descending
        high_risk_list.sort(key=lambda x: x['risk_score'], reverse=True)
        return high_risk_list[:limit]

    @staticmethod
    def analyze_vaccination_gaps():
        """
        Vaccination Gap Analysis:
        Aggregates vaccine data by subcenter, checking the percentage of unvaccinated people.
        """
        stats = SurveyMember.objects.values(
            'survey__subcenter__name', 'survey__subcenter__center__name'
        ).annotate(
            total_members=Count('id'),
            unvaccinated=Count('id', filter=Q(vaccination_status=SurveyMember.VaccinationStatus.NOT)),
            partially_vaccinated=Count('id', filter=Q(vaccination_status=SurveyMember.VaccinationStatus.PARTIALLY)),
            fully_vaccinated=Count('id', filter=Q(vaccination_status=SurveyMember.VaccinationStatus.FULLY))
        )
        
        gaps = []
        for s in stats:
            total = s['total_members']
            unvaccinated = s['unvaccinated']
            gap_percentage = (unvaccinated / total * 100) if total > 0 else 0
            
            gaps.append({
                'subcenter': s['survey__subcenter__name'],
                'center': s['survey__subcenter__center__name'],
                'total_population': total,
                'unvaccinated_count': unvaccinated,
                'gap_percentage': round(gap_percentage, 1),
                'risk_alert': gap_percentage > 35.0
            })
            
        gaps.sort(key=lambda x: x['gap_percentage'], reverse=True)
        return gaps

    @staticmethod
    def identify_high_risk_areas_clustering():
        """
        High-Risk Area Identification (Clustering):
        Uses K-Means clustering on aggregated Ward-wise parameters:
        - Avg Age
        - Diabetes Rate
        - Hypertension Rate
        - Unvaccinated Rate
        Groups wards into 3 Risk Clusters (High, Medium, Low).
        """
        members = SurveyMember.objects.all().select_related('survey')
        if members.count() < 10:
            return []
            
        data = []
        for m in members:
            data.append({
                'ward': m.survey.ward,
                'panchayat': m.survey.panchayat,
                'age': m.age,
                'diabetes': 1 if m.has_diabetes else 0,
                'hypertension': 1 if (m.blood_pressure_systolic and m.blood_pressure_systolic > 140) else 0,
                'unvaccinated': 1 if m.vaccination_status == SurveyMember.VaccinationStatus.NOT else 0
            })
            
        df = pd.DataFrame(data)
        # Aggregate by Panchayat & Ward
        ward_stats = df.groupby(['panchayat', 'ward']).agg({
            'age': 'mean',
            'diabetes': 'mean',
            'hypertension': 'mean',
            'unvaccinated': 'mean'
        }).reset_index()
        
        if len(ward_stats) < 3:
            # Not enough regions for 3 clusters, assign mock scores
            results = []
            for _, row in ward_stats.iterrows():
                results.append({
                    'panchayat': row['panchayat'],
                    'ward': row['ward'],
                    'risk_score': round((row['diabetes'] + row['hypertension'] + row['unvaccinated']) * 33.3, 1),
                    'cluster': 'Medium Risk'
                })
            return results
            
        # Fit K-Means
        features = ['age', 'diabetes', 'hypertension', 'unvaccinated']
        kmeans = KMeans(n_clusters=3, random_state=42, n_init='auto')
        ward_stats['cluster_id'] = kmeans.fit_predict(ward_stats[features])
        
        # Determine the high/medium/low based on the feature centers
        centers = kmeans.cluster_centers_
        # Risk proxy: sum of diabetes, hypertension, unvaccinated rates
        risk_proxy = centers[:, 1] + centers[:, 2] + centers[:, 3]
        sorted_indices = np.argsort(risk_proxy) # from lowest risk to highest risk
        
        cluster_mapping = {
            sorted_indices[0]: 'Low Risk',
            sorted_indices[1]: 'Medium Risk',
            sorted_indices[2]: 'High Risk'
        }
        
        results = []
        for _, row in ward_stats.iterrows():
            cluster_name = cluster_mapping[row['cluster_id']]
            # Calculate a risk index out of 100 for display
            risk_val = (row['diabetes'] + row['hypertension'] + row['unvaccinated']) * 33.3
            results.append({
                'panchayat': row['panchayat'],
                'ward': row['ward'],
                'risk_score': round(risk_val, 1),
                'cluster': cluster_name
            })
            
        results.sort(key=lambda x: x['risk_score'], reverse=True)
        return results
