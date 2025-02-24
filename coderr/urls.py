
from django.contrib import admin
from django.urls import include, path, include
from django.http import JsonResponse
def home_view(request):
    return JsonResponse({"message": "Welcome to Join Backend API"})

urlpatterns = [
    path('', home_view),  # Füge eine Root-Route hinzu
    path('admin/', admin.site.urls),
    path('api/', include('coder_app.urls')),  # Füge die API-Route hinzu
]
