"""
Soft delete ("papelera"): deleting a record hides it instead of destroying it,
so a mistake can be undone.

`SoftDeleteModel.delete()` is overridden, so every path that deletes one record
(web views, the API, `.delete()` in code) lands in the trash. `objects` only
returns live records, which hides trashed ones from lists, searches, pickers,
exports and counts at once; `all_objects` sees everything, and `hard_delete()`
really removes a row (used when the trash is emptied).

Rows that point at a trashed record (enrolments, registrations, certificates...)
use `alive_through(...)` as their manager so they disappear with it and come
back when it is restored.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def dead(self):
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Live records only."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class TrashManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Everything, trashed or not (`Model.all_objects`)."""


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False, db_index=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        editable=False,
    )

    objects = SoftDeleteManager()
    all_objects = TrashManager()

    class Meta:
        abstract = True

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    # Hooks for subclasses -------------------------------------------------
    def on_soft_delete(self):
        """Detach things that should not keep pointing at a trashed record."""

    # Operations -----------------------------------------------------------
    def soft_delete(self, user=None):
        from core import audit

        user = user or audit.current_user()
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["deleted_at", "deleted_by"])
        self.on_soft_delete()
        audit.log_action(self, "delete", user)

    def restore(self, user=None):
        from core import audit

        user = user or audit.current_user()
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["deleted_at", "deleted_by"])
        audit.log_action(self, "restore", user)

    def delete(self, using=None, keep_parents=False):
        self.soft_delete()
        return 1, {self._meta.label: 1}

    def hard_delete(self, user=None):
        """Remove the row for good (emptying the trash)."""
        from core import audit

        audit.log_action(self, "purge", user or audit.current_user())
        return super().delete()


def alive_through(*paths):
    """A manager that hides rows whose related record(s) are in the trash:
    `alive_through("member", "course")` keeps only rows whose member and course
    are both live."""

    class AliveThroughManager(models.Manager):
        def get_queryset(self):
            queryset = super().get_queryset()
            for path in paths:
                queryset = queryset.filter(**{f"{path}__deleted_at__isnull": True})
            return queryset

    return AliveThroughManager()
