from django.contrib import admin
from django.contrib import admin
from django.contrib.auth.models import User
from .models import Profil, Offers, OfferDetails, Orders, Reviews  # Stelle sicher, dass alle importiert sind

class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "first_name", "last_name", "is_staff")
    search_fields = ("id", "username", "email")

class ProfilAdmin(admin.ModelAdmin):  # Admin-Klasse für `Profil`
    list_display = ("user", "profile_type")  # Falls `created` existiert
      # `user__username`, damit nach Namen gesucht wird

# Standard-User-Modell deregistrieren und mit der neuen Klasse neu registrieren
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Profil, ProfilAdmin)  # Profil mit `ProfilAdmin` registrieren
admin.site.register(Offers)
admin.site.register(OfferDetails)
admin.site.register(Orders)
admin.site.register(Reviews)