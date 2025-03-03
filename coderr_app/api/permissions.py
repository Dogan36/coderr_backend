from rest_framework.permissions import BasePermission
from coderr_app.models import Profil

class IsStaffForDeleteOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method == "DELETE":
            return request.user.is_staff  # DELETE nur für staff erlaubt
        return True  # Andere Methoden sind erlaubt

class IsCustomerForCreateOnly(BasePermission):
    def has_permission(self, request, view):
        # Prüfe, ob die Anfrage eine Bestellung erstellen will
        if request.method == "POST":
            try:
                profil = Profil.objects.get(user=request.user)
                return profil.profile_type == "customer" 
            except Profil.DoesNotExist:
                return False 
        return True
    
class IsBusinessForCreateOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method == "POST":
            try:
                profil = Profil.objects.get(user=request.user)
                return profil.profile_type == "business" 
            except Profil.DoesNotExist:
                return False 
        return True