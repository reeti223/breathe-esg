from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.authtoken.views import obtain_auth_token
from ingestion.views import IngestView, RecordsView, ReviewView, StatsView
import os

def serve_frontend(request):
    from django.http import HttpResponse
    frontend_path = os.path.join(settings.BASE_DIR.parent, 'frontend', 'index.html')
    with open(frontend_path, 'r', encoding='utf-8') as f:
        return HttpResponse(f.read(), content_type='text/html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login/', obtain_auth_token),
    path('api/ingest/<str:source_type>/', IngestView.as_view()),
    path('api/records/', RecordsView.as_view()),
    path('api/records/<uuid:record_id>/review/', ReviewView.as_view()),
    path('api/stats/', StatsView.as_view()),
    path('', serve_frontend),
]