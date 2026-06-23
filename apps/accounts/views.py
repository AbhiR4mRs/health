from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from apps.accounts.models import AuditLog

def login_view(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                
                # Create Audit Log
                AuditLog.objects.create(
                    user=user,
                    action="Logged in successfully",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return redirect('/dashboard/')
            else:
                return render(request, 'accounts/login.html', {'error': 'Invalid username or password'})
        else:
            return render(request, 'accounts/login.html', {'error': 'Invalid username or password'})
            
    return render(request, 'accounts/login.html')

def logout_view(request):
    user = request.user
    if user.is_authenticated:
        AuditLog.objects.create(
            user=user,
            action="Logged out",
            ip_address=request.META.get('REMOTE_ADDR')
        )
    logout(request)
    return redirect('/login/')
