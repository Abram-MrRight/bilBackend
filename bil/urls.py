
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from dashboard import views as dashboard_views

from api import views



urlpatterns = [
    path('', include('dashboard.urls')),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('dashboard/', include('dashboard.urls')),


]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

