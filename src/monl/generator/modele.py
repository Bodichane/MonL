"""De l'AST validé au modèle que le générateur manipule."""

from ..ir import EffectPlan, ForeignKeyPlacement
from ..planning import plan_foreign_keys


class ModeleMixin:
    """De l'AST validé au modèle que le générateur manipule."""


    def _build_effect_plans(self) -> tuple[EffectPlan, ...]:
        """Réunit les effets validés dans un catalogue commun et ordonné."""
        plans = []
        for entity, rules in self.derived_by_entity.items():
            plans.extend(EffectPlan(
                kind="derive", trigger_entity=entity, target_entity=entity,
                field=rule.field, source_entity=rule.source_entity,
                source_field=rule.source_field, config=rule.as_ir(),
            ) for rule in rules)
        for source, rules in self.aggregations_by_source.items():
            plans.extend(EffectPlan(
                kind="aggregate", trigger_entity=source,
                target_entity=rule.entity, field=rule.field,
                source_entity=source, source_field=rule.source_field, config=rule.as_ir(),
            ) for rule in rules)
        for trigger, rules in self.reputation_rules_by_trigger.items():
            plans.extend(EffectPlan(
                kind="increment" if rule.direction == "increments" else "decrement",
                trigger_entity=trigger, target_entity=rule.target_entity,
                field=rule.target_field, source_entity=None,
                source_field=rule.amount_field, config=rule.as_ir(),
            ) for rule in rules)
        for entity, rules in self.release_rules_by_entity.items():
            plans.extend(EffectPlan(
                kind="release", trigger_entity=entity,
                target_entity=rule["releases"], field=rule["field"],
                source_entity=None, source_field=None, config=rule,
            ) for rule in rules)
        plans.extend(EffectPlan(
            kind="payment_lock", trigger_entity=entity, target_entity=entity,
            field=field, source_entity=None, source_field=None,
            config={"entity": entity, "field": field},
        ) for entity, field in self.payable_by_entity.items())
        plans.extend(EffectPlan(
            kind="postpayment_write", trigger_entity=entity, target_entity=entity,
            field=None, source_entity=None, source_field=None, config=config,
        ) for entity, config in self.postpayment_writable_by_entity.items())
        plans.extend(EffectPlan(
            kind="message", trigger_entity=rule["trigger_entity"],
            target_entity=rule["trigger_entity"], field=None,
            source_entity=None, source_field=None, config=rule,
        ) for rule in self.message_rules_by_trigger.values())
        return tuple(plans)

    def _effects(self, kind, *, trigger=None, target=None):
        return [plan for plan in self.effect_plans
                if plan.kind == kind
                and (trigger is None or plan.trigger_entity == trigger)
                and (target is None or plan.target_entity == target)]

    def _compute_fk_placements(self) -> dict[str, list[ForeignKeyPlacement]]:
        """Adaptateur des émetteurs vers l'analyse typée des clés étrangères.

        Le placement ne dépend que de `relation_models`, figé à la
        construction : il est donc calculé UNE fois. Les émetteurs
        l'interrogent depuis des boucles imbriquées — mesuré à 270 305 appels
        pour une spec de 1 668 lignes, soit 102 s passés à reconstruire le
        même index. Le recalculer à chaque appel rendait le coût de
        compilation cubique en nombre d'entités.
        """
        if self._fk_placements_caches is None:
            self._fk_placements_caches = plan_foreign_keys(self.relation_models)
        return self._fk_placements_caches

    def _compute_seed_data(self):
        """AJOUT (roadmap frontend, bloc 'seed') : regroupe les données de
        démonstration par nom de table (lowercase), dans l'ordre de
        déclaration. Retourne {table: [ {champ: valeur}, ... ]}. Plusieurs
        blocs 'seed' visant la même entité sont concaténés.

        Les champs 'generated' (ex. pseudonyme anonyme d'auteur) ne sont pas
        renseignés par l'utilisateur dans le seed (le validateur le tolère
        car ils sont retirés du schéma d'entrée) ; comme à la création réelle
        ils sont assignés par le serveur, on leur donne ici une valeur
        synthétique déterministe ('Anon#1000', 'Anon#1001'…) pour que le seed
        produise des enregistrements complets et cohérents avec le rendu
        (fil social, etc.).

        BRIQUE 21 (point 100) : chaque entrée est désormais un COUPLE
        {"values": {...}, "parent": None | {...}}, et non plus la seule ligne.
        Le rattachement d'un enfant ne peut pas être résolu ici : l'`id` du
        parent n'existe qu'une fois la ligne insérée, et le socle ne sème une
        table que si elle est VIDE — un parent déjà peuplé par de vraies données
        ne serait donc pas réinséré, et un rang calculé à la compilation
        désignerait la mauvaise ligne. La désignation voyage telle quelle et se
        résout par un SELECT au démarrage."""
        seed_data = {}
        for seed in self.seeds:
            entity = seed["entity"]
            table = entity.lower()
            generated = self.generated_fields_by_entity.get(entity, [])
            parent = seed.get("parent")
            rattachement = None
            if parent:
                rattachement = {
                    "column": f"{parent['entity'].lower()}_id",
                    "table": parent["entity"].lower(),
                    "field": parent["field"],
                    "value": parent["value"],
                }
            seed_data.setdefault(table, [])
            for row in seed["rows"]:
                filled = dict(row)
                for gfield in generated:
                    if gfield not in filled:
                        # Pseudonyme synthétique stable, unique par ligne.
                        filled[gfield] = f"Anon#{1000 + len(seed_data[table])}"
                seed_data[table].append({"values": filled, "parent": rattachement})
        return seed_data
