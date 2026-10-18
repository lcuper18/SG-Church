"""Signed links that let a person stop reminders and announcements without logging in."""

from django.core import signing

SALT = "email-unsubscribe"


def make_token(member):
    # No expiry: the link in an old e-mail must keep working.
    return signing.dumps(str(member.pk), salt=SALT)


def member_for(token):
    """The (live) member a token was made for, or None if it is forged or the member is gone."""
    from members.models import Member

    try:
        pk = signing.loads(token, salt=SALT)
    except signing.BadSignature:
        return None
    try:
        return Member.objects.select_related("tenant").filter(pk=pk).first()
    except (ValueError, TypeError):
        return None
