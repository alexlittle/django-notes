'''
Removes unused tags
'''

import datetime
import http
import socket
import ssl
import urllib.error
import urllib.request


from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from bookmark.models import Bookmark, BookmarkTag, Tag


class Command(BaseCommand):
    help = _(u"Checks the urls to ensure they are still valid links")
    errors = []

    def handle(self, *args, **options):
        tags = Tag.objects.filter(favourite=False)
        for tag in tags:
            if tag.bookmark_count() == 0:
                print(tag.name + ": deleted")
                tag.delete()

        for tag in tags:        
            if tag.bookmark_count() == 1:
                print(tag.name + ": only 1 use")