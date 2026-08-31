"""
Checks the urls to ensure they are valid links

"""

import datetime
import http
import smtplib
import ssl
from urllib import error, request

from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from notes.models import Note, NotesConfig
from notes.utils import send_templated_mail


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Command(BaseCommand):
    help = _("Checks the urls to ensure they are still valid links")

    def add_arguments(self, parser):
        parser.add_argument("days", type=int, nargs="?", default=0)
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            default=True,
            help=_(
                "Do not prompt before deleting broken links; just record the failure "
                "(used when run unattended, e.g. from cron)."
            ),
        )

    def handle(self, *args, **options):

        days = options["days"]
        interactive = options["interactive"]

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
                        "User-Agent": (
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/35.0.1916.47 Safari/537.36"
                        )
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
            except error.HTTPError as exc:
                if exc.code in (301, 302, 303, 307, 308):
                    print("has been redirected")
                    self.update_link_check(note, "redirect")
                    # Still checked and recorded above - just not flagged as broken,
                    # e.g. for links behind a login screen that always redirect.
                    if not note.link_check_ignore_redirects:
                        redirect_list.append(note)
                else:
                    print(f"Error: HTTP {exc.code}")
                    self.update_link_check(note, "error")
                    error_list.append(note)
            except error.URLError:
                print("Error")
                self.update_link_check(note, "error")
                error_list.append(note)

        if error_list or redirect_list:
            self.send_report(error_list, redirect_list)

        print(f"{len(error_list)} errors")
        for idx, el in enumerate(error_list):
            print(f"{idx}/{len(error_list)} {el.url}")
            if interactive:
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

    def send_report(self, error_list, redirect_list):
        # Off by default - enable via NotesConfig (e.g. in the admin) rather than code,
        # so it can be turned on/off and re-addressed without a deploy.
        if NotesConfig.get_value("link_check.email_enabled").strip().lower() != "true":
            return

        recipients = NotesConfig.get_value("link_check.email_recipients")
        recipient_list = [addr.strip() for addr in recipients.split(",") if addr.strip()] or None

        # Attach the edit link so the email can link there directly - clicking
        # through to the site itself isn't useful, you want to fix/remove the note.
        domain = Site.objects.get_current().domain
        for note in [*error_list, *redirect_list]:
            note.edit_url = f"https://{domain}{reverse('notes:edit', args=[note.id])}"

        try:
            send_templated_mail(
                subject=_("Link checker report"),
                template_name="link_check_report",
                context={"error_list": error_list, "redirect_list": redirect_list},
                recipient_list=recipient_list,
            )
        except (OSError, smtplib.SMTPException) as exc:
            # don't let a broken mail server stop the rest of the cron run
            print(f"Failed to send link checker report email: {exc}")
