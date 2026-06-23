from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.accounts.permissions import CustomUser
from apps.center.models import Center
from apps.subcenter.models import Subcenter
from apps.accounts.models import CustomUser

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
