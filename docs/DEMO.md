# Application de référence — CodexShop

CodexShop est la papeterie livrée dans `demo/`. Elle sert de parcours de
référence pour vérifier la création d'une boutique, une commande et l'évolution
du schéma avec conservation des données. Sa spécification, son interface et
ses photos sont versionnées ; le backend et le contrat sont recompilés.

Ce guide décrit le projet actuel. Les vérifications automatisées ci-dessous
ne constituent pas un retour d'utilisateurs réels.

## 1. Préparer une copie de travail

Depuis la racine du dépôt, avec monl installé dans votre environnement Python
(`pip install -e '.[dev]'` pour disposer aussi des outils de vérification) :

```bash
projet_demo="$(mktemp -d /tmp/codexshop-XXXXXX)"
cp demo/spec.ml "$projet_demo/"
cp -r demo/frontend demo/assets "$projet_demo/"
monl compile "$projet_demo/spec.ml" --output "$projet_demo"
monl run "$projet_demo" --check
monl run "$projet_demo"
```

Conservez ce terminal et la valeur de `projet_demo` pour la suite. Pour garder
la boutique durablement, déplacez le dossier temporaire vers votre espace de
projets après avoir arrêté le serveur.

Ouvrez `http://127.0.0.1:8000/site` pour la boutique et
`http://127.0.0.1:8000/docs` pour explorer l'API générée.
La copie contient sa propre `spec.ml` : une évolution ne modifie donc pas
l'exemple du dépôt. Compiler directement `demo/spec.ml` vers un autre dossier
conserverait une référence à la spec d'origine.

## 2. Passer une commande

Dans une copie neuve, le catalogue contient douze produits. Effectuez ce
parcours dans l'interface :

1. Ajoutez deux **Carnets Lin Ivoire**, à 24 € pièce, au panier.
2. Créez un compte client avec une adresse e-mail comme **identifiant**,
   un mot de passe d'au moins huit caractères et une fiche de livraison complète.
   Utilisez des données fictives pour cette démonstration locale.
3. Confirmez la commande et retrouvez-la dans votre compte.
4. Vérifiez le total de **48 €**, la référence `CMD-…`, la date de création
   et le stock du produit, passé de **18 à 16**.

Le compte d'authentification et la fiche de livraison sont deux objets
distincts. L'API refuse de créer une commande sans fiche, avec le statut 409.
L'interface guide la création de cette fiche.

Le total et les sous-totaux sont calculés par le serveur. Pour reproduire les
appels depuis Swagger, utilisez `/register`, puis `/login`, et collez le
`access_token` dans **Authorize**. Après création de la fiche `/customer`,
créez une commande avec `POST /order` :

```json
{"status": "À confirmer"}
```

Ajoutez ensuite sa ligne avec `POST /ligneorder` :

```json
{"order_id": 1, "product_id": 1, "quantite": 2}
```

Remplacez les identifiants par ceux renvoyés par votre API.
N'envoyez ni `total`, ni `sousTotal`, ni référence de commande.

Sans `STRIPE_SECRET_KEY`, la demande de paiement répond **503** en nommant la
configuration manquante. C'est la limite du parcours local : aucune somme n'est
encaissée. Les lignes réservent déjà du stock ; l'annulation le restitue.
Le paiement auprès du prestataire et l'expédition après règlement nécessitent
une validation séparée en environnement de test du prestataire.

## 3. Faire évoluer une commande sans la perdre

Arrêtez le serveur avec `Ctrl+C`. Dans **la copie** `$projet_demo/spec.ml`,
ajoutez une ligne `    note: Text` juste après `entity Order`, en conservant
tous les champs existants.

```bash
monl run "$projet_demo" --check
monl diff "$projet_demo"
monl update "$projet_demo"
```

La première commande doit refuser la spec non recompilée. `diff` permet de lire
le changement prévu, puis `update` régénère le backend et le contrat et produit
`$projet_demo/docs/FRONTEND_UPDATE_PROMPT.md`, qui mentionne `Order.note`.
La base `app.db`, les comptes, le secret JWT et les fichiers frontend sont conservés.

