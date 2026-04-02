"""
WSGI config for marifetli_project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from core.observability import setup_observability

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marifetli_project.settings")
setup_observability("marifetli-backend")

application = get_wsgi_application()
