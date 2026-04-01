# 08 - Personnaliser l'environnement

> **Situation** : Vous passez vos journees dans DataForge Studio et vous voulez adapter l'interface a vos preferences visuelles et fonctionnelles.

---

## Changer de theme

DataForge Studio propose **4 themes integres** :

| Theme | Description |
|-------|-------------|
| **Sombre (Minimal)** | Theme sombre moderne, par defaut. Ideal pour le travail prolonge |
| **Clair (Minimal)** | Theme clair minimaliste pour les environnements lumineux |
| **Theme Sombre** | Theme sombre complet avec palette etendue |
| **Theme Clair** | Theme clair complet avec palette etendue |

### Appliquer un theme

1. Allez dans **Options > Preferences**
2. Dans l'arbre de gauche, selectionnez **Themes**
3. Cliquez sur le theme souhaite
4. Le changement est **immediat** -- pas besoin de redemarrer

Le theme s'applique a l'ensemble de l'interface : barre laterale, arbres, grilles, editeur SQL, dialogues et fenetres detachees.

[Screenshot: Meme ecran en theme sombre et en theme clair cote a cote]

---

## Changer la langue

L'interface est disponible en **francais** et en **anglais** :

1. Allez dans **Options > Preferences**
2. Dans l'arbre de gauche, selectionnez **Langue**
3. Choisissez **Francais** ou **English**
4. Le changement est immediat

La langue affecte tous les menus, boutons, labels, messages d'erreur et notifications.

---

## Preferences generales

Les preferences sont accessibles via **Options > Preferences > General**. Chaque parametre est un noeud dans l'arbre, avec un panneau d'edition a droite.

### Parametres disponibles

| Parametre | Type | Description |
|-----------|------|-------------|
| **sql_format_style** | Choix | Style de formatage SQL par defaut (expanded, compact, comma_first, aligned) |
| **query_column_names** | Texte | Noms de colonnes declenchant l'option "Edit Query" (par defaut : `query, requete`) |
| **objects_borders** | Booleen | Afficher les contours des widgets (mode debug) |
| **export_language** | Choix | Langage d'export par defaut (Python, R, etc.) |

Pour modifier un parametre :

1. Cliquez sur le parametre dans l'arbre
2. Modifiez la valeur dans le panneau droit
3. Cliquez sur **Appliquer**

[Screenshot: Panneau de preferences avec un parametre selectionne]

---

## Disposition de l'interface

### Panneau laterale epinglable

Le panneau lateral (arbre de navigation) est **epinglable** :

- **Epingle** (mode par defaut) : le panneau reste visible en permanence
- **Non epingle** : le panneau se replie automatiquement quand il perd le focus, liberant de l'espace pour le contenu principal

Basculez entre les deux modes via le bouton **pin** dans la barre du panneau.

### Redimensionner les zones

Les separateurs entre les panneaux (arbre / contenu, editeur / resultats) sont **deplacables** a la souris. Faites glisser la barre separatrice pour ajuster la repartition de l'espace.

### Split view dans les onglets de requete

Chaque onglet de requete peut basculer entre :

- **Mode empile** (par defaut) : editeur au-dessus, resultats en dessous
- **Mode cote a cote** : editeur a gauche, resultats a droite

Utilisez le bouton **Split Toggle** dans la barre d'outils de l'onglet.

---

## Fenetre frameless et barre de titre personnalisee

DataForge Studio utilise une **fenetre frameless** avec une barre de titre personnalisee integree au theme. Cette barre contient :

- Le titre de l'application
- Les boutons standard (minimiser, maximiser, fermer)
- Le bouton de split toggle (dans certaines vues)

La fenetre supporte le **redimensionnement par les bords** et le **deplacement** via la barre de titre.

---

## Creer un raccourci bureau

Pour un acces rapide sans passer par le terminal :

```bash
uv run python scripts/create_shortcut.py
```

- **Windows** : cree un fichier `.lnk` sur le bureau avec l'icone de l'application
- **macOS** : cree un bundle `.app` (a glisser dans le Dock)
- **Linux** : cree une entree `.desktop` dans le menu des applications

---

## Verifier et installer les mises a jour

### Verification automatique

Au demarrage, DataForge Studio verifie s'il existe une version plus recente sur GitHub. Si c'est le cas :

- Un message s'affiche dans la **barre de statut** en bas de la fenetre
- Vous pouvez choisir de mettre a jour immediatement, de voir les details sur GitHub, ou de reporter au lendemain

### Mise a jour

1. Cliquez sur la notification de mise a jour
2. Choisissez **"Update on Quit"** : la mise a jour s'executera a la fermeture de l'application
3. Ou manuellement :

   ```bash
   git pull
   uv sync
   ```

---

## Astuce

- Le theme sombre est recommande pour le travail prolonge sur ecran. Si vous alternez entre interieur et exterieur, le theme clair est plus lisible en pleine lumiere.
- Apres un changement de theme, les fenetres detachees (onglets de requete, aide) s'adaptent automatiquement -- pas besoin de les fermer et rouvrir.
- Le parametre `objects_borders` est utile uniquement pour le debogage de l'interface. En usage normal, laissez-le desactive.

---

## Ce qui se passe en coulisse

- Les themes sont definis dans un fichier JSON (`themes.json`) avec une palette de couleurs structuree : base, texte, interactif, boutons, data, etc.
- Le systeme de theming utilise `ThemeBridge`, un singleton qui genere les feuilles de style QSS (Qt Style Sheets) a partir de la palette de couleurs.
- Les icones SVG sont **recolorees dynamiquement** via remplacement de texte dans le SVG source, adaptant les couleurs au theme actif.
- Les preferences sont stockees dans la table `user_preferences` de la base de configuration. Le systeme est **data-driven** : ajouter un parametre ne necessite aucun code d'interface supplementaire.
- La verification de mise a jour utilise un **cooldown de 24 heures** : apres avoir reporte une mise a jour, la notification ne reapparait que le lendemain.

---

[<< Acceder a un serveur FTP](07-ftp-access.md) | [Suivant : Reference rapide >>](09-reference.md)