Pour vérifier la migration côté API avant d'adapter l'interface, démarrez le
backend depuis le même terminal :

```bash
(cd "$projet_demo" && python -m uvicorn app:app --host 127.0.0.1 --port 8000)
```

Connectez-vous dans Swagger avec le même compte. La commande existante doit
garder son identifiant, sa référence, sa date et son total ; `note` vaut `null`.
Le stock doit rester à 16 et le catalogue à douze produits : redémarrer ne doit
ni restituer le stock réservé ni dupliquer les données initiales.

Avec `PUT /order/{id}`, envoyez :

```json
{"status": "À confirmer", "note": "Livrer le matin"}
```

Relisez la commande pour vérifier la note. Puis envoyez deux fois :

```json
{"status": "Annulée", "note": "Livrer le matin"}
```

Le stock revient à 18 et y reste. Arrêtez ce serveur après vérification.

Cette évolution change aussi le formulaire attendu : `note` doit être envoyé
dans les nouvelles créations et modifications. `update` ne réécrit pas
l'interface. Utilisez le brief d'évolution pour ajouter sa saisie et son
affichage au frontend, puis rejouez `monl run "$projet_demo" --check` et le
parcours de commande. Le test de migration ci-dessous vérifie l'API évoluée ;
il ne prétend pas adapter ou valider ce nouveau formulaire.

## 4. Rejouer les vérifications automatiques

Depuis la racine du dépôt :

```bash
python -m pytest tests/test_demo.py tests/test_demo_cycle.py -q
```

Ces tests nécessitent de pouvoir ouvrir des ports locaux. Le smoke test de
l'interface utilise Node et jsdom ; les diagnostics indiquent leur disponibilité.

| Vérification | Preuve automatisée |
|---|---|
| Spec, backend, contrat et interface cohérents | `test_demo.py` |
| Interface autonome et appels API au démarrage | `test_demo.py` |
| Fiche obligatoire, montant calculé et stock décrémenté | `test_demo_cycle.py` |
| Commande invisible depuis un autre compte client | `test_demo_cycle.py` |
| Stock insuffisant refusé sans changement partiel | `test_demo_cycle.py` |
| Paiement indisponible explicitement sans clé | `test_demo_cycle.py` |
| Compte, jeton, commande et stock conservés après update | `test_demo_cycle.py` |
| Nouveau champ utilisable et annulation sans double restitution | `test_demo_cycle.py` |

Les tests travaillent dans des dossiers temporaires. Ils n'appellent aucun
prestataire de paiement et ne modifient pas votre boutique de travail.

## 5. Observer un premier utilisateur

Faites essayer la copie initiale à une personne qui ne connaît pas Monl. Donnez
un objectif (« commander deux carnets puis retrouver la commande ») et observez
les étapes avant de fournir des explications. Pour le parcours exploitant,
faites suivre les sections de préparation et d'évolution à un développeur.

Pour chaque session, relevez :

| Tâche | Réussie sans aide ? | Durée | Blocage ou message observé |
|---|---|---|---|
| Lancer la boutique depuis le guide | À renseigner | À mesurer | À renseigner |
| Créer un compte et compléter la livraison | À renseigner | À mesurer | À renseigner |
| Commander et retrouver référence et montant | À renseigner | À mesurer | À renseigner |
| Comprendre l'indisponibilité du paiement local | À renseigner | À mesurer | À renseigner |
| Mettre à jour la spec et retrouver la commande | À renseigner | À mesurer | À renseigner |

Notez la version de Monl et les étapes exactes de reproduction, sans mot de
passe ni jeton. Corrigez en priorité les blocages qui empêchent de terminer une
tâche ou font perdre confiance dans le montant, le stock ou la conservation des
données. Aucun résultat utilisateur n'est encore consigné dans ce guide.
