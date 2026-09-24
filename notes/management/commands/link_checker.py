"""
Checks the urls to ensure they are valid links

"""

import datetime
import http
import smtplib
import ssl
import time
from urllib import error, request
from urllib.parse import urlparse

from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _

from notes.models import Note, NotesConfig
from notes.utils import send_templated_mail


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# Minimum gap between requests to the same domain - avoids tripping CDN/WAF rate
# limiting (e.g. Fastly, Cloudflare) when many notes share a domain.
SAME_DOMAIN_DELAY_SECONDS = 2

# Network-level failures that are frequently just a transient blip (a dropped
# connection, a slow server) rather than proof the link is actually dead.
TRANSIENT_EXCEPTIONS = (
    TimeoutError,
    ssl.CertificateError,
    http.client.RemoteDisconnected,
    ConnectionResetError,
    http.client.BadStatusLine,
    error.URLError,
)

# How many times to attempt a single URL (the first attempt plus retries)
# before giving up and recording it as an error, and how long to wait between
# attempts. A 5xx response is retried the same way, since those are often the
# origin server having a bad moment rather than the page being gone.
CHECK_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 3

# A note's link is only reported/offered for deletion once it has come back
# non-ok on this many consecutive runs - a single failed run is very often a
# transient network issue or a one-off block, not a genuinely dead link.
CONSECUTIVE_FAILURES_THRESHOLD = 2

# Fallback used if NotesConfig's "link_check.email_interval_hours" is missing
# or invalid - links are still checked every cron run, but the report email
# is only sent once per interval so a noisy backlog doesn't mean an email a
# run.
DEFAULT_EMAIL_INTERVAL_HOURS = 24

