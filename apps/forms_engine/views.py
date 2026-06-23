from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.text import slugify
from apps.forms_engine.models import FormDefinition, FormField, FormResponse
from apps.forms_engine.forms import DynamicForm
from apps.accounts.permissions import get_scoped_queryset, CustomUser

@login_required(login_url='/login/')
def forms_list(request):
    user = request.user
    
    # 1. Subcenter Admins can manage forms (view, edit, toggle, delete)
    if user.role == CustomUser.Role.SUBCENTER or user.is_superuser:
        # Fetch forms created by this subcenter/user
        forms = FormDefinition.objects.filter(created_by=user)
        responses = get_scoped_queryset(user, FormResponse).select_related('form', 'center', 'subcenter', 'submitted_by')
        return render(request, 'forms_engine/forms_list.html', {
            'forms': forms,
            'responses': responses,
            'is_manager': True
        })
        
    # 2. Survey Conductors can ONLY view the "Available Forms" list (active templates)
    elif user.role == CustomUser.Role.CONDUCTOR:
        if not user.subcenter:
            return render(request, 'error.html', {'message': 'Your account is not assigned to any Subcenter.'})
            
        # Active forms created by their subcenter admin, or global templates (created by HQ admins)
        forms = FormDefinition.objects.filter(active=True).filter(
            created_by__subcenter=user.subcenter
        ) | FormDefinition.objects.filter(active=True, created_by__role=CustomUser.Role.HQ)
        
        forms = forms.distinct()
        
        # Responses submitted by this specific conductor
        responses = FormResponse.objects.filter(submitted_by=user).select_related('form', 'submitted_by')
        
        return render(request, 'forms_engine/forms_list.html', {
            'forms': forms,
            'responses': responses,
            'is_manager': False
        })
        
    # 3. HQ or Center Admins see all templates
    else:
        forms = FormDefinition.objects.all()
        responses = get_scoped_queryset(user, FormResponse).select_related('form', 'center', 'subcenter', 'submitted_by')
        return render(request, 'forms_engine/forms_list.html', {
            'forms': forms,
            'responses': responses,
            'is_manager': False
        })

@login_required(login_url='/login/')
def form_fill(request, identifier):
    form_def = get_object_or_404(FormDefinition, identifier=identifier, active=True)
    user = request.user
    
    # Block non-conductors/non-subcenters
    if user.role not in [CustomUser.Role.SUBCENTER, CustomUser.Role.CONDUCTOR] and not user.is_superuser:
        return render(request, 'error.html', {'message': 'Only Subcenters and Survey Conductors can submit responses.'})
        
    if not user.subcenter and not user.is_superuser:
        return render(request, 'error.html', {'message': 'Your account is not assigned to any Subcenter.'})

    if request.method == 'POST':
        form = DynamicForm(form_def, data=request.POST, files=request.FILES)
        if form.is_valid():
            center = user.subcenter.center if user.subcenter else None
            subcenter = user.subcenter
            form.save(user=user, center=center, subcenter=subcenter)
            messages.success(request, f"Response to '{form_def.name}' submitted successfully!")
            return redirect('/forms/')
    else:
        form = DynamicForm(form_def)
        
    return render(request, 'forms_engine/form_fill.html', {
        'form_def': form_def,
        'form': form
    })

# --- Subcenter Form Management (CRUD) ---

