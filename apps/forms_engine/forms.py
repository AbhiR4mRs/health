from django import forms
from apps.forms_engine.models import FormDefinition, FormField, FormResponse, Answer

class DynamicForm(forms.Form):
    def __init__(self, form_definition, *args, **kwargs):
        self.form_definition = form_definition
        super().__init__(*args, **kwargs)
        
        fields = form_definition.fields.all().order_by('order')
        
        for field in fields:
            field_name = f"field_{field.id}"
            required = field.required
            label = field.label
            placeholder = field.placeholder or ""
            
            if field.field_type == FormField.FieldType.TEXT:
                self.fields[field_name] = forms.CharField(
                    label=label,
                    required=required,
                    widget=forms.TextInput(attrs={'placeholder': placeholder, 'class': 'form-control'})
                )
            elif field.field_type == FormField.FieldType.TEXTAREA:
                self.fields[field_name] = forms.CharField(
                    label=label,
                    required=required,
                    widget=forms.Textarea(attrs={'placeholder': placeholder, 'rows': 4, 'class': 'form-control'})
                )
            elif field.field_type == FormField.FieldType.NUMBER:
                self.fields[field_name] = forms.FloatField(
                    label=label,
                    required=required,
                    widget=forms.NumberInput(attrs={'placeholder': placeholder, 'class': 'form-control'})
                )
            elif field.field_type == FormField.FieldType.DATE:
                self.fields[field_name] = forms.DateField(
                    label=label,
                    required=required,
                    widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
                )
            elif field.field_type == FormField.FieldType.EMAIL:
                self.fields[field_name] = forms.EmailField(
                    label=label,
                    required=required,
                    widget=forms.EmailInput(attrs={'placeholder': placeholder, 'class': 'form-control'})
                )
            elif field.field_type == FormField.FieldType.PHONE:
                self.fields[field_name] = forms.CharField(
                    label=label,
                    required=required,
                    widget=forms.TextInput(attrs={'type': 'tel', 'placeholder': placeholder, 'class': 'form-control'})
                )
            elif field.field_type == FormField.FieldType.SELECT:
                choices = [(opt, opt) for opt in field.get_options_list()]
                self.fields[field_name] = forms.ChoiceField(
                    label=label,
                    required=required,
                    choices=[('', 'Select Option')] + choices,
                    widget=forms.Select(attrs={'class': 'form-select'})
                )
            elif field.field_type == FormField.FieldType.RADIO:
                choices = [(opt, opt) for opt in field.get_options_list()]
                self.fields[field_name] = forms.ChoiceField(
                    label=label,
                    required=required,
                    choices=choices,
                    widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
                )
            elif field.field_type == FormField.FieldType.CHECKBOX:
                self.fields[field_name] = forms.BooleanField(
                    label=label,
                    required=required,
                    widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
                )
            elif field.field_type == FormField.FieldType.MULTISELECT:
                choices = [(opt, opt) for opt in field.get_options_list()]
                self.fields[field_name] = forms.MultipleChoiceField(
                    label=label,
                    required=required,
                    choices=choices,
                    widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
                )
            elif field.field_type == FormField.FieldType.FILE:
                self.fields[field_name] = forms.FileField(
                    label=label,
                    required=required,
                    widget=forms.FileInput(attrs={'class': 'form-control'})
                )

    def save(self, user, center, subcenter):
        response = FormResponse.objects.create(
            form=self.form_definition,
            submitted_by=user,
            submitted_role=user.role if user.role != 'CONDUCTOR' else user.conductor_role,
            center=center,
            subcenter=subcenter
        )
        
        for field in self.form_definition.fields.all():
            field_name = f"field_{field.id}"
            value = self.cleaned_data.get(field_name)
            
            if isinstance(value, list):
                value_str = ", ".join(value)
            elif value is None:
                value_str = ""
            else:
                value_str = str(value)
                
            if field.field_type == FormField.FieldType.FILE and value and not isinstance(value, str):
                from django.core.files.storage import default_storage
                file_path = default_storage.save(f"dynamic_uploads/{value.name}", value)
                value_str = default_storage.url(file_path)

            Answer.objects.create(
                response=response,
                field=field,
                value=value_str
            )
        return response
