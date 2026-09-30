"""
Tenant models for multi-tenancy.
Each tenant represents a church/organization.
"""

from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
import uuid

from core.validators import FileSizeValidator


class Tenant(models.Model):
    """
    Represents a church/tenant in the multi-tenant system.
    Isolation is row-level: every tenant-owned model has a `tenant` FK,
    filtered per-query — there is no per-tenant database schema.
    """

    DENOMINATION_CHOICES = [
        ("catholic", "Catholic"),
        ("baptist", "Baptist"),
        ("methodist", "Methodist"),
        ("presbyterian", "Presbyterian"),
        ("lutheran", "Lutheran"),
        ("anglican", "Anglican"),
        ("evangelical", "Evangelical"),
        ("pentecostal", "Pentecostal"),
        ("charismatic", "Charismatic"),
        ("nondenominational", "Non-denominational"),
        ("other", "Other"),
    ]

    # The 10 most-traded currencies internationally (BIS Triennial Survey:
    # USD, EUR, JPY, GBP, CNY, AUD, CAD, CHF, HKD, SGD) plus the currencies
    # of the Spanish-speaking countries this platform serves.
    CURRENCY_CHOICES = [
        ("USD", "Dólar estadounidense"),
        ("EUR", "Euro"),
        ("JPY", "Yen japonés"),
        ("GBP", "Libra esterlina"),
        ("CNY", "Yuan chino"),
        ("AUD", "Dólar australiano"),
        ("CAD", "Dólar canadiense"),
        ("CHF", "Franco suizo"),
        ("HKD", "Dólar de Hong Kong"),
        ("SGD", "Dólar de Singapur"),
        ("MXN", "Peso mexicano"),
        ("COP", "Peso colombiano"),
        ("ARS", "Peso argentino"),
        ("CLP", "Peso chileno"),
        ("PEN", "Sol peruano"),
        ("BRL", "Real brasileño"),
        ("CRC", "Colón costarricense"),
        ("GTQ", "Quetzal guatemalteco"),
        ("HNL", "Lempira hondureño"),
        ("NIO", "Córdoba nicaragüense"),
        ("PAB", "Balboa panameño"),
        ("DOP", "Peso dominicano"),
        ("UYU", "Peso uruguayo"),
        ("BOB", "Boliviano"),
        ("PYG", "Guaraní paraguayo"),
        ("VES", "Bolívar venezolano"),
    ]

    # Countries this platform is commonly used in — every Spanish-speaking
    # country plus major countries elsewhere. Not the full ISO 3166-1 list
    # (no django-countries dependency), but broad enough for a platform
    # meant to serve churches worldwide.
    COUNTRY_CHOICES = [
        ("AR", "Argentina"),
        ("BO", "Bolivia"),
        ("BR", "Brasil"),
        ("CA", "Canadá"),
        ("CL", "Chile"),
        ("CO", "Colombia"),
        ("CR", "Costa Rica"),
        ("CU", "Cuba"),
        ("EC", "Ecuador"),
        ("SV", "El Salvador"),
        ("ES", "España"),
        ("US", "Estados Unidos"),
        ("GQ", "Guinea Ecuatorial"),
        ("GT", "Guatemala"),
        ("HN", "Honduras"),
        ("MX", "México"),
        ("NI", "Nicaragua"),
        ("PA", "Panamá"),
        ("PY", "Paraguay"),
        ("PE", "Perú"),
        ("PR", "Puerto Rico"),
        ("DO", "República Dominicana"),
        ("UY", "Uruguay"),
        ("VE", "Venezuela"),
        ("DE", "Alemania"),
        ("AU", "Australia"),
        ("ZA", "Sudáfrica"),
        ("KR", "Corea del Sur"),
        ("CN", "China"),
        ("PH", "Filipinas"),
        ("FR", "Francia"),
        ("IN", "India"),
        ("IE", "Irlanda"),
        ("IT", "Italia"),
        ("JP", "Japón"),
        ("KE", "Kenia"),
        ("NG", "Nigeria"),
        ("NZ", "Nueva Zelanda"),
        ("NL", "Países Bajos"),
        ("PT", "Portugal"),
        ("GB", "Reino Unido"),
        ("SG", "Singapur"),
        ("SE", "Suecia"),
        ("CH", "Suiza"),
    ]

    DATE_FORMAT_CHOICES = [
        ("DD/MM/YYYY", "DD/MM/YYYY"),
        ("MM/DD/YYYY", "MM/DD/YYYY"),
        ("YYYY-MM-DD", "YYYY-MM-DD"),
    ]

    # Unique identifier
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Church information
    name = models.CharField(max_length=255, verbose_name="Church Name")
    slug = models.SlugField(max_length=63, unique=True, blank=True)
    subdomain = models.CharField(
        max_length=63,
        unique=True,
        blank=True,
        help_text='Subdomain for this church (e.g., "miiglesia" for miiglesia.sgchurch.app)',
    )

    # Church details (for onboarding)
    denomination = models.CharField(
        max_length=50, choices=DENOMINATION_CHOICES, blank=True
    )
    country = models.CharField(
        max_length=2,
        choices=COUNTRY_CHOICES,
        blank=True,
        null=True,
        help_text="ISO country code",
    )
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    logo = models.ImageField(
        upload_to="church_logos/",
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
            FileSizeValidator(max_mb=2),
        ],
    )

    # Contact information
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    # Stripe integration
    stripe_account_id = models.CharField(max_length=64, blank=True, null=True)
    stripe_onboarding_complete = models.BooleanField(default=False)

    # Configuration
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="USD")
    timezone = models.CharField(max_length=50, default="America/New_York")
    date_format = models.CharField(
        max_length=20, choices=DATE_FORMAT_CHOICES, default="DD/MM/YYYY"
    )
    enable_families = models.BooleanField(default=True)
    enable_tags = models.BooleanField(default=True)
    settings = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    onboarding_completed = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tenants"
        verbose_name = "Tenant"
        verbose_name_plural = "Tenants"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.subdomain or self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("tenant_dashboard", kwargs={"subdomain": self.subdomain})


class TenantDomain(models.Model):
    """
    Custom domains for tenants.
    Allows churches to use their own domain.
    """

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="domains")
    domain = models.CharField(max_length=253, unique=True)
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tenant_domains"
        verbose_name = "Tenant Domain"
        verbose_name_plural = "Tenant Domains"
        ordering = ["-is_primary", "domain"]

    def __str__(self):
        return f"{self.domain} ({self.tenant.name})"
