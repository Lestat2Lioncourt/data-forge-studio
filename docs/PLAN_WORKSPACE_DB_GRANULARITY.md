# Plan — Modèle workspace à granularité base de données

> **Statut** : étapes 1-6 implémentées (code). Reste : validation manuelle dans l'app
> (cas ORBIT-BDD, lier-toutes-les-bases, décochage, SQLite, hors-ligne).
> **Origine** : un serveur lié à un workspace dupliquait les bases déjà liées
> individuellement (lien serveur `database_name=''` + liens base-précise pour la
> même connexion). Décision : modèle uniforme à la granularité base.

## 0. Sémantique cible

- Un lien workspace = **toujours une base précise**, affichée sous un nœud serveur.
- « Lier le serveur » = action de confort créant **un lien par base** (dédup contre
  l'existant), en **snapshot** (décision A — pas de suivi dynamique des bases ajoutées
  ensuite).
- Le sentinelle `database_name=""` devient **legacy**, normalisé paresseusement (F).
- Bases mono-connexion (SQLite / Access / PostgreSQL) : **pas de niveau serveur** (E).

## Décisions validées

| Réf | Décision |
|-----|----------|
| A | « Lier le serveur » = snapshot des bases à l'instant T. Les bases ajoutées plus tard n'apparaissent pas automatiquement. |
| B | Lier un serveur exige une connexion vivante (pour énumérer les bases). |
| C | L'item serveur (Resources, multi-bases) n'est plus une checkbox mais une **action** « Lier toutes les bases ». Décochage **base par base**. |
| D | Action « Retirer du workspace » sur un nœud base **dans l'arbre workspace**. |
| E | Bases mono-connexion (SQLite/Access/PostgreSQL) : nœud connexion = nœud base, pas de regroupement serveur. |
| F | Normalisation **paresseuse** des liens `''` legacy au chargement (pas de migration one-shot, pas de connexion forcée au démarrage). |

---

## 1. Helper de classification — `utils/db_capabilities.py` (nouveau)

```python
MULTI_DATABASE_TYPES = {"sqlserver", "mysql", "mariadb"}

def is_multi_database_server(db_type: str) -> bool:
    """True si une connexion expose plusieurs bases sur une même connexion.
    PostgreSQL se connecte à UNE base → traité mono-connexion."""
    return (db_type or "").lower() in MULTI_DATABASE_TYPES
```

Source unique de vérité, utilisée par le menu Resources et l'arbre workspace.

## 2. Repository / config_db

`project_repository.py` :
- `add_database` / `remove_database` : inchangés (gèrent déjà `database_name`).
- **Nouvelle `replace_server_link_with_databases(project_id, database_id, db_names)`**
  (transactionnelle) :
  1. `INSERT OR IGNORE` un lien spécifique par `db_name` (la PK
     `(project_id, database_id, database_name)` déduplique) ;
  2. supprime la ligne `''` de cette connexion dans ce workspace.

`config_db.py` : exposer `replace_server_link_with_databases`.

## 3. Menu Resources — action « lier toutes les bases » (C)

`database/workspace_mixin.py · _build_workspace_submenu(db_id, database_name)` :
- **database_name fourni** (clic base) → checkbox toggle, inchangé.
- **database_name None** (clic serveur) :
  - mono (`not is_multi_database_server`) → checkbox toggle, inchangé.
  - multi → **action** par workspace « Lier toutes les bases à *{ws}* » →
    `_link_all_databases_to_workspace(ws_id, db_id)`.

`_link_all_databases_to_workspace(workspace_id, db_id)` :
1. connexion (`connections.get(db_id)` sinon `_create_connection` synchrone + WaitCursor) — B ;
2. échec → `DialogHelper.warning` (VPN ?) et abandon ;
3. `loader.get_databases()` ;
4. `config_db.replace_server_link_with_databases(...)` ;
5. `workspace_manager.refresh_workspace(workspace_id)`.

## 4. Arbre workspace — regroupement par serveur

