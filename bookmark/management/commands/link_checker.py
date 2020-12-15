'''
 Checks the urls to ensure they are valid links

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

from bookmark.models import Bookmark


class Command(BaseCommand):
    help = _(u"Checks the urls to ensure they are still valid links")
    errors = []

    def add_arguments(self, parser):
        parser.add_argument('days', type=int)
        
    def handle(self, *args, **options):

        days = options['days']
        today = timezone.now()
        today_minus_days = today + datetime.timedelta(days=-days)
        bookmarks = Bookmark.objects.filter(
            link_check_date__lte=today_minus_days) \
            .exclude(link_check_result="OK")

        for bookmark in bookmarks:
            print("Checking: " + bookmark.url)

            try:
                response = urllib.request.urlopen(bookmark.url, timeout=20)
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
        if status == 'error':
            accept = input(_(u"Delete this link? [y/n]"))
            if accept == 'y':
                bookmark.delete()
