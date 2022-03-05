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

    def add_arguments(self, parser):
        parser.add_argument('days', type=int, default=0)
        
    def handle(self, *args, **options):

        days = options['days']
        
        if days == 0:
            bookmarks = Bookmark.objects.all()
        else:
            today = timezone.now()
            today_minus_days = today - datetime.timedelta(days=days)
            bookmarks = Bookmark.objects.filter(
                link_check_date__lte=today_minus_days)
        

        for idx, bookmark in enumerate(bookmarks):
            print("Checking: %s (%d/%d)" % (bookmark.url, idx, len(bookmarks)))

            try:
                request = urllib.request.Request(
                    bookmark.url, 
                    data=None, 
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
                    }
                )
                response = urllib.request.urlopen(request, timeout=20)
                print(response.code)
                self.update_link_check(bookmark, 'OK')
            except (urllib.error.HTTPError,
                    urllib.error.URLError,
                    ssl.CertificateError,
                    http.client.RemoteDisconnected,
                    ConnectionResetError,
                    socket.timeout,
                    http.client.BadStatusLine):
                self.update_link_check(bookmark, 'error')

    def update_link_check(self, bookmark, status):
        bookmark.link_check_date = timezone.now()
        bookmark.link_check_result = status
        bookmark.save()
        if status == 'error':
            accept = input(_(u"Delete this link? [y/n]"))
            if accept == 'y':
                bookmark.delete()
