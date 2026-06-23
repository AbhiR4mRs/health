from rest_framework import permissions
from django.contrib.auth.mixins import UserPassesTestMixin
from apps.accounts.models import CustomUser

# --- Django REST Framework (API) Permissions ---

class IsHQUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == CustomUser.Role.HQ

class IsCenterUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == CustomUser.Role.CENTER

class IsSubcenterUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == CustomUser.Role.SUBCENTER

class IsConductorUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == CustomUser.Role.CONDUCTOR


# --- Django View (HTML) Mixins ---

class HQRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == CustomUser.Role.HQ

class CenterRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role in [CustomUser.Role.HQ, CustomUser.Role.CENTER]

class SubcenterRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role in [CustomUser.Role.HQ, CustomUser.Role.CENTER, CustomUser.Role.SUBCENTER]


# --- Row-Level Scoping Helper Functions ---

def get_scoped_queryset(user, model_class, center_field='center', subcenter_field='subcenter', conductor_field='submitted_by'):
    """
    Applies row-level hierarchical scoping to a model queryset based on the user's role.
    """
    queryset = model_class.objects.all()
    
    if user.is_superuser or user.role == CustomUser.Role.HQ:
        return queryset
        
    elif user.role == CustomUser.Role.CENTER:
        if not user.center:
            return model_class.objects.none()
        filter_kwargs = {center_field: user.center}
        return queryset.filter(**filter_kwargs)
        
    elif user.role == CustomUser.Role.SUBCENTER:
        if not user.subcenter:
            return model_class.objects.none()
        filter_kwargs = {subcenter_field: user.subcenter}
        return queryset.filter(**filter_kwargs)
        
    elif user.role == CustomUser.Role.CONDUCTOR:
        if not user.subcenter:
            return model_class.objects.none()
        # Conductors belong to a subcenter, can view all reports assigned to their subcenter or created by them
        filter_kwargs = {subcenter_field: user.subcenter}
        return queryset.filter(**filter_kwargs)
        
    return model_class.objects.none()
