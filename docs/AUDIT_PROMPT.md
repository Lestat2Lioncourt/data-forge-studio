# Prompt d'audit global DataForge Studio

*Ce prompt est a fournir a Claude pour relancer un audit complet de la solution.*

---

## Prompt

On va refaire un audit global de la solution. Le precedent compte-rendu d'audit est stocke dans `ROADMAP.md`.

Fais une analyse globale de la solution avec identification de tous les risques, des optimisations de code (code orphelin, conflits de code, factorisations possibles, etc...).

Genere un bilan les + et les - de la solution. Met a jour le fichier plan d'action `ROADMAP.MD`.

Donnes les scores sur 10 pour chaque critere suivant :
- Structure de l'application
- Qualite du code
- Gestion de la securite
- Maintenabilite
- Fiabilite
- Performance
- Extensibilite
- Documentation
- UX/UI

Pour chaque score, donne la justification et l'evolution par rapport a l'audit precedent.

### Points specifiques a analyser :

1. **Duplication de code** : identifier les blocs de code dupliques (>5 lignes identiques dans plusieurs fichiers)
2. **Gestion d'erreurs** : compter les `except Exception` generiques vs exceptions specifiques, les bare `except:`, les `except + pass`
3. **Code mort/orphelin** : methodes definies mais jamais appelees, imports inutilises, code commente
4. **Securite** : injections SQL (f-string dans requetes), credentials en dur, `eval()`/`exec()`, `subprocess shell=True`
5. **Performance** : fichiers > 500 lignes, requetes DB repetees sans cache, fuites connexions
6. **Tests** : couverture, tests casses, modules non testes
7. **i18n** : parite des cles entre langues, strings hardcodees dans le code
8. **Memoire** : ratio `.connect()` vs `.disconnect()`, presence de `closeEvent`/`cleanup`, `deleteLater()`
9. **Dependances** : deps inutilisees dans pyproject.toml (verifier imports reels)
10. **Architecture** : imports circulaires, coexistence de systemes paralleles

### Format attendu :

- Mettre a jour la section "Analyse Globale" avec les nouveaux scores et justifications
- Mettre a jour le "Bilan" (+/-) avec les nouvelles trouvailles
- Mettre a jour les "Risques Identifies" (barrer les resolus, ajouter les nouveaux)
- Mettre a jour le "Plan de Correctifs" avec les nouvelles actions
- Mettre a jour les "Statistiques du Projet"
- Mettre a jour la "Timeline" avec les derniers evenements
- Mettre a jour la "Conclusion" avec les recommandations actualisees

### Metriques a collecter :

```
- Nombre total de fichiers Python (src/)
- Nombre total de lignes de code (src/)
- Top 15 fichiers les plus volumineux
- Nombre de `except Exception` par fichier
- Nombre de bare `except:`
- Nombre de `except + pass`
- Nombre de `.connect()` vs `.disconnect()`
- Nombre de `deleteLater()`
- Nombre de cles i18n par langue
- Imports non utilises dans les dependances
- Nombre de commits depuis le dernier audit
```

---

*Derniere utilisation : 2026-02-28 (Audit #2)*
