# -*- coding: utf-8 -*-

"""
Django settings for django-notes project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

import os
import sys

from django import urls

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DEBUG = True

ALLOWED_HOSTS = ['localhost.notes', 'localhost']

ADMINS = (
    ('Admin', 'org@example.com'),
)

SITE_ID = 1

ROOT_URLCONF = 'config.urls'

WSGI_APPLICATION = 'config.wsgi.application'


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'crispy_forms',
    'notes',
    'tinymce',
    'crispy_bootstrap4',
    'ml'
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'notes.middleware.LoginRequiredMiddleware',
]


#####################################################################
# Templates

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'notes.context_processors.debug_mode',
                'notes.context_processors.get_datetime',
            ],
            'debug': DEBUG,
        },
    },
]

#####################################################################


#####################################################################
# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

#####################################################################


#####################################################################
# Static assets & media uploads
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'notes', 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
#####################################################################


#####################################################################
# Email
SERVER_EMAIL = 'Alex Little <consult@alexlittle.net>'
EMAIL_SUBJECT_PREFIX = '[Alex Little]: '
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_FILE_PATH = '/tmp/'
#####################################################################


#####################################################################
# Authentication
LOGIN_URL = urls.reverse_lazy('profile_login')
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]
#####################################################################


#####################################################################
# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',  # Or INFO, WARNING, ERROR, CRITICAL
        },
    },
}
#####################################################################

DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': ''
        }
    }
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

######################################################################

SESSION_COOKIE_NAME = "notes"

CRISPY_TEMPLATE_PACK = 'bootstrap4'

LOGIN_URL = '/admin/'
LOGIN_REDIRECT_URL = '/'

NOTES_ASSISTANT_ENABLED = False

try:
    from config.local_settings import *
except ImportError:
    import warnings
    warnings.warn("Using default settings. Add `config.local_settings.py`"
                  "for custom settings.")
