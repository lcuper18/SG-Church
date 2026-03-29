"""
WSGI config for SG Church project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sg_church.settings.local")

application = get_wsgi_application()
