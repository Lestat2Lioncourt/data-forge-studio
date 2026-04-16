"""Audit des icônes : liste les PNG de base/ sans équivalent SVG."""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ICONS_BASE = Path(__file__).parent.parent / "ui" / "assets" / "icons" / "base"


def find_missing_svgs(base_dir: Path = ICONS_BASE) -> list[str]:
    """Return PNG filenames in base_dir that have no .svg sibling."""
    if not base_dir.is_dir():
        return []
    svgs = {p.stem for p in base_dir.glob("*.svg")}
    return sorted(p.name for p in base_dir.glob("*.png") if p.stem not in svgs)


def audit_icons(base_dir: Path = ICONS_BASE) -> list[str]:
    """Log a consolidated warning listing PNG icons missing an SVG counterpart."""
    missing = find_missing_svgs(base_dir)
    if missing:
        logger.warning(
            "Icon audit: %d PNG sans SVG dans %s — conversion a demander : %s",
            len(missing), base_dir.name, ", ".join(missing),
        )
    return missing
