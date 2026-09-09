# CARTE — monl-compiler

Une page pour comprendre le projet en dix minutes. Tout ce qui est vérifiable
ici est rejoué par `scripts/verifier_carte.py`, que la CI exécute : un module
déplacé ou un décompte de routes qui bouge font échouer la construction. Le
*pourquoi* de chaque décision vit dans `docs/design_decisions.md`.

## La phrase

monl compile une spécification déclarative (`.ml`) en backend FastAPI complet :
base de données, API REST, authentification, contrôle d'accès, plus un contrat
que le frontend devra respecter. La spec est l'unique source de vérité, et
aucune IA n'écrit le backend.

## Faire tourner

```bash
pip install -e ".[dev]"
mkdir -p /tmp/demo
cp exemples/01_portfolio.ml /tmp/demo/spec.ml
cp -r exemples/assets /tmp/demo/assets   # asset déclaré mais absent = échec, exprès
monl compile /tmp/demo/spec.ml --output /tmp/demo
cd /tmp/demo && python -m uvicorn app:app --port 8000
curl -s localhost:8000/health            # {"status":"ok"}
```

`monl init` ouvre à la place le dialogue guidé — sans IA — qui rédige la spec.
Les onze autres sous-commandes couvrent le cycle de vie : `compile`, `run`,
`update`, `diff`, `usage`, `migrate`, `frontend`, `retouche`, `assets`,
`content` et `import`.

## La preuve

Mesuré le 2026-09-09 sur `de92ea1`, avec le venv du dépôt :

| Quoi | Résultat |
|---|---|
| Suite de tests | 1532 passés, 16 sautés, **1 en échec** — voir « Là où ça fait mal » |
| `exemples/01_portfolio.ml` | 71 lignes de spec → 1207 lignes d'`app.py` + 60 de SQL |
| Backend produit | 11 routes exposées, `/health` répond `{"status":"ok"}` |
| Déterminisme | deux compilations de la même spec : artefacts identiques au bit près |

Reproduire : `python scripts/verifier_carte.py --preuve` (~40 s).

## La forme

Un seul chemin traverse le produit, sans branche cachée :

```
spec.ml → parser (lark) → AST → audit statique → plans IR typés → générateur
        → app.py + schema.sql + frontend_contract.json + monl.json (sceau sha256)
```

| Étape | Où |
|---|---|
| Lecture du DSL | `src/monl/parser/` |
| Audit de sécurité statique | `src/monl/ast_validator/` |
| Représentation intermédiaire | `src/monl/ir.py`, `src/monl/planning.py` |
| Émission du backend | `src/monl/generator/` (une couche par module) |
| Contrat pour le frontend | `src/monl/frontend_contract/` |

**Où vit l'état :** nulle part dans le compilateur, déterministe et sans mémoire.
Il vit dans le projet compilé (SQLite, ou PostgreSQL via `MONL_DATABASE_URL`) et
dans son `monl.json`, qui scelle spec, contrat et fichiers produits par sha256.

**Second paquet :** `src/monl_platform/` expose le compilateur en web, API et
serveur MCP (comptes, projets, quotas). Il appelle le compilateur ; le
compilateur l'ignore, et `tests/test_architecture.py` fait échouer la suite si
cette frontière s'inverse.

## Les frontières

Ce que le projet ne fait pas, et ne cherche pas à faire :

- **L'IA n'écrit jamais le backend**, ni les permissions, ni la logique métier :
  elle n'intervient qu'au bout, pour le frontend, contre un contrat vérifié.
- **Aucun langage de requête n'est exposé** : filtrage et tri sont fermés,
  décidés côté serveur.
- **Pas de panneau d'administration web** — en ligne de commande uniquement :
  un panneau web serait la cible dont une seule faille donne tous les comptes.
- **Le code `custom` n'est pas exécuté** : le générateur y écrit des coquilles
  vides que l'auteur du projet remplit (`src/monl/generator/sandbox.py`).
- **Pas de vérification d'adresse à l'inscription** : monl sait envoyer, mais
  que faire d'un compte non confirmé est une décision de parcours non prise.

## Les décisions qu'on ne rediscute pas

- **La spec est l'unique source de vérité.** `app.py` et `schema.sql` ne se
  modifient jamais à la main ; `monl.json` les scelle pour que la triche se voie.
- **Le générateur est déterministe** : même spec, mêmes octets. C'est ce qui
  rend une régression lisible dans un diff.
- **La CI échoue au lieu de sauter.** Un test sauté ne dit pas « rien à
  vérifier ici », il dit « je n'ai pas vérifié » — d'où `-rs`, qui nomme chaque
  saut et son motif.
- **La couverture est mesurée séparément** (compilateur, plateforme), plancher
  90 % chacun : une moyenne unique avait laissé la barrière tomber en silence.

## Là où ça fait mal

- **Le générateur construit le code par concaténation de chaînes.** Le
  remplacement par templates/AST avec golden-files est le chantier n° 2 vers la
  GA ; le découpage en modules l'a préparé, personne ne l'a commencé.
- **La documentation dérive plus vite qu'elle ne se relit.** `docs/BETA.md`
  annonce encore le pooling de connexions comme « reste ouvert » alors que
  `cd2a56e` l'a livré (`src/monl/generator/runtime_pool.py`). Cette page pèse
  5 Ko contre 285 Ko pour CLAUDE, CODEBASE_AUDIT, CHANGELOG et README réunis.
- **`pytest tests/` n'est pas vert sans `libpq`.**
  `test_pool_de_connexions.py::test_repli_sans_psycopg_pool…` importe le backend
  produit dans un sous-processus sans la garde `ImportError` qu'a son voisin
  `tests/test_postgresql.py` : il échoue là où les autres sautent en le disant.
- **La suite dure six à douze minutes** parce qu'elle démarre de vrais serveurs.
  Prix assumé de la règle « prouvé par exécution », pas un défaut à corriger.
- **Restent non traités :** migrations descendantes destructives, secrets
  délégués (Vault, SSM), gouvernance du DSL, audit externe, modèle de menace.

## Où on en est

Version 0.9.0-beta.8, `main` sur `de92ea1` — dernier chantier fusionné : la
consolidation du compilateur et de ses plans IR (#58). **Prochaine étape :** le
générateur par templates, chantier n° 2 de `docs/BETA.md`.
