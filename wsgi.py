import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "globus_portal_framework.settings")
application = get_wsgi_application()