REQUEST_HEADERS = {
    # A current-looking UA matters here - some sites' WAFs (Cloudflare, security
    # plugins, etc.) block or reset connections from known stale/scraper UA
    # strings (e.g. an old Chrome build), which was previously causing live
    # sites to be misreported as broken links.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
}


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
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help=_(
                "Only check the N links with the oldest link_check_date, instead of every "
                "due link - lets a scheduled run work through the backlog gradually rather "
                "than hitting every site at once."
            ),
        )

    def handle(self, *args, **options):
        days = options["days"]
        interactive = options["interactive"]
        limit = options["limit"]

        notes = self.get_notes_to_check(days, limit)
        error_list, redirect_list, blocked_list = self.check_notes(notes)

        self.maybe_send_report()

        self.review_errors(error_list, interactive)
        self.print_list("redirects", redirect_list)

        # Not offered for deletion (interactively or otherwise) - a 403/429 is
        # frequently a bot/WAF block rather than proof the link is dead.
        self.print_list("blocked", blocked_list)

    def get_notes_to_check(self, days, limit):
        """Build the queryset of notes with links due to be checked."""
        if days == 0:
            notes = Note.objects.all()
        else:
            today = timezone.now()
            today_minus_days = today - datetime.timedelta(days=days)
            notes = Note.objects.filter(link_check_date__lte=today_minus_days)

        notes = notes.exclude(url__isnull=True).exclude(url="").order_by("link_check_date")
        if limit:
            notes = notes[:limit]
        return notes

    def check_notes(self, notes):
        """Check every note's link, recording the outcome of each.

        Returns the (error_list, redirect_list, blocked_list) notes to report on.
        """
        error_list = []
        redirect_list = []
        blocked_list = []
        domain_last_request = {}

        opener = request.build_opener(NoRedirect)
        request.install_opener(opener)

        total = len(notes)
        for idx, note in enumerate(notes):
            print(f"Checking: {note.url} ({idx}/{total})")
            self.throttle_domain(note.url, domain_last_request)

            result = self.check_url(note.url)
            self.update_link_check(note, result)
            self.classify_result(note, result, error_list, redirect_list, blocked_list)

        return error_list, redirect_list, blocked_list

    def throttle_domain(self, url, domain_last_request):
        """Sleep if needed so the same domain isn't hit faster than SAME_DOMAIN_DELAY_SECONDS."""
        domain = urlparse(url).netloc
        last_request = domain_last_request.get(domain)
        if last_request is not None:
            elapsed = time.monotonic() - last_request
            if elapsed < SAME_DOMAIN_DELAY_SECONDS:
                time.sleep(SAME_DOMAIN_DELAY_SECONDS - elapsed)
        domain_last_request[domain] = time.monotonic()

    def classify_result(self, note, result, error_list, redirect_list, blocked_list):
        """Sort a checked note into the relevant report list, if any."""
        if result == "redirect":
            # Still checked and recorded above - just not flagged as broken,
            # e.g. for links behind a login screen that always redirect.
            if not note.link_check_ignore_redirects:
                redirect_list.append(note)
        elif result == "error" and note.link_check_fail_count >= CONSECUTIVE_FAILURES_THRESHOLD:
            error_list.append(note)
        elif result == "blocked" and note.link_check_fail_count >= CONSECUTIVE_FAILURES_THRESHOLD:
            blocked_list.append(note)

    def review_errors(self, error_list, interactive):
        """Print broken links, offering to delete each one when run interactively."""
        print(f"{len(error_list)} errors")
        for idx, el in enumerate(error_list):
            print(f"{idx}/{len(error_list)} {el.url}")
            if interactive:
                accept = input(_("Delete this link? [y/n]"))
                if accept == "y":
                    el.delete()

    def print_list(self, label, items):
        print(f"{len(items)} {label}")
        for idx, item in enumerate(items):
            print(f"{idx}/{len(items)} {item.url}")

    def check_url(self, url):
        """
        Fetch url, retrying transient failures and 5xx responses up to
        CHECK_ATTEMPTS times. Returns one of "ok", "redirect", "blocked" or
        "error".
        """
        last_exc = None
        for attempt in range(1, CHECK_ATTEMPTS + 1):
            result, last_exc = self.attempt_fetch(url, last_exc)
            if result is not None:
                return result

            if attempt < CHECK_ATTEMPTS:
                print(f"Retrying ({attempt}/{CHECK_ATTEMPTS - 1})...")
                time.sleep(RETRY_DELAY_SECONDS)

        print(f"Error: {last_exc}")
        return "error"

    def attempt_fetch(self, url, last_exc):
        """
        Make a single attempt to fetch url.

        Returns a (result, last_exc) tuple - result is None if the attempt
        failed in a way that's worth retrying (a transient exception, or an
        HTTP 5xx), in which case last_exc is updated to the new exception.
        """
        try:
            my_request = request.Request(url, method="GET", headers=REQUEST_HEADERS)
            response = request.urlopen(my_request, timeout=20)
            print(response.code)
            return "ok", last_exc
        except error.HTTPError as exc:
            # HTTPError is a subclass of URLError, so it must be handled
            # before the generic TRANSIENT_EXCEPTIONS catch below - that
            # includes URLError and would otherwise swallow every HTTP
            # error code as a transient failure.
            return self.classify_http_error(exc), exc
        except TRANSIENT_EXCEPTIONS as exc:
            return None, exc

    def classify_http_error(self, exc):
        """Map an HTTPError to a check_url() result, or None if it's worth retrying."""
        if exc.code in (301, 302, 303, 307, 308):
            print("has been redirected")
            return "redirect"
        if exc.code in (403, 429):
            # Almost always a bot/WAF block on an automated request rather
            # than a genuinely dead link - not worth retrying.
            print(f"Blocked: HTTP {exc.code}")
            return "blocked"
        if exc.code >= 500:
            return None
        print(f"Error: HTTP {exc.code}")
        return "error"

    def update_link_check(self, note, result):
        note.link_check_date = timezone.now()
        note.link_check_result = result
        if result in ("error", "blocked"):
            note.link_check_fail_count += 1
        else:
            note.link_check_fail_count = 0
        note.save()

    def maybe_send_report(self):
        # Off by default - enable via NotesConfig (e.g. in the admin) rather than code,
        # so it can be turned on/off and re-addressed without a deploy.
        if NotesConfig.get_value("link_check.email_enabled").strip().lower() != "true":
            return

        last_sent_at = self.get_last_email_sent_at()
        interval = datetime.timedelta(hours=self.get_email_interval_hours())
        if last_sent_at is not None and timezone.now() - last_sent_at < interval:
            print("Skipping link checker report email - not due yet")
            return

        # Query the full current backlog rather than just what this run checked -
        # links flagged by an earlier run (and not yet due for a recheck) still
        # belong in the digest.
        error_list = list(
            Note.objects.exclude(url="").filter(
                link_check_result="error",
                link_check_fail_count__gte=CONSECUTIVE_FAILURES_THRESHOLD,
            )
        )
        blocked_list = list(
            Note.objects.exclude(url="").filter(
                link_check_result="blocked",
                link_check_fail_count__gte=CONSECUTIVE_FAILURES_THRESHOLD,
            )
        )
        redirect_list = list(
            Note.objects.exclude(url="").filter(
                link_check_result="redirect",
                link_check_ignore_redirects=False,
            )
        )
        if not (error_list or redirect_list or blocked_list):
            return

        if self.send_report(error_list, redirect_list, blocked_list):
            NotesConfig.objects.update_or_create(
                name="link_check.email_last_sent_at",
                defaults={"value": timezone.now().isoformat()},
            )

    def get_email_interval_hours(self):
        try:
            hours = int(NotesConfig.get_value("link_check.email_interval_hours"))
            if hours > 0:
                return hours
        except ValueError:
            pass
        return DEFAULT_EMAIL_INTERVAL_HOURS

    def get_last_email_sent_at(self):
        raw = NotesConfig.get_value("link_check.email_last_sent_at")
        if not raw:
            return None
        parsed = parse_datetime(raw)
        if parsed is not None and timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed)
        return parsed

    def send_report(self, error_list, redirect_list, blocked_list):
        recipients = NotesConfig.get_value("link_check.email_recipients")
        recipient_list = [addr.strip() for addr in recipients.split(",") if addr.strip()] or None

        # Attach the edit link so the email can link there directly - clicking
        # through to the site itself isn't useful, you want to fix/remove the note.
        domain = Site.objects.get_current().domain
        for note in [*error_list, *redirect_list, *blocked_list]:
            note.edit_url = f"https://{domain}{reverse('notes:edit', args=[note.id])}"

        try:
            send_templated_mail(
                subject=_("Link checker report"),
                template_name="link_check_report",
                context={
                    "error_list": error_list,
                    "redirect_list": redirect_list,
                    "blocked_list": blocked_list,
                },
                recipient_list=recipient_list,
            )
            return True
        except (OSError, smtplib.SMTPException) as exc:
            # don't let a broken mail server stop the rest of the cron run
            print(f"Failed to send link checker report email: {exc}")
            return False
