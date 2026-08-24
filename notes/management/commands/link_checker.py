"""
Checks the urls to ensure they are valid links

"""

import datetime
import http
import ssl
from urllib import error, request

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from notes.models import Note


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Command(BaseCommand):
    help = _("Checks the urls to ensure they are still valid links")

    def add_arguments(self, parser):
        parser.add_argument("days", type=int, default=0)

    def handle(self, *args, **options):

        days = options["days"]

        if days == 0:
            notes = Note.objects.all()
        else:
            today = timezone.now()
            today_minus_days = today - datetime.timedelta(days=days)
            notes = Note.objects.filter(link_check_date__lte=today_minus_days)

        notes = notes.exclude(url__isnull=True).exclude(url="")
        error_list = []
        redirect_list = []

        for idx, note in enumerate(notes):
            print(f"Checking: {note.url} ({idx}/{len(notes)})")
            opener = request.build_opener(NoRedirect)
            request.install_opener(opener)
            try:
                my_request = request.Request(
                    note.url,
                    method="GET",
                    headers={
                        "User-Agent": """Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) 
                        AppleWebKit/537.36 (KHTML, like Gecko) 
                        Chrome/35.0.1916.47 Safari/537.36"""
                    },
                )
                response = request.urlopen(my_request, timeout=20)
                print(response.code)
                self.update_link_check(note, "ok")
            except (
                TimeoutError,
                ssl.CertificateError,
                http.client.RemoteDisconnected,
                ConnectionResetError,
                http.client.BadStatusLine,
            ):
                print("Error")
                self.update_link_check(note, "error")
                error_list.append(note)
            except (error.URLError, error.HTTPError):
                print("has been redirected")
                self.update_link_check(note, "redirect")
                redirect_list.append(note)

        print(f"{len(error_list)} errors")
        for idx, el in enumerate(error_list):
            print(f"{idx}/{len(error_list)} {el.url}")
            accept = input(_("Delete this link? [y/n]"))
            if accept == "y":
                el.delete()

        print(f"{len(redirect_list)} redirects")
        for idx, rl in enumerate(redirect_list):
            print(f"{idx}/{len(redirect_list)} {rl.url}")

    def update_link_check(self, note, result):
        note.link_check_date = timezone.now()
        note.link_check_result = result
        note.save()
