'''
 Checks the urls to ensure they are valid links

'''

import datetime
import http
import socket
import ssl
import urllib.error
import urllib.request


from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from bookmark.models import Bookmark


class Command(BaseCommand):
    help = _(u"Checks the urls to ensure they are still valid links")
    errors = []

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):

        today = timezone.now()
        today_minus_7 = today + datetime.timedelta(days=-7)
        #today_minus_7 = timezone.make_aware(today_minus_7)
        bookmarks = Bookmark.objects.filter(link_check_date__lte=today_minus_7).exclude(link_check_result="OK")
        
        for bookmark in bookmarks:
            print("Checking: " + bookmark.url)
            
            try:
                response = urllib.request.urlopen(bookmark.url, timeout=10)
                print(response.code)
                self.update_link_check(bookmark, 'OK')
            except urllib.error.HTTPError:
                self.update_link_check(bookmark, 'error')
            except urllib.error.URLError:
                self.update_link_check(bookmark, 'error')
            except ssl.CertificateError:
                self.update_link_check(bookmark, 'error')
            except http.client.RemoteDisconnected:
                self.update_link_check(bookmark, 'error')
            except ConnectionResetError:
                self.update_link_check(bookmark, 'error')
            except socket.timeout:
                self.update_link_check(bookmark, 'error')
            except http.client.BadStatusLine:
                self.update_link_check(bookmark, 'error')
        
    def update_link_check(self, bookmark, status):
        bookmark.link_check_date = timezone.now()
        bookmark.link_check_result = status
        bookmark.save()
            
            