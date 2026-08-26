import contextlib
import io

from django.core.management import call_command

from .base import NotesCommandTestCase


def _run_and_capture(*args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        # tag_diff uses plain print(), not self.stdout.write(), so
        # call_command's stdout= kwarg won't capture it - redirecting
        # sys.stdout is the only way to see the output.
        call_command("tag_diff", *args)
    return buf.getvalue()


class TagDiffCommandTests(NotesCommandTestCase):
    def test_reports_a_close_match_above_the_cutoff(self):
        self.make_tag(name="python")
        self.make_tag(name="pythom")  # one-character typo
        self.make_tag(name="gardening")

        output = _run_and_capture(0.6)

        self.assertIn("python", output)
        self.assertIn("pythom", output)
        self.assertNotIn("gardening", output)

    def test_raising_the_cutoff_excludes_weaker_matches(self):
        self.make_tag(name="python")
        self.make_tag(name="pythom")

        output = _run_and_capture(0.99)

        self.assertEqual(output.strip(), "")

    def test_default_cutoff_is_used_when_omitted(self):
        self.make_tag(name="python")
        self.make_tag(name="pythom")

        with_default = _run_and_capture()
        with_explicit_default = _run_and_capture(0.6)

        self.assertEqual(with_default, with_explicit_default)

    def test_identically_named_tags_belonging_to_different_users_are_never_flagged(self):
        # Comparison is by exact name string, and current_tag is filtered
        # out of the list it's compared against (`tag != current_tag`).
        # Two different users' tags that happen to share the exact same
        # name are therefore invisible to this tool - arguably the most
        # important duplicate to catch, and the one case it can't catch.
        self.make_tag(user=self.user, name="python")
        self.make_tag(user=self.other_user, name="python")

        output = _run_and_capture(0.6)

        self.assertEqual(output.strip(), "")
