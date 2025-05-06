
from django.contrib import admin
from django.urls import include, path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static

def home_view(request):
    return JsonResponse({"message": "Welcome to Coderr Backend API"})

urlpatterns = [
    path('', home_view),  # Füge eine Root-Route hinzu
    path('admin/', admin.site.urls),
    path('api/', include('coderr_app.api.urls')),  # Füge die API-Route hinzu
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)