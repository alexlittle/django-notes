'''
 Checks the urls to ensure they are valid links

'''

import datetime
import http
import socket
import ssl
from urllib import request, error

from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from bookmark.models import Bookmark


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

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
            bookmarks = Bookmark.objects.filter(link_check_date__lte=today_minus_days)

        error_list = []
        redirect_list = []

        for idx, bookmark in enumerate(bookmarks):
            print("Checking: %s (%d/%d)" % (bookmark.url, idx, len(bookmarks)))
            opener = request.build_opener(NoRedirect)
            request.install_opener(opener)
            try:
                my_request = request.Request(
                    bookmark.url,
                    method="GET",
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
                    }
                )
                response = request.urlopen(my_request, timeout=20)
                print(response.code)
                self.update_link_check(bookmark, "ok")
            except (ssl.CertificateError,
                    http.client.RemoteDisconnected,
                    ConnectionResetError,
                    socket.timeout,
                    http.client.BadStatusLine):
                print("Error")
                self.update_link_check(bookmark, "error")
                error_list.append(bookmark)
            except (error.URLError, error.HTTPError):
                print("has been redirected")
                self.update_link_check(bookmark, "redirect")
                redirect_list.append(bookmark)

        print("%d errors" % len(error_list))
        for idx, el in enumerate(error_list):
            print("%d/%d %s" % (idx, len(error_list), el.url))
            accept = input(_(u"Delete this link? [y/n]"))
            if accept == 'y':
                el.delete()

        print("%d redirects" % len(redirect_list))
        for idx, rl in enumerate(redirect_list):
            print("%d/%d %s" % (idx, len(redirect_list), rl.url))

    def update_link_check(self, bookmark, result):
        bookmark.link_check_date = timezone.now()
        bookmark.link_check_result = result
        bookmark.save()
