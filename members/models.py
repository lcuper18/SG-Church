"""
Member models for SG Church.
"""

from django.core.validators import FileExtensionValidator
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.urls import reverse
import re
import uuid

from django.core.exceptions import ValidationError

from core.softdelete import SoftDeleteModel
from core.text import fold
from core.validators import FileSizeValidator


class UserManager(BaseUserManager):
    """Custom user manager that uses email as the identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es requerido")
        email = self.normalize_email(email)
        username = email.split("@")[0]  # Use part of email as username
        extra_fields.setdefault("username", username)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model for SG Church.
    Extends Django's AbstractUser with role-based access.
    """

    ROLE_CHOICES = [
        ("admin", "Administrador"),
        ("pastor", "Pastor"),
        ("treasurer", "Tesorero/a"),
        ("teacher", "Maestro/a"),
        ("volunteer", "Voluntario/a"),
        ("member", "Miembro"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Use custom manager
    objects = UserManager()

    # Role and permissions
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")

    # Tenant relationship (church this user belongs to)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )

    # Link to member profile (optional)
    member_profile = models.OneToOneField(
        "Member",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_user",
    )

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["username"]

    def __str__(self):
        return self.get_full_name() or self.username

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    @property
    def is_church_admin(self):
        return self.role == "admin" or self.is_superuser

    @property
    def can_manage_finance(self):
        return self.is_superuser or self.role in ["admin", "treasurer"]

    @property
    def can_manage_members(self):
        return self.is_superuser or self.role in ["admin", "pastor", "volunteer"]

    @property
    def can_manage_education(self):
        return self.is_superuser or self.role in ["admin", "teacher"]

    @property
    def can_view_roster(self):
        """See who is enrolled in a course or block (names only). Wider than
        the member directory: teachers need it to certify their students."""
        return self.can_manage_members or self.can_manage_education

    @property
    def can_view_pastoral_notes(self):
        """Pastoral notes are the most sensitive free text in the system."""
        return self.is_superuser or self.role in ["admin", "pastor"]


class Member(SoftDeleteModel):
    """
    Represents a church member.
    """

    STATUS_CHOICES = [
        ("visitor", "Visitante"),
        ("attendee", "Asistente"),
        ("member", "Miembro"),
        ("inactive", "Inactivo"),
    ]

    GENDER_CHOICES = [
        ("male", "Masculino"),
        ("female", "Femenino"),
        ("other", "Otro"),
    ]

    MARITAL_STATUS_CHOICES = [
        ("single", "Soltero/a"),
        ("married", "Casado/a"),
        ("divorced", "Divorciado/a"),
        ("widowed", "Viudo/a"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Tenant (church)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="members"
    )

    # Basic information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    # National ID (cédula, DNI, DIMEX, passport...): tells apart people who share a
    # name, and is printed on certificates. `national_id_key` is the same value
    # without spaces/hyphens/dots, upper-case, so "1-1234-5678" and "112345678"
    # are the same person; that is what must be unique among live members.
    national_id = models.CharField(max_length=30, blank=True)
    national_id_key = models.CharField(max_length=30, blank=True, editable=False)

    # Demographics
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    marital_status = models.CharField(
        max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True
    )

    # Sacraments (lightweight - see the education app for eligibility checks
    # that key off these fields)
    is_baptized = models.BooleanField(default=False)
    baptism_date = models.DateField(null=True, blank=True)

    # Membership status
    member_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="visitor"
    )
    membership_date = models.DateField(null=True, blank=True)

    # Family relationship
    family = models.ForeignKey(
        "Family",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )

    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    # Photo
    photo = models.ImageField(
        upload_to="members/photos/",
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
            FileSizeValidator(max_mb=5),
        ],
    )

    # Notes
    notes = models.TextField(blank=True)

    # Tags
    tags = models.ManyToManyField("Tag", blank=True, related_name="members")

    # Accent-free, lower-case copy of name, e-mail and phone that searches run
    # against (kept in save()); see core.text.fold.
    search_text = models.TextField(blank=True, default="", editable=False)

    # User account (optional - for member portal access)
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="member",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "members"
        verbose_name = "Member"
        verbose_name_plural = "Members"
        ordering = ["last_name", "first_name"]
        constraints = [
            # One person per ID within a church (people in the trash don't count).
            models.UniqueConstraint(
                fields=["tenant", "national_id_key"],
                condition=models.Q(deleted_at__isnull=True) & ~models.Q(national_id_key=""),
                name="unique_live_national_id_per_tenant",
            )
        ]
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["email"]),
            models.Index(fields=["member_status"]),
            models.Index(fields=["tenant", "member_status"]),
        ]

    SEARCH_SOURCE_FIELDS = ("first_name", "last_name", "email", "phone", "national_id")

    @staticmethod
    def normalize_national_id(value):
        return re.sub(r"[^0-9A-Za-z]", "", str(value or "")).upper()

    @property
    def national_id_hint(self):
        """Last digits only (···5678): enough to tell homonyms apart in pickers
        without showing the whole number to everyone."""
        key = self.national_id_key or self.normalize_national_id(self.national_id)
        return f"···{key[-4:]}" if key else ""

    def build_search_text(self):
        parts = [str(getattr(self, name) or "") for name in self.SEARCH_SOURCE_FIELDS]
        parts.append(self.normalize_national_id(self.national_id))  # searchable without hyphens
        return fold(" ".join(parts))

    def clean(self):
        super().clean()
        self.national_id = (self.national_id or "").strip()
        key = self.normalize_national_id(self.national_id)
        if key and self.tenant_id:
            clash = (
                Member.objects.filter(tenant_id=self.tenant_id, national_id_key=key)
                .exclude(pk=self.pk)
                .first()
            )
            if clash:
                raise ValidationError(
                    {"national_id": f"Esta identificación ya pertenece a {clash.full_name}."}
                )

    def save(self, *args, **kwargs):
        self.national_id = (self.national_id or "").strip()
        self.national_id_key = self.normalize_national_id(self.national_id)
        self.search_text = self.build_search_text()
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and set(update_fields) & set(self.SEARCH_SOURCE_FIELDS):
            kwargs["update_fields"] = {*update_fields, "search_text", "national_id_key"}
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_absolute_url(self):
        return reverse("member_detail", kwargs={"pk": self.pk})

    def on_soft_delete(self):
        # A trashed person can no longer head a family.
        Family.all_objects.filter(head_of_family=self).update(head_of_family=None)


class Family(SoftDeleteModel):
    """
    Represents a family unit within a church.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Tenant (church)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="families"
    )

    # Family information
    name = models.CharField(
        max_length=255, help_text='Family name (e.g., "Garcia Family")'
    )
    head_of_family = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="head_of_families",
    )

    # Address (shared by family members)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    # Phone
    home_phone = models.CharField(max_length=20, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "families"
        verbose_name = "Family"
        verbose_name_plural = "Families"
        ordering = ["name"]
        constraints = [
            # Names are unique among live families, so a trashed one doesn't
            # block reusing its name.
            models.UniqueConstraint(
                fields=["tenant", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_live_family_name_per_tenant",
            )
        ]

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.members.count()


class Tag(models.Model):
    """
    Tags for categorizing members.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Tenant (church)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="tags"
    )

    # Tag information
    name = models.CharField(max_length=50)
    color = models.CharField(
        max_length=7, default="#3B82F6", help_text="Hex color code (e.g., #3B82F6)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tags"
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ["name"]
        unique_together = ["tenant", "name"]

    def __str__(self):
        return self.name
