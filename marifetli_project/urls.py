"""
URL configuration for marifetli_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


def root_view(request):
    """Backend kök URL: API bilgisi veya admin'e yönlendirme."""
    if request.path.rstrip('/') == '':
        return JsonResponse({
            'name': 'Marifetli API',
            'admin': '/admin/',
            'api': '/api/',
        })
    from django.http import Http404
    raise Http404()

urlpatterns = [
    path('', root_view),
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('api/auth/', include('users.urls')),
    path('api/categories/', include('categories.urls')),
    path('api/questions/', include('questions.urls')),
    path('api/answers/', include('answers.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/onboarding/', include('onboarding.urls')),
    path('api/achievements/', include('achievements.urls')),
    path('api/blog/', include('blog.urls')),
    path('api/favorites/', include('favorites.urls')),
    path('api/emails/', include('emails.urls')),
    path('api-auth/', include('rest_framework.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)