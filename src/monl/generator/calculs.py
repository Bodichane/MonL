"""Rendu des calculs à partir des plans métier résolus.

Les clés des dérivations, agrégations et compteurs sont déterminées par
`planning`. Les émetteurs de création, modification et suppression lisent
les mêmes plans pour conserver la cible de chaque effet."""

class CalculsMixin:
    """Ce que le serveur CALCULE : dérivation, somme, compteurs."""

    def _derived_field_names(self, entity: str) -> list[str]:
        """Champs de 'entity' calculés par le serveur (brique 10, point 77).

        Ils doivent être traités comme les champs 'generated' partout où le
        client pourrait les fournir : absents du schéma Pydantic, et exclus des
        valeurs d'écriture qu'on lit dans `data`."""
        return [plan.field for plan in self.derived_by_entity.get(entity, ())]

    def _aggregated_field_names(self, entity: str) -> list[str]:
        """Champs de 'entity' qui sont une SOMME de ses enfants (brique 12).

        Traités partout comme les champs 'derivedFrom' : absents du schéma
        Pydantic, et jamais lus dans `data`."""
        return [plan.field for plan in self.aggregated_by_entity.get(entity, ())]

    def _aggregation_recomputes(self, source_entity):
        """Sommes à recalculer après toute écriture sur 'source_entity'.

        La requête recalcule les lignes du parent dans la transaction de
        l'écriture. COALESCE donne zéro à un panier vide et ROUND conserve
        l'arrondi monétaire attendu par les routes existantes."""
        recalculs = []
        for plan in self.aggregations_by_source.get(source_entity, ()):
            fk = plan.parent_fk
            recalculs.append({
                "fk_column": fk,
                "sql": (f'UPDATE "{plan.entity.lower()}" SET "{plan.field}" = '
                        f'(SELECT ROUND(COALESCE(SUM("{plan.source_field}"), 0), 2) '
                        f'FROM "{source_entity.lower()}" WHERE "{fk}" = ?) '
                        f'WHERE id = ?'),
            })
        return recalculs

    def _counter_fk_columns(self, trigger_entity: str) -> list[str]:
        """Clés choisies par le client, dédoublonnées dans l'ordre des effets."""
        return list(dict.fromkeys(
            plan.target_fk for plan in self.reputation_rules_by_trigger.get(trigger_entity, ())
        ))

    def _emit_categorization_lines(self, categorized_field, row_var, indent):
        """AJOUT (roadmap, écosystème de capacités -- brique 5) : génère le
        code source Python qui remplace, sur un dict de ligne déjà nommé
        (row_var), un champ numérique par son libellé de catégorie
        (ex. 'likes' -> 'likes_category'). La validation dans
        ast_validator.py garantit que 'clauses' se termine toujours par
        exactement un palier 'otherwise', et que tous les paliers 'below'
        qui précèdent sont strictement croissants -- donc la chaîne
        if/elif/.../else générée ici est toujours syntaxiquement valide et
        couvre nécessairement toute valeur possible."""
        field = categorized_field["field"]
        clauses = categorized_field["clauses"]
        cat_key = f"{field}_category"
        # repr() plutôt qu'une interpolation manuelle entre guillemets : le
        # libellé vient d'un STRING_LITERAL utilisateur et peut contenir des
        # apostrophes/antislashs -- repr() produit toujours un littéral
        # Python syntaxiquement valide, quel que soit le contenu.
        lines = [f"{indent}_v = {row_var}.pop('{field}')"]
        for i, clause in enumerate(clauses):
            label_literal = repr(clause["label"])
            if "otherwise" in clause:
                lines.append(f"{indent}else: {row_var}['{cat_key}'] = {label_literal}")
            else:
                keyword = "if" if i == 0 else "elif"
                lines.append(f"{indent}{keyword} _v < {clause['below']}: {row_var}['{cat_key}'] = {label_literal}")
        return lines
