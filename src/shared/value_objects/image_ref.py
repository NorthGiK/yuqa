"""Reference to an image stored outside the database."""

from dataclasses import dataclass

from src.shared.errors import ValidationError


@dataclass(frozen=True, slots=True)
class ImageRef:
    """Minimal image reference used by card templates."""

    storage_key: str
    content_type: str = "image/png"
    original_name: str | None = None

    def __post_init__(self) -> None:
        if not self.storage_key:
            raise ValidationError("storage_key must not be empty")
        if not self.content_type:
            raise ValidationError("content_type must not be empty")
