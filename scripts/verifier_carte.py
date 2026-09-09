"""Rejoue ce que CARTE.md affirme, et échoue dès qu'une affirmation a vieilli.

Une carte de projet est DESCRIPTIVE : contrairement à une spec `.ml`, qui
produit le code et ne peut donc pas mentir, elle est écrite après lui et dérive
en silence. `docs/BETA.md` en donne l'exemple vivant : il annonçait encore le
pooling de connexions comme « reste ouvert » alors que le commit cd2a56e
l'avait livré. Ce script est la contrepartie de cette faiblesse — il transforme
chaque affirmation vérifiable de la carte en assertion exécutée.

Deux modes :

  (défaut)   contrôles à coût nul (~5 s) : plafond de lignes, sections
             obligatoires, existence de chaque chemin cité, sous-commandes
             réellement offertes par la CLI, nombre de tests collectés,
             ancienneté de la preuve.

  --preuve   rejoue en plus le chemin principal du produit (~40 s) : compile
             deux fois la même spec pour prouver le déterminisme octet par
             octet, démarre le backend produit et compte ses routes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

# `monl --help` colore sa sortie même quand elle est capturée, sans TTY. Sans
# ce nettoyage, le bloc `{init,compile,…}` ne se laisse pas lire et le contrôle
# des sous-commandes en surplus serait sauté SANS le dire — la forme d'angle
# mort que ce dépôt refuse (point 140).
ANSI = re.compile(r"\x1b\[[0-9;]*m")

# Un motif entre accents graves n'est traité comme un chemin du dépôt que si son
# premier segment est un dossier de premier niveau. Sans cette borne, `/health`
# ou `application/json` déclencheraient de fausses alertes, et une carte qui
# crie au loup ne se lit plus.
DOSSIERS_RACINE = {
    "src", "tests", "docs", "exemples", "demo", "scripts",
    "outils", "skills", "env", ".github",
}


class Echec(Exception):
    """Une affirmation de la carte ne tient plus."""


def _lire_config(chemin: Path) -> dict:
    return json.loads(chemin.read_text(encoding="utf-8"))


def _sortie(commande: list[str], *, cwd: Path | None = None) -> str:
    resultat = subprocess.run(
        commande, cwd=cwd or RACINE, capture_output=True, text=True, timeout=300
    )
    if resultat.returncode != 0:
        raise Echec(f"{' '.join(commande)} a échoué :\n{resultat.stderr.strip()[:800]}")
    return resultat.stdout


# --------------------------------------------------------------------------
# Contrôles rapides
# --------------------------------------------------------------------------

def verifier_plafond(config: dict, carte: str) -> str:
    plafond = config["plafond_lignes"]
    lignes = len(carte.splitlines())
    if lignes > plafond:
        raise Echec(
            f"CARTE.md fait {lignes} lignes pour un plafond de {plafond}. "
            "Le plafond n'est pas cosmétique : une carte qu'on ne lit plus en "
            "dix minutes est redevenue de la documentation. Coupez, ou "
            "déplacez vers docs/."
        )
    return f"{lignes}/{plafond} lignes"


def verifier_sections(config: dict, carte: str) -> str:
    titres = set(re.findall(r"^##\s+(.+?)\s*$", carte, re.MULTILINE))
    manquantes = [s for s in config["sections_obligatoires"] if s not in titres]
    if manquantes:
        raise Echec("sections absentes de CARTE.md : " + ", ".join(manquantes))
    return f"{len(config['sections_obligatoires'])} sections présentes"


def verifier_chemins_declares(config: dict) -> str:
    absents = [c for c in config["chemins"] if not (RACINE / c).exists()]
    if absents:
        raise Echec("chemins déclarés dans carte.json mais absents : " + ", ".join(absents))
    return f"{len(config['chemins'])} chemins déclarés existent"


def verifier_chemins_cites(carte: str) -> str:
    cites = set()
    for motif in re.findall(r"`([^`\s]+)`", carte):
        premier = motif.split("/")[0]
        if "/" in motif and premier in DOSSIERS_RACINE:
            cites.add(motif.rstrip(".,;:)"))
    absents = [c for c in sorted(cites) if not (RACINE / c).exists()]
    if absents:
        raise Echec("chemins cités par CARTE.md mais absents du dépôt : " + ", ".join(absents))
    return f"{len(cites)} chemins cités dans la prose existent"


def verifier_cli(config: dict) -> str:
    if shutil.which("monl") is None:
        raise Echec("la commande `monl` est absente du PATH : `pip install -e \".[dev]\"`")
    aide = ANSI.sub("", _sortie(["monl", "--help"]))
    attendues = config["cli"]["sous_commandes"]
    manquantes = [s for s in attendues if not re.search(rf"\b{re.escape(s)}\b", aide)]
    if manquantes:
        raise Echec(
            "sous-commandes annoncées par la carte mais absentes de `monl --help` : "
            + ", ".join(manquantes)
        )
    # L'inverse compte autant : une commande ajoutée sans être cartographiée est
    # une part du produit que personne ne découvrira en lisant la carte.
    bloc = re.search(r"\{([a-z,\-]+)\}", aide)
    if bloc is None:
        raise Echec(
            "le bloc des sous-commandes est illisible dans `monl --help` : "
            "le contrôle du surplus ne peut pas s'exécuter, et un contrôle qui "
            "ne s'exécute pas ne dit rien."
        )
    reelles = [s for s in bloc.group(1).split(",") if s]
    surplus = [s for s in reelles if s not in attendues]
    if surplus:
        raise Echec(
            "sous-commandes offertes par la CLI mais absentes de la carte : "
            + ", ".join(surplus)
        )
    return f"{len(attendues)} sous-commandes conformes"


def verifier_tests(config: dict) -> str:
    attendu = config["tests"]["collectes"]
    tolerance = config["tests"]["tolerance"]
    # `-o addopts=` neutralise le `-q` de pyproject.toml : cumulé au nôtre il
    # vaudrait `-qq`, qui supprime précisément la ligne de décompte qu'on lit.
    sortie = _sortie([
        sys.executable, "-m", "pytest", "tests/", "--collect-only",
        "-q", "-o", "addopts=", "-p", "no:cacheprovider",
    ])
    trouve = re.search(r"(\d+)\s+tests?\s+collected", sortie)
    if not trouve:
        raise Echec("impossible de lire le décompte de tests collectés")
    reel = int(trouve.group(1))
    ecart = abs(reel - attendu) / attendu
    if ecart > tolerance:
        raise Echec(
            f"la carte annonce ~{attendu} tests, la collecte en trouve {reel} "
            f"({ecart:.0%} d'écart, tolérance {tolerance:.0%}). "
            "Mettez `tests.collectes` à jour dans carte.json."
        )
    return f"{reel} tests collectés (carte : ~{attendu})"


def verifier_preuve_datee(config: dict) -> str:
    commit = config["preuve"]["commit"]
    # Un clone superficiel (`actions/checkout` sans `fetch-depth: 0`, ou un
    # `--depth 1` local) ne contient pas l'ancêtre : le dire vaut mieux que
    # d'échouer sur une absence d'historique, et mieux que de se taire.
    superficiel = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=RACINE, capture_output=True, text=True,
    ).stdout.strip()
    if superficiel == "true":
        return f"preuve prise en {commit} — historique superficiel, lien non vérifiable ici"
    verif = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=RACINE, capture_output=True, text=True,
    )
    if verif.returncode != 0:
        raise Echec(
            f"le commit de preuve {commit} n'est pas un ancêtre de HEAD : "
            "la carte atteste un état que cette branche n'a jamais eu."
        )
    depuis = _sortie(["git", "rev-list", "--count", f"{commit}..HEAD"]).strip()
    return f"preuve prise en {commit}, {depuis} commit(s) plus tôt"


# --------------------------------------------------------------------------
# Rejeu du chemin principal
# --------------------------------------------------------------------------

def _empreintes(dossier: Path, artefacts: list[str]) -> dict[str, str]:
    empreintes = {}
    for nom in artefacts:
        chemin = dossier / nom
        if not chemin.exists():
            raise Echec(f"la compilation n'a pas produit {nom}")
        empreintes[nom] = hashlib.sha256(chemin.read_bytes()).hexdigest()
    return empreintes


def _compiler(config: dict, cible: Path) -> dict[str, str]:
    principal = config["chemin_principal"]
    cible.mkdir(parents=True, exist_ok=True)
    shutil.copy(RACINE / principal["spec"], cible / "spec.ml")
    shutil.copytree(RACINE / principal["assets"], cible / "assets", dirs_exist_ok=True)
    _sortie(["monl", "compile", str(cible / "spec.ml"), "--output", str(cible)])
    return _empreintes(cible, principal["artefacts"])


def verifier_determinisme(config: dict, atelier: Path) -> str:
    a = _compiler(config, atelier / "a")
    b = _compiler(config, atelier / "b")
    # Le secret JWT est tiré au hasard à chaque compilation : il vit dans
    # .jwt_secret, hors de la liste d'artefacts, et ne fausse donc rien ici.
    divergents = [nom for nom in a if a[nom] != b[nom]]
    if divergents:
        raise Echec(
            "deux compilations de la même spec produisent des octets différents : "
            + ", ".join(divergents)
            + ". Le déterminisme est la promesse centrale du compilateur."
        )
    return f"{len(a)} artefacts identiques octet pour octet sur deux compilations"


def verifier_routes(config: dict, projet: Path) -> str:
    principal = config["chemin_principal"]
    port = 8931
    serveur = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--port", str(port),
         "--log-level", "warning"],
        cwd=projet, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        schema = None
        for _ in range(40):
            if serveur.poll() is not None:
                raise Echec("le backend produit s'est arrêté au démarrage")
            try:
                with urllib.request.urlopen(f"{base}/openapi.json", timeout=2) as reponse:
                    schema = json.load(reponse)
                break
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                time.sleep(0.5)
        if schema is None:
            raise Echec("le backend produit n'a jamais répondu")

        reel = sum(len(methodes) for methodes in schema["paths"].values())
        if reel != principal["routes"]:
            raise Echec(
                f"la carte annonce {principal['routes']} routes pour "
                f"{principal['spec']}, le serveur en expose {reel}. "
                "Le compilateur est déterministe : cet écart est un changement "
                "de produit, pas du bruit."
            )
        with urllib.request.urlopen(f"{base}{principal['sonde_sante']}", timeout=5) as r:
            sante = r.read().decode().strip()
        if sante != principal["reponse_sante"]:
            raise Echec(f"{principal['sonde_sante']} répond {sante!r}")
        return f"{reel} routes exposées, {principal['sonde_sante']} conforme"
    finally:
        serveur.terminate()
        try:
            serveur.wait(timeout=10)
        except subprocess.TimeoutExpired:
            serveur.kill()


# --------------------------------------------------------------------------

def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analyseur.add_argument(
        "--preuve", action="store_true",
        help="rejouer aussi le chemin principal (compilation déterministe, routes).",
    )
    arguments = analyseur.parse_args()

    config = _lire_config(RACINE / "carte.json")
    carte = (RACINE / config["carte"]).read_text(encoding="utf-8")

    controles = [
        ("plafond", lambda: verifier_plafond(config, carte)),
        ("sections", lambda: verifier_sections(config, carte)),
        ("chemins déclarés", lambda: verifier_chemins_declares(config)),
        ("chemins cités", lambda: verifier_chemins_cites(carte)),
        ("sous-commandes", lambda: verifier_cli(config)),
        ("tests collectés", lambda: verifier_tests(config)),
        ("preuve datée", lambda: verifier_preuve_datee(config)),
    ]

    atelier: Path | None = None
    if arguments.preuve:
        atelier = Path(tempfile.mkdtemp(prefix="carte-"))
        controles += [
            ("déterminisme", lambda: verifier_determinisme(config, atelier)),
            ("routes réelles", lambda: verifier_routes(config, atelier / "a")),
        ]

    echecs = 0
    try:
        for nom, controle in controles:
            try:
                print(f"  ok   {nom} — {controle()}")
            except Echec as erreur:
                print(f"  ÉCHEC {nom} — {erreur}", file=sys.stderr)
                echecs += 1
    finally:
        if atelier is not None:
            shutil.rmtree(atelier, ignore_errors=True)

    if echecs:
        print(f"\nCARTE.md n'est plus exacte : {echecs} affirmation(s) démentie(s).",
              file=sys.stderr)
        return 1
    print("\nCARTE.md est exacte.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