`workspace_manager.py · _load_workspace_resources` :
- normalisation à la volée (§5) des `''` multi **déjà connectés** ;
- grouper par `connection.id` :
  - **multi** → nœud `type="server_group"` (nom = connexion, métadonnée `config`),
    enfants = un nœud `type="database"` par base liée (`database_name` réel, dummy child).
    Conteneur pur, aucune logique de chargement.
  - **mono** → un seul nœud `type="database"` directement sous la catégorie.
- `''` multi **non normalisé** (hors-ligne) → nœud legacy `type="database"` avec dummy
  (fallback serveur-complet existant) ; normalisation au 1ᵉʳ déploiement réussi.

## 5. Normalisation paresseuse des `''` legacy (F)

Règle : **jamais de connexion forcée**.
- Au chargement : si une entrée `''` multi a une connexion **déjà ouverte**, normaliser
  silencieusement avant rendu → s'affiche groupé.
- Sinon : rendre le nœud legacy ; au **1ᵉʳ déploiement réussi**, normaliser puis
  `refresh_workspace`. Échec → garder `''`, fallback, réessai plus tard.
- Dédup intégrée (cas `ORBIT-BDD` : `''` + 4 bases → un lien par base, `''` supprimé).
- SQLite/Access : aucune normalisation.

## 6. Retrait par base depuis le workspace (D) — correctif

`_remove_resource_from_workspace` : passer `data.get("database_name")` à
`remove_database_from_workspace` (sinon seul le lien `''` est supprimé). Étendre le
nettoyage des nœuds vides au niveau `server_group`.

## 7. i18n (en/fr)

- `ws_link_all_databases` = « Lier toutes les bases à {workspace} »
- `ws_link_all_failed` = « Impossible d'énumérer les bases (connexion/VPN ?) »
- `ws_link_all_done` = « {count} base(s) liée(s) à {workspace} »

## 8. Données existantes & compat

- Aucune migration de schéma.
- Liens `''` actuels (MariaDB-TEST, ORBIT-BDD) normalisés à la 1ʳᵉ connexion ;
  les 2 SQLite restent tels quels.
- Export/Import : déjà basés sur `database_name`, compatibles.

## 9. Tests

- Unitaire `replace_server_link_with_databases` : dédup (ORBIT-BDD), suppression `''`,
  idempotence.
- Unitaire `is_multi_database_server`.
- Manuel : (a) lier serveur multi ; (b) décocher 2 bases ; (c) lier 1 base ;
  (d) SQLite ; (e) re-lier serveur après ajout ; (f) hors-ligne → fallback puis normalisation.

## 10. Ordre d'implémentation

1. ✅ **Helper `is_multi_database_server` + `replace_server_link_with_databases` (+ tests).**
2. ✅ Correctif retrait D (`_remove_resource_from_workspace` passe `database_name`).
3. ✅ Rendu groupé `_load_workspace_resources` (+ `server_group`, helpers `_populate_workspace_databases` etc.).
4. ✅ Action « lier toutes les bases » (`_build_workspace_submenu` + `_link_all_databases_to_workspace`).
5. ✅ Normalisation paresseuse F (`_normalize_connected_server_links` au chargement + `_normalize_server_link_after_load` à l'expansion).
6. ✅ i18n (`ws_link_all_*`) + nettoyage des `server_group` vides.

### Reste à faire
- Validation manuelle dans l'app (les 6 scénarios du §9).

### Fait en complément
- Menu contextuel `server_group` : « Remove server (all databases) from Workspace »
  (`remove_all_databases` repo + `_remove_server_group_from_workspace`).
- Robustesse `_enumerate_server_databases` : check de joignabilité + capture des
  exceptions de connexion (plus de crash sur serveur en timeout).
- Combo base de l'onglet requête : branche `mysql` ajoutée (`_load_databases` +
  `_on_database_changed`) — listait le serveur au lieu des bases.
- SQL Server moindre privilège : `get_databases()` et la combo base filtrent via
  `HAS_DBACCESS(name) = 1` → un compte restreint ne voit/lie que ses bases
  autorisées (plus d'erreurs sur les bases interdites).

Chaque étape est livrable/testable indépendamment ; 1-2-3 donnent déjà un workspace
cohérent même avant l'action de confort.
