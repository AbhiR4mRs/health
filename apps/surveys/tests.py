from django.test import TestCase
from apps.accounts.models import CustomUser
from apps.center.models import Center
from apps.subcenter.models import Subcenter
from apps.surveys.models import HealthSurvey
from apps.accounts.permissions import get_scoped_queryset
from apps.forms_engine.models import FormDefinition, FormField, FormResponse, Answer
from apps.forms_engine.forms import DynamicForm

class SurveyRBACAndFormsTestCase(TestCase):
    def setUp(self):
        # 1. Create Centers
        self.center1 = Center.objects.create(name="Center 1", code="C1")
        self.center2 = Center.objects.create(name="Center 2", code="C2")

        # 2. Create Subcenters
        self.sc1 = Subcenter.objects.create(center=self.center1, name="Subcenter 1", code="S1")
        self.sc2 = Subcenter.objects.create(center=self.center2, name="Subcenter 2", code="S2")

        # 3. Create Users
        self.hq_user = CustomUser.objects.create_user(
            username="hq_admin", password="password", role=CustomUser.Role.HQ
        )
        self.sc1_user = CustomUser.objects.create_user(
            username="sc1_admin", password="password", role=CustomUser.Role.SUBCENTER, subcenter=self.sc1
        )
        self.sc2_user = CustomUser.objects.create_user(
            username="sc2_admin", password="password", role=CustomUser.Role.SUBCENTER, subcenter=self.sc2
        )

        # 4. Create Surveys
        self.survey1 = HealthSurvey.objects.create(
            submitted_by=self.sc1_user, submitted_role="SUBCENTER",
            center=self.center1, subcenter=self.sc1,
            house_number="H1", ward="W1", panchayat="P1", address="A1",
            family_head_name="Head 1", family_members_count=1
        )
        self.survey2 = HealthSurvey.objects.create(
            submitted_by=self.sc2_user, submitted_role="SUBCENTER",
            center=self.center2, subcenter=self.sc2,
            house_number="H2", ward="W2", panchayat="P2", address="A2",
            family_head_name="Head 2", family_members_count=1
        )

    def test_row_level_scoping(self):
        # HQ User sees all
        hq_qs = get_scoped_queryset(self.hq_user, HealthSurvey)
        self.assertEqual(hq_qs.count(), 2)

        # Subcenter 1 user sees only Subcenter 1 surveys
        sc1_qs = get_scoped_queryset(self.sc1_user, HealthSurvey)
        self.assertEqual(sc1_qs.count(), 1)
        self.assertEqual(sc1_qs.first(), self.survey1)

        # Subcenter 2 user sees only Subcenter 2 surveys
        sc2_qs = get_scoped_queryset(self.sc2_user, HealthSurvey)
        self.assertEqual(sc2_qs.count(), 1)
        self.assertEqual(sc2_qs.first(), self.survey2)

    def test_dynamic_form_generation_and_saving(self):
        # Create form definition
        form_def = FormDefinition.objects.create(
            name="Test Form", identifier="test-form", created_by=self.hq_user
        )
        field_text = FormField.objects.create(
            form=form_def, label="Feedback", field_type=FormField.FieldType.TEXT, required=True, order=1
        )
        field_select = FormField.objects.create(
            form=form_def, label="Rating", field_type=FormField.FieldType.SELECT, required=True, options="Good, Bad", order=2
        )

        # Initialize Form instance with dummy input values
        post_data = {
            f"field_{field_text.id}": "This is great!",
            f"field_{field_select.id}": "Good"
        }
        form = DynamicForm(form_def, data=post_data)
        self.assertTrue(form.is_valid())

        # Save response
        response = form.save(user=self.sc1_user, center=self.center1, subcenter=self.sc1)
        self.assertEqual(FormResponse.objects.count(), 1)
        self.assertEqual(Answer.objects.count(), 2)

        # Verify values saved matches input
        ans_text = Answer.objects.get(response=response, field=field_text)
        self.assertEqual(ans_text.value, "This is great!")

        ans_select = Answer.objects.get(response=response, field=field_select)
        self.assertEqual(ans_select.value, "Good")

    def test_form_management_restrictions(self):
        # Create Conductor user
        conductor = CustomUser.objects.create_user(
            username="cond_asha", password="password", role=CustomUser.Role.CONDUCTOR, subcenter=self.sc1
        )
        
        # Test 1: Conductor is blocked from form creation view
        self.client.force_login(conductor)
        response = self.client.get('/forms/create/')
        # Should render error.html page or return access denied (we return error.html with custom message)
        self.assertContains(response, "restricted to Subcenter Administrators", status_code=200)

        # Test 2: Subcenter admin can access form creation view
        self.client.force_login(self.sc1_user)
        response = self.client.get('/forms/create/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'forms_engine/form_create.html')

    def test_form_scoping_reports(self):
        # Create a dynamic form response for Subcenter 1 and Subcenter 2
        form_def = FormDefinition.objects.create(
            name="Report Test Form", identifier="rep-test-form", created_by=self.hq_user
        )
        
        fr1 = FormResponse.objects.create(
            form=form_def, submitted_by=self.sc1_user, submitted_role="SUBCENTER",
            center=self.center1, subcenter=self.sc1
        )
        fr2 = FormResponse.objects.create(
            form=form_def, submitted_by=self.sc2_user, submitted_role="SUBCENTER",
            center=self.center2, subcenter=self.sc2
        )

        # Check scoping querysets for FormResponse
        sc1_responses = get_scoped_queryset(self.sc1_user, FormResponse)
        self.assertEqual(sc1_responses.count(), 1)
        self.assertEqual(sc1_responses.first(), fr1)

        sc2_responses = get_scoped_queryset(self.sc2_user, FormResponse)
        self.assertEqual(sc2_responses.count(), 1)
        self.assertEqual(sc2_responses.first(), fr2)
