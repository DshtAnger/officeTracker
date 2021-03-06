"""
WSGI config for officeTracker project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

#add

from os.path import join, dirname, abspath

PROJECT_DIR = dirname(dirname(abspath(__file__)))

import sys

sys.path.insert(0, PROJECT_DIR)

#end

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'officeTracker.settings')

application = get_wsgi_application()
