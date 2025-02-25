from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from coderr_app.models import Offers, OfferDetails, Orders, Profil, Reviews


admin.site.register(Offers)
admin.site.register(OfferDetails)
admin.site.register(Orders)
admin.site.register(Profil)
admin.site.register(Reviews)