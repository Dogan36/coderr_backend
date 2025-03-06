from rest_framework.permissions import BasePermission
from coderr_app.models import Profil, Orders, Offers, Reviews

class IsAdminOrCustomPermission(BasePermission):
    """
    Erlaubt Admins (`is_staff=True`) immer den Zugriff.
    Falls kein Admin, muss eine spezifische Permission greifen.
    """

    def has_permission(self, request, view):
        if request.user and request.user.is_staff:
            return True  # Admins dürfen immer alles
        return self.has_custom_permission(request, view)

    def has_custom_permission(self, request, view):
        """
        Diese Methode wird von anderen Klassen überschrieben.
        """
        return False  # Standardmäßig kein Zugriff

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True  # Admins haben auch Objekt-Zugriff
        return self.has_custom_object_permission(request, view, obj)

    def has_custom_object_permission(self, request, view, obj):
        """
        Diese Methode kann überschrieben werden.
        """
        return False

class IsBusinessForPatchOnly(IsAdminOrCustomPermission):
    """
    Erlaubt `PATCH` nur für den Anbieter (`business_user`) oder Admins.
    Kunden können den Status NICHT ändern.
    """

    def has_custom_permission(self, request, view):
        if request.method != "PATCH":
            return True  # Andere Methoden brauchen keine Restriktionen

        try:
            order = Orders.objects.get(pk=view.kwargs.get("pk"))
            return order.business_user == request.user
        except Orders.DoesNotExist:
            return False  # Falls Bestellung nicht existiert, verweigern
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:  # Admins dürfen immer
            return True

        # Nur der Business-User darf PATCH-Anfragen senden
        return request.method == "PATCH" and obj.business_user == request.user
    
class IsCustomerForCreateOnly(IsAdminOrCustomPermission):
    def has_permission(self, request, view):
        # Prüfe, ob die Anfrage eine Bestellung erstellen will
        if request.method == "POST":
            try:
                profil = Profil.objects.get(user=request.user)
                return profil.profile_type == "customer" 
            except Profil.DoesNotExist:
                return False 
        return True
    def has_object_permission(self, request, view, obj):
        # `GET` für alle erlauben
        if request.method == "GET":
            return True
        return self.has_permission(request, view)
    
class IsBusinessForCreateOnly(IsAdminOrCustomPermission):
    """
    Erlaubt das Erstellen (`POST`) nur für Business-User.
    Admins haben immer Zugriff.
    """
    def has_custom_permission(self, request, view):
        if request.method != "POST":
            return True  # Andere Methoden brauchen keine Restriktionen
        try:
            profil = Profil.objects.get(user=request.user)
            return profil.profile_type == "business"
        except Profil.DoesNotExist:
            return False
    
class IsOwnerForPatchOnly(IsAdminOrCustomPermission):
    """
    Erlaubt `PATCH` & `DELETE` nur für den Besitzer des Angebots.
    Admins haben immer Zugriff.
    """

    def has_custom_permission(self, request, view):
        if request.method not in ["PATCH", "DELETE"]:
            return True  # Andere Methoden brauchen keine Restriktionen

        offer_id = view.kwargs.get("pk")  # Angebots-ID aus der URL abrufen
        try:
            offer = Offers.objects.get(pk=offer_id)
            print(f"🔍 Angebot gefunden: {offer.id} gehört {offer.user}")  
            print(f"🔍 Request User: {request.user} (Admin: {request.user.is_staff})")

            if request.user == offer.user:
                print("✅ Zugriff erlaubt (User ist Besitzer)")
                return True
            else:
                print("❌ Zugriff verweigert (Nicht der Besitzer)")
                return False

        except Offers.DoesNotExist:
            print("❌ Angebot nicht gefunden!")
            return False  # Falls das Angebot nicht existiert, kein Zugriff

    def has_object_permission(self, request, view, obj):
        """
        Prüft den Zugriff auf ein einzelnes Angebot.
        """
        print(f"🔎 has_object_permission() aufgerufen für: {obj}")
        return request.user == obj.user or request.user.is_staff 

class IsUniqueReviewer(BasePermission):
    """
    Erlaubt `POST` nur, wenn der Benutzer das Business noch nicht bewertet hat.
    """
    
    def has_permission(self, request, view):
        # Falls es keine `POST`-Anfrage ist, Permission erlauben (GET, PATCH, DELETE sind erlaubt)
        if request.method != "POST":
            return True

        # Business-ID aus der Anfrage holen
        business_user = request.data.get("business_user")

        # Falls keine Business-ID übergeben wurde, abbrechen (müsste eigentlich schon vom Serializer geprüft werden)
        if not business_user:
            return False

        # Prüfen, ob der aktuelle Benutzer das Business bereits bewertet hat
        already_reviewed = Reviews.objects.filter(business_user=business_user, reviewer=request.user).exists()
        
        # Falls eine Bewertung existiert, verweigern wir die Erlaubnis
        if already_reviewed:
            return False
        
        return True
    def has_object_permission(self, request, view, obj):
        # `GET` für alle erlauben
        if request.method == "GET":
            return True
        return self.has_permission(request, view)
    
class IsOwnerCustomerOrAdmin(BasePermission):
    """
    Erlaubt `PATCH` und `DELETE` nur für den Ersteller der Bewertung, wenn dieser ein `customer`-Profil hat.
    Admins dürfen immer bearbeiten/löschen.
    """

    def has_object_permission(self, request, view, obj):
        # `GET` für alle Benutzer erlauben
        if request.method == "GET":
            return True

        # Ersteller der Bewertung und Admins dürfen bearbeiten/löschen
        if request.method in ["PATCH", "DELETE"]:
            # Prüfen, ob der Nutzer ein `customer`-Profil hat
            try:
                profil = Profil.objects.get(user=request.user)
                if profil.profile_type == "customer" and obj.reviewer == request.user:
                    return True  # ✅ Erlaubt für Kunden, die ihre eigene Bewertung bearbeiten
            except Profil.DoesNotExist:
                return False

            # Admins dürfen immer bearbeiten/löschen
            return request.user.is_staff

        return False
