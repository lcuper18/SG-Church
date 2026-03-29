"""
Member models for SG Church.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.urls import reverse
import uuid


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
        ("admin", "Church Admin"),
        ("pastor", "Pastor"),
        ("treasurer", "Treasurer"),
        ("teacher", "Teacher"),
        ("volunteer", "Volunteer"),
        ("member", "Member"),
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
        return self.role in ["admin", "treasurer"]

    @property
    def can_manage_members(self):
        return self.role in ["admin", "pastor", "volunteer"]

    @property
    def can_manage_education(self):
        return self.role in ["admin", "teacher"]


class Member(models.Model):
    """
    Represents a church member.
    """

    STATUS_CHOICES = [
        ("visitor", "Visitor"),
        ("attendee", "Attendee"),
        ("member", "Member"),
        ("inactive", "Inactive"),
    ]

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]

    MARITAL_STATUS_CHOICES = [
        ("single", "Single"),
        ("married", "Married"),
        ("divorced", "Divorced"),
        ("widowed", "Widowed"),
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

    # Demographics
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    marital_status = models.CharField(
        max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True
    )

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
    photo = models.ImageField(upload_to="members/photos/", null=True, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    # Tags
    tags = models.ManyToManyField("Tag", blank=True, related_name="members")

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
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["email"]),
            models.Index(fields=["member_status"]),
            models.Index(fields=["tenant", "member_status"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_absolute_url(self):
        return reverse("member_detail", kwargs={"pk": self.pk})


class Family(models.Model):
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
        unique_together = ["tenant", "name"]

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
