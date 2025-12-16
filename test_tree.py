"""Test script pour vérifier la visibilité du tree view."""
import sys
from PySide6.QtWidgets import QApplication
from src.dataforge_studio.ui.managers.database_manager import DatabaseManager

app = QApplication(sys.argv)

# Créer le DatabaseManager
dm = DatabaseManager()

# Vérifier le contenu
print(f"=== DATABASE MANAGER DEBUG ===")
print(f"Schema tree items: {dm.schema_tree.topLevelItemCount()}")
print(f"Schema tree visible: {dm.schema_tree.isVisible()}")
print(f"Schema tree width: {dm.schema_tree.width()}")
print(f"Schema tree height: {dm.schema_tree.height()}")

if dm.schema_tree.topLevelItemCount() > 0:
    item = dm.schema_tree.topLevelItem(0)
    print(f"First item exists: Yes")
    print(f"First item child count: {item.childCount()}")
    print(f"First item is hidden: {item.isHidden()}")
    # Essayer d'expand l'item
    item.setExpanded(True)

# Afficher le widget
dm.show()
dm.resize(1200, 800)

print(f"\nFenêtre affichée. Vérifiez si le tree est visible dans le left panel.")
print(f"Si le tree est vide, vérifiez les couleurs du thème.")

sys.exit(app.exec())
