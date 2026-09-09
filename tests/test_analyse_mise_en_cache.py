"""Les analyses partagées sont calculées une fois, pas à chaque interrogation.

Ce témoin compte des APPELS et jamais des secondes : un seuil temporel ne veut
pas dire la même chose sur deux machines (point 160), alors qu'un nombre
d'appels est déterministe. Sans les caches, une spec de cette taille demandait
270 305 reconstructions du même index de clés étrangères — le coût de
compilation devenait cubique en nombre d'entités, et une spec de 1 668 lignes
prenait près de sept minutes.
"""

from monl import planning
from monl.ast_validator import MonlAST
from monl.generator import MonlSecureGenerator
from monl.parser import parse_monl_string


def _spec_a_effets(n_familles):
    """Une spec dont chaque famille porte compteur, unicité composite et
    masquage : c'est la combinaison qui fait interroger les mêmes analyses
    depuis plusieurs boucles imbriquées."""
    lignes = ["app BancCache", "", "entity Membre", "    pseudo: String",
              "    reputation: Integer", ""]
    for i in range(n_familles):
        lignes += [f"entity Publication{i}", "    auteur: String",
                   "    titre: String", "    mentions: Integer", "",
                   f"entity Appreciation{i}", "    note: Integer", ""]
    lignes += ["actor Membre selfRegister", ""]
    for i in range(n_familles):
        lignes += [f"relation Membre hasMany Publication{i}",
                   f"relation Membre hasMany Appreciation{i}",
                   f"relation Publication{i} hasMany Appreciation{i}"]
    lignes.append("")
    for i in range(n_familles):
        lignes += [
            f"rule Publication{i}.titre required",
            f"rule Publication{i}.auteur generated",
            f"rule Publication{i}.Update ownedBy Membre",
            f"rule Appreciation{i}.Create increments Publication{i}.mentions",
            f"rule Appreciation{i}.Create oncePer Membre, Publication{i}",
            f"rule Appreciation{i}.Read ownedBy Membre",
        ]
    lignes += ["", "workflow Participer for Membre"]
    for i in range(n_familles):
        for action in ("Create", "Read", "Update"):
            lignes.append(f"    {action} Publication{i}")
        lignes += [f"    Create Appreciation{i}", f"    Read Appreciation{i}"]
    return "\n".join(lignes) + "\n"


def _compiler(monkeypatch, n_familles):
    """Compile en comptant les reconstructions de l'index de clés étrangères."""
    appels = []
    vrai = planning.plan_foreign_keys

    def compte(relations):
        appels.append(1)
        return vrai(relations)

    # Le remplacement vise le module où le nom est CHERCHÉ (point 153) :
    # `modele.py` importe la fonction, donc c'est là qu'elle est résolue.
    from monl.generator import modele
    monkeypatch.setattr(modele, "plan_foreign_keys", compte)

    ir = MonlAST(parse_monl_string(_spec_a_effets(n_familles))).validate_and_audit()
    generateur = MonlSecureGenerator(ir)
    generateur.emitters.render()
    return len(appels)


def test_lindex_des_cles_etrangeres_nest_construit_quune_fois(monkeypatch, capsys):
    """Une seule construction, quelle que soit la taille de la spec."""
    petit = _compiler(monkeypatch, 3)
    capsys.readouterr()
    assert petit == 1, (
        f"{petit} reconstructions de l'index pour 3 familles : le cache de "
        "`_compute_fk_placements` ne porte plus.")


def test_le_cout_danalyse_ne_suit_pas_la_taille_de_la_spec(monkeypatch, capsys):
    """Le nombre d'appels ne doit pas croître avec le nombre d'entités.

    C'est la propriété qui compte, et elle se mesure sans chronomètre : si le
    coût redevenait proportionnel (ou pire) au nombre d'entités, ce témoin le
    dirait sur n'importe quelle machine.
    """
    petit = _compiler(monkeypatch, 3)
    capsys.readouterr()
    grand = _compiler(monkeypatch, 24)
    capsys.readouterr()
    assert petit == grand == 1, (
        f"l'index est reconstruit {petit} fois pour 3 familles et {grand} fois "
        "pour 24 : l'analyse redevient proportionnelle à la taille de la spec.")


def test_les_colonnes_didentite_sont_deduites_une_seule_fois(capsys):
    """`_identity_fk_columns` est interrogé par sept émetteurs : il mémorise.

    Le contenu doit rester identique entre deux interrogations — un cache qui
    rendrait autre chose au second appel serait pire que pas de cache.
    """
    ir = MonlAST(parse_monl_string(_spec_a_effets(4))).validate_and_audit()
    generateur = MonlSecureGenerator(ir)
    capsys.readouterr()

    premier = generateur._identity_fk_columns()
    second = generateur._identity_fk_columns()

    assert premier is second, "chaque interrogation refait la déduction"
    # Toute entité créée par le membre porte SA colonne de compte, y compris
    # l'appréciation — dont la seconde relation entrante vise la publication
    # comptée, écartée parce que c'est le client qui la désigne (point 99).
    attendu = {f"{prefixe}{i}": {"membre_id"}
               for prefixe in ("Publication", "Appreciation") for i in range(4)}
    assert premier == attendu, premier
