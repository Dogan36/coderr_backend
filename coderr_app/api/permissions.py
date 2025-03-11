from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission
from coderr_app.models import Profil, Orders, Offers, Reviews

class IsAdminOrCustomPermission(BasePermission):
    """Allows access to admins (`is_staff=True`). If not an admin, a custom permission check is required."""

    def has_permission(self, request, view):
        """Grants access if the user is an admin, otherwise delegates to custom permission."""
        if request.user and request.user.is_staff:
            return True
        return self.has_custom_permission(request, view)

    def has_custom_permission(self, request, view):
        """Can be overridden by subclasses to define custom permission logic."""
        return False

    def has_object_permission(self, request, view, obj):
        """Grants object-level access to admins, otherwise checks custom object permission."""
        if request.user and request.user.is_staff:
            return True
        return self.has_custom_object_permission(request, view, obj)

    def has_custom_object_permission(self, request, view, obj):
        """Can be overridden by subclasses to define object-level custom permission logic."""
        return False


class IsBusinessForPatchOnly(IsAdminOrCustomPermission):
    """Allows `PATCH` only for the business user (`business_user`) or admins. Customers cannot modify the status."""

    def has_custom_permission(self, request, view):
        """Grants access to non-PATCH requests. For PATCH, only the business user can modify the order."""
        if request.method != "PATCH":
            return True  # No restrictions for other methods

        try:
            order = Orders.objects.get(pk=view.kwargs.get("pk"))
            return order.business_user == request.user
        except Orders.DoesNotExist:
            return False  # Deny access if the order does not exist

    def has_object_permission(self, request, view, obj):
        """Allows PATCH requests only for the business user. Admins always have access."""
        if request.user.is_staff:
            return True
        return request.method == "PATCH" and obj.business_user == request.user

    
class IsCustomerForCreateOnly(IsAdminOrCustomPermission):
    """Allows `POST` only for customers (`profile_type="customer"`). Other requests have no restrictions."""

    def has_permission(self, request, view):
        """Grants `POST` access only if the user has a customer profile. Other methods are unrestricted."""
        if request.method == "POST":
            try:
                profile = Profil.objects.get(user=request.user)
                return profile.profile_type == "customer"
            except Profil.DoesNotExist:
                return False  # Deny access if the profile does not exist
        return True

    def has_object_permission(self, request, view, obj):
        """Allows `GET` requests for all users. Delegates other methods to `has_permission()`."""
        if request.method == "GET":
            return True
        return self.has_permission(request, view)

    
class IsBusinessForCreateOnly(IsAdminOrCustomPermission):
    """Allows `POST` only for business users. Admins always have access."""

    def has_custom_permission(self, request, view):
        """Grants `POST` access only if the user has a business profile. Other methods are unrestricted."""
        if request.method != "POST":
            return True
        try:
            profile = Profil.objects.get(user=request.user)
            return profile.profile_type == "business"
        except Profil.DoesNotExist:
            return False


class IsOwnerForPatchOnly(IsAdminOrCustomPermission):
    """Allows `PATCH` & `DELETE` only for the owner of the offer. Admins always have access."""

    def has_custom_permission(self, request, view):
        """Grants access only for `PATCH` & `DELETE` if the user is the owner of the offer."""
        if request.method not in ["PATCH", "DELETE"]:
            return True

        offer_id = view.kwargs.get("pk")  # Retrieve offer ID from URL
        try:
            offer = Offers.objects.get(pk=offer_id)
            return request.user == offer.user
        except Offers.DoesNotExist:
            return False  # Deny access if the offer does not exist

    def has_object_permission(self, request, view, obj):
        """Grants object-level access if the user is the owner or an admin."""
        return request.user == obj.user or request.user.is_staff


class IsUniqueReviewer(BasePermission):
    """Ensures that a user can only review a business once."""

    def has_permission(self, request, view):
        """Allows `POST` only if the user has not already reviewed the business."""
        if request.method != "POST":
            return True

        business_user = request.data.get("business_user")
        if not business_user:
            raise ValidationError({"business_user": "A `business_user` must be specified."})

        already_reviewed = Reviews.objects.filter(business_user=business_user, reviewer=request.user).exists()
        return not already_reviewed

    def has_object_permission(self, request, view, obj):
        """Allows `GET` requests for all users. Delegates other methods to `has_permission()`."""
        if request.method == "GET":
            return True
        return self.has_permission(request, view)

    
class IsOwnerCustomerOrAdmin(BasePermission):
    """Allows `PATCH` and `DELETE` only for the review creator if they have a `customer` profile. Admins always have access."""

    def has_object_permission(self, request, view, obj):
        """Grants access for `GET` requests and allows modification only for the review owner or an admin."""
        if request.method == "GET":
            return True
        return request.user == obj.reviewer or request.user.is_staff


class IsOwnerOfProfile(BasePermission):
    """Allows profile editing only for the profile owner. Admins have no special access."""

    def has_object_permission(self, request, view, obj):
        """Grants `GET` access for all users and `PATCH` access only for the profile owner."""
        if request.method == "GET":
            return True
        return obj.user == request.user
