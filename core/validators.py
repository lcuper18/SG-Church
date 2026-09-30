"""
Shared file-upload validators for SG Church.
"""

from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat
from django.utils.deconstruct import deconstructible


@deconstructible
class FileSizeValidator:
    """
    Rejects files larger than max_mb megabytes. A class (not a closure) so
    Django can serialize it into migrations, same convention as the built-in
    validators (e.g. RegexValidator).
    """

    def __init__(self, max_mb):
        self.max_mb = max_mb

    def __call__(self, file):
        max_bytes = self.max_mb * 1024 * 1024
        if file.size > max_bytes:
            raise ValidationError(
                f"El archivo pesa {filesizeformat(file.size)}; el máximo "
                f"permitido es {filesizeformat(max_bytes)}."
            )

    def __eq__(self, other):
        return isinstance(other, FileSizeValidator) and self.max_mb == other.max_mb
