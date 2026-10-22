"""Project settings: a YAML file validated with pydantic.

The path defaults to ``config/settings.yaml`` at the repository root and can be overridden with
the ``SCOUTING_CONFIG`` environment variable.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "settings.yaml"
ENV_VAR = "SCOUTING_CONFIG"

_COMPETITION_CODE = re.compile(r"^[A-Z0-9]{2,6}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DataPaths(_Strict):
    raw_dir: Path = Path("data/raw")
    processed_dir: Path = Path("data/processed")


class TransfermarktSource(_Strict):
    url: str
    filename: str = "transfermarkt-datasets.duckdb"
    sha256: str | None = None
    license: str
    attribution: str

    @field_validator("sha256")
    @classmethod
    def _valid_sha256(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.lower()
        if not _SHA256.match(value):
            raise ValueError("sha256 must be 64 hexadecimal characters")
        return value


class Sources(_Strict):
    transfermarkt: TransfermarktSource


class Scope(_Strict):
    focus_competition: str
    competitions: dict[str, str] = Field(min_length=1)
    seasons: list[int] = Field(min_length=1)

    @field_validator("competitions")
    @classmethod
    def _valid_codes(cls, value: dict[str, str]) -> dict[str, str]:
        bad = [code for code in value if not _COMPETITION_CODE.match(code)]
        if bad:
            raise ValueError(f"invalid competition codes: {bad}")
        return value

    @field_validator("seasons")
    @classmethod
    def _valid_seasons(cls, value: list[int]) -> list[int]:
        if any(season < 1990 or season > 2100 for season in value):
            raise ValueError("seasons must be start years, e.g. 2025 for 2025/26")
        return sorted(set(value))

    @model_validator(mode="after")
    def _focus_in_scope(self) -> Scope:
        if self.focus_competition not in self.competitions:
            raise ValueError(
                f"focus_competition '{self.focus_competition}' is not listed in competitions"
            )
        return self

    @property
    def competition_ids(self) -> list[str]:
        """Competition codes in the order they are declared."""
        return list(self.competitions)


class ConfidenceMinutes(_Strict):
    """Minutes needed for a medium / high confidence badge (below ``medium`` = low)."""

    medium: int = Field(900, gt=0)
    high: int = Field(1800, gt=0)

    @model_validator(mode="after")
    def _ordered(self) -> ConfidenceMinutes:
        if self.high <= self.medium:
            raise ValueError("confidence_minutes.high must be greater than medium")
        return self


class Analysis(_Strict):
    min_minutes: int = Field(900, ge=0)
    confidence_minutes: ConfidenceMinutes = ConfidenceMinutes()
    young_age_max: float = Field(23, gt=14, lt=40)


class Settings(_Strict):
    data: DataPaths = DataPaths()
    sources: Sources
    scope: Scope
    analysis: Analysis = Analysis()
    root: Path = REPO_ROOT

    def resolve(self, path: Path) -> Path:
        """Return ``path`` as an absolute path, relative paths being anchored at ``root``."""
        return path if path.is_absolute() else self.root / path

    @property
    def raw_dir(self) -> Path:
        return self.resolve(self.data.raw_dir)

    @property
    def processed_dir(self) -> Path:
        return self.resolve(self.data.processed_dir)


class ConfigError(ValueError):
    """Raised when the settings file is missing or invalid, with a readable message."""


def load_settings(path: str | Path | None = None) -> Settings:
    """Load and validate the settings file.

    Resolution order: explicit ``path``, then ``$SCOUTING_CONFIG``, then the default file.
    """
    config_path = Path(path or os.environ.get(ENV_VAR) or DEFAULT_CONFIG_PATH)
    if not config_path.exists():
        raise ConfigError(f"Settings file not found: {config_path}")

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Settings file is not valid YAML ({config_path}): {exc}") from exc

    raw.setdefault("root", str(config_path.resolve().parents[1]))
    try:
        return Settings.model_validate(raw)
    except ValueError as exc:
        raise ConfigError(f"Invalid settings in {config_path}:\n{exc}") from exc