@login_required(login_url='/login/')
def form_create(request):
    user = request.user
    # Only Subcenter Admin and Superuser can create forms
    if user.role != CustomUser.Role.SUBCENTER and not user.is_superuser:
        return render(request, 'error.html', {'message': 'Form creation is restricted to Subcenter Administrators.'})

    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            description = request.POST.get('description')
            identifier = request.POST.get('identifier')
            
            if not identifier:
                identifier = slugify(name)
                
            form_def = FormDefinition.objects.create(
                name=name,
                identifier=identifier,
                description=description,
                created_by=user,
                active=True
            )
            
            # Save fields from dynamic inputs
            field_idx = 0
            while True:
                label_key = f'field_label_{field_idx}'
                if label_key not in request.POST:
                    break
                    
                label = request.POST.get(label_key)
                if label:
                    field_type = request.POST.get(f'field_type_{field_idx}', 'TEXT')
                    required = request.POST.get(f'field_required_{field_idx}') == 'true'
                    placeholder = request.POST.get(f'field_placeholder_{field_idx}', '')
                    options = request.POST.get(f'field_options_{field_idx}', '')
                    
                    FormField.objects.create(
                        form=form_def,
                        label=label,
                        field_type=field_type,
                        required=required,
                        placeholder=placeholder,
                        options=options,
                        order=field_idx
                    )
                field_idx += 1
                
            messages.success(request, f"Custom form '{name}' created successfully!")
            return redirect('/forms/')
        except Exception as e:
            messages.error(request, f"Error creating form: {str(e)}")
            
    return render(request, 'forms_engine/form_create.html')

@login_required(login_url='/login/')
def form_edit(request, pk):
    user = request.user
    if user.role != CustomUser.Role.SUBCENTER and not user.is_superuser:
        return render(request, 'error.html', {'message': 'Form editing is restricted to Subcenter Administrators.'})
        
    form_def = get_object_or_404(FormDefinition, pk=pk)
    
    # Subcenter admins can only edit their own created forms
    if form_def.created_by != user and not user.is_superuser:
        return render(request, 'error.html', {'message': 'You can only edit forms created by your own Subcenter.'})

    if request.method == 'POST':
        try:
            form_def.name = request.POST.get('name')
            form_def.description = request.POST.get('description')
            form_def.save()
            
            # Recreate fields (simpler & cleaner for dynamic fields editor)
            form_def.fields.all().delete()
            
            field_idx = 0
            while True:
                label_key = f'field_label_{field_idx}'
                if label_key not in request.POST:
                    break
                    
                label = request.POST.get(label_key)
                if label:
                    field_type = request.POST.get(f'field_type_{field_idx}', 'TEXT')
                    required = request.POST.get(f'field_required_{field_idx}') == 'true'
                    placeholder = request.POST.get(f'field_placeholder_{field_idx}', '')
                    options = request.POST.get(f'field_options_{field_idx}', '')
                    
                    FormField.objects.create(
                        form=form_def,
                        label=label,
                        field_type=field_type,
                        required=required,
                        placeholder=placeholder,
                        options=options,
                        order=field_idx
                    )
                field_idx += 1
                
            messages.success(request, f"Form '{form_def.name}' updated successfully!")
            return redirect('/forms/')
        except Exception as e:
            messages.error(request, f"Error updating form: {str(e)}")

    fields = form_def.fields.all().order_by('order')
    return render(request, 'forms_engine/form_edit.html', {
        'form_def': form_def,
        'fields': fields
    })

@login_required(login_url='/login/')
def form_toggle(request, pk):
    user = request.user
    if user.role != CustomUser.Role.SUBCENTER and not user.is_superuser:
        return render(request, 'error.html', {'message': 'Only Subcenter Administrators can toggle form status.'})
        
    form_def = get_object_or_404(FormDefinition, pk=pk)
    if form_def.created_by != user and not user.is_superuser:
        return render(request, 'error.html', {'message': 'You can only toggle status of forms created by your own Subcenter.'})
        
    form_def.active = not form_def.active
    form_def.save()
    status_str = "activated" if form_def.active else "deactivated"
    messages.success(request, f"Form '{form_def.name}' has been {status_str}!")
    return redirect('/forms/')

@login_required(login_url='/login/')
def form_delete(request, pk):
    user = request.user
    if user.role != CustomUser.Role.SUBCENTER and not user.is_superuser:
        return render(request, 'error.html', {'message': 'Only Subcenter Administrators can delete forms.'})
        
    form_def = get_object_or_404(FormDefinition, pk=pk)
    if form_def.created_by != user and not user.is_superuser:
        return render(request, 'error.html', {'message': 'You can only delete forms created by your own Subcenter.'})
        
    name = form_def.name
    form_def.delete()
    messages.success(request, f"Form '{name}' has been deleted successfully.")
    return redirect('/forms/')
