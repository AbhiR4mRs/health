from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.accounts.permissions import CustomUser
from apps.subcenter.models import Subcenter

@login_required(login_url='/login/')
def center_subcenters_list_view(request):
    user = request.user
    if user.role != CustomUser.Role.CENTER and not user.is_superuser:
        return render(request, 'error.html', {'message': 'Center Administrator permissions required.'})
        
    if not user.center:
        return render(request, 'error.html', {'message': 'Your account is not assigned to any Center. Contact administrator.'})
        
    subcenters = Subcenter.objects.filter(center=user.center).prefetch_related('users', 'health_surveys')
    
    return render(request, 'center/subcenters_list.html', {
        'subcenters': subcenters,
        'center': user.center
    })
