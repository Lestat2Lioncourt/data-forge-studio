"""Lance l'audit des icones a la demande (PNG sans SVG dans base/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dataforge_studio.utils.icon_audit import find_missing_svgs

missing = find_missing_svgs()
if not missing:
    print("OK : tous les PNG ont un SVG correspondant.")
else:
    print(f"{len(missing)} PNG sans SVG :")
    for name in missing:
        print(f"  - {name}")
