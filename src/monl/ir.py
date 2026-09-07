"""Types de l'interface entre validation, analyse et génération.

L'IR reste volontairement composée de conteneurs Python simples : les
émetteurs existants peuvent donc être migrés progressivement, sans conversion
globale ni changement du JSON produit. Ces ``TypedDict`` rendent toutefois la
frontière explicite et vérifiable par un analyseur de types.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from .ir_types import (
    ActionIR,
    ActionKind,
    AggregatedFieldIR,
    CategorizedFieldIR,
    CategoryClauseIR,
    CategoryLabelIR,
    CompilationIR,
    CounterRuleIR,
    DerivedFieldIR,
    EntityFields,
    FieldBoundIR,
    FieldConstraintsIR,
    ForeignKeyPlacement,
    MetaIR,
    NamedFieldIR,
    NumberedFieldIR,
    PostPaymentIR,
    PublicConditionIR,
    RelationIR,
    RelationKind,
    SandboxIR,
    SchemaIR,
    SecurityIR,
    TransitiveOwnershipIR,
    UploadFieldIR,
    WorkflowIR,
)

__all__ = [
    "AccessPolicy", "ActionIR", "ActionKind", "AggregatePlan",
    "AggregatedFieldIR", "AggregationPlans", "CategorizedFieldIR",
    "CategoryClauseIR", "CategoryLabelIR", "CompilationIR", "CompilationPlans",
    "CompilationResult", "CounterPlan", "CounterRuleIR", "DerivedFieldIR",
    "DerivedPlan", "EffectKind", "EffectPlan", "EntityFields", "EntityModel",
    "FieldBound", "FieldBoundIR", "FieldConstraints", "FieldConstraintsIR",
    "FieldPolicy", "ForeignKeyPlacement", "MetaIR", "NamedFieldIR",
    "NumberedFieldIR", "NumberingPlan", "PostPaymentIR", "PublicCondition",
    "PublicConditionIR", "RelationIR", "RelationKind", "RelationModel",
    "RoutePlan", "SandboxIR", "SchemaIR", "SecurityIR", "TransitiveOwnership",
    "TransitiveOwnershipIR", "UploadFieldIR", "UploadPlan", "WorkflowIR",
]

EffectKind = Literal[
    "derive",
    "aggregate",
    "increment",
    "decrement",
    "release",
    "payment_lock",
    "postpayment_write",
    "message",
]

# Colonnes sémantiques communes au schéma, au runtime et au contrat frontend.
# Elles appartiennent à l'IR, pas à un émetteur particulier.
PAYMENT_STATUS_COLUMN = "payment_status"
PAYMENT_REF_COLUMN = "payment_ref"
PAYMENT_TRACKING_COLUMNS = (PAYMENT_STATUS_COLUMN, PAYMENT_REF_COLUMN)



class CompilationGenerator(Protocol):
    """Surface minimale du générateur exposée par ``CompilationResult``."""

    ast: CompilationIR
    app_name: str
    compilation_plans: "CompilationPlans"


@dataclass(slots=True)
class RoutePlan:
    """Route logique fusionnée depuis un ou plusieurs workflows.

    Une route n'est pas encore du code FastAPI ni une entrée du contrat JSON :
    c'est le plan commun que ces deux émetteurs rendent ensuite chacun dans
    leur format.
    """

    action: ActionKind
    key: str
    target: str
    base_target: str
    actors: set[str]
    tags: list[str]

    def allow(self, actor: str, workflow: str) -> None:
        self.actors.add(actor)
        if workflow not in self.tags:
            self.tags.append(workflow)


@dataclass(frozen=True, slots=True)
class DerivedPlan:
    """Calcul serveur résolu, partagé par les routes et le contrat frontend."""

    entity: str
    field: str
    source_entity: str
    source_field: str
    factor: str
    source_fk: str

    def as_ir(self) -> DerivedFieldIR:
        """Copie au format historique pour le catalogue générique d'effets."""
        return {
            "entity": self.entity, "field": self.field,
            "source_entity": self.source_entity, "source_field": self.source_field,
            "factor": self.factor,
        }


@dataclass(frozen=True, slots=True)
class AggregatePlan:
    """Somme résolue ; parent_fk se trouve sur l'entité source enfant."""

    entity: str
    field: str
    source_entity: str
    source_field: str
    parent_fk: str

    def as_ir(self) -> AggregatedFieldIR:
        return {
            "entity": self.entity, "field": self.field,
            "source_entity": self.source_entity, "source_field": self.source_field,
        }


@dataclass(frozen=True, slots=True)
class AggregationPlans:
    """Deux index d'un même jeu de calculs : cible et événement source."""

    by_entity: Mapping[str, tuple[AggregatePlan, ...]]
    by_source: Mapping[str, tuple[AggregatePlan, ...]]


@dataclass(frozen=True, slots=True)
class CounterPlan:
    """Effet sur une ligne liée ; la cible et son plancher sont déjà résolus."""

    trigger_entity: str
    target_entity: str
    target_field: str
    amount: int | None
    amount_field: str | None
    direction: Literal["increments", "decrements"]
    target_fk: str
    minimum: int | None

    def as_ir(self) -> CounterRuleIR:
        return {
            "trigger_entity": self.trigger_entity, "target_entity": self.target_entity,
            "target_field": self.target_field, "amount": self.amount,
            "amount_field": self.amount_field, "direction": self.direction,
        }


@dataclass(frozen=True, slots=True)
class FieldBound:
    portee: Literal["longueur", "valeur"]
    valeur: int


@dataclass(frozen=True, slots=True)
class FieldConstraints:
    required: bool
    unique: bool
    minimum: FieldBound | None
    maximum: FieldBound | None


@dataclass(frozen=True, slots=True)
class NumberingPlan:
    format: str
    period: str


@dataclass(frozen=True, slots=True)
class UploadPlan:
    max_bytes: int
    accepted_types: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FieldPolicy:
    """Sémantique consolidée d'un champ après validation."""

    name: str
    type: str
    hidden_in_reads: bool
    server_generated: bool
    categorized_in_reads: bool
    postpayment_only: bool
    allowed_values: tuple[str, ...]
    constraints: FieldConstraints
    derived_rule: DerivedPlan | None
    aggregate_rule: AggregatePlan | None
    timestamped: bool
    numbering_rule: NumberingPlan | None
    upload_rule: UploadPlan | None


@dataclass(frozen=True, slots=True)
class EntityModel:
    """Entité et politiques de ses champs, indexées par leur nom."""

    name: str
    fields: Mapping[str, FieldPolicy]


@dataclass(frozen=True, slots=True)
class RelationModel:
    """Relation validée et orientation physique de sa clé étrangère."""

    source: str
    kind: RelationKind
    target: str

    @property
    def owner_entity(self) -> str:
        return self.target if self.kind == "belongsTo" else self.source

    @property
    def held_entity(self) -> str:
        return self.source if self.kind == "belongsTo" else self.target

    @property
    def fk_column(self) -> str:
        return f"{self.owner_entity.lower()}_id"

    @property
    def unique(self) -> bool:
        return self.kind == "hasOne"


@dataclass(frozen=True, slots=True)
class PublicCondition:
    field: str
    value: str


@dataclass(frozen=True, slots=True)
class TransitiveOwnership:
    actor: str
    chain: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AccessPolicy:
    """Décision d'accès consolidée pour une action sur une cible."""

    entity: str
    action: str
    actors: frozenset[str]
    public: bool
    public_condition: PublicCondition | None
    owner_entity: str | None
    transitive_ownership: TransitiveOwnership | None
    party_fields: tuple[str, ...]
    supervisors: frozenset[str]


@dataclass(frozen=True, slots=True)
class EffectPlan:
    """Effet métier validé, indépendant de son rendu SQL ou HTTP."""

    kind: EffectKind
    trigger_entity: str
    target_entity: str
    field: str | None
    source_entity: str | None
    source_field: str | None
    config: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class CompilationPlans:
    """Analyses dérivées partagées par les émetteurs.

    Le générateur reste l'implémentation historique de ces calculs, mais le
    contrat frontend reçoit désormais ce résultat nommé plutôt que de lire ses
    méthodes privées. Les deux émetteurs consomment donc la même analyse.
    """

    route_map: Mapping[tuple[str, str], RoutePlan]
    foreign_key_placements: Mapping[str, tuple[ForeignKeyPlacement, ...]]
    identity_foreign_keys: Mapping[str, frozenset[str]]
    client_foreign_keys: Mapping[str, tuple[str, ...]]
    incoming_relations: Mapping[str, Mapping[str, Any] | None]
    payment_locked_parents: Mapping[str, tuple[Mapping[str, Any], ...]]
    reputation_rules_by_trigger: Mapping[str, tuple[CounterPlan, ...]]
    entity_models: Mapping[str, EntityModel]
    access_policies: Mapping[tuple[str, str], AccessPolicy]
    actors: tuple[str, ...]
    self_register_actors: tuple[str, ...]
    auth_identifier: tuple[str, ...] | None
    auth_phone_prefix: str | None
    auth_features: Mapping[str, Any]
    payment_currency: Mapping[str, Any] | None
    payment_provider: str | None
    public_conditions: Mapping[tuple[str, str], Mapping[str, Any]]
    required_profiles: Mapping[str, str]
    payable_by_entity: Mapping[str, str]
    release_rules_by_entity: Mapping[str, tuple[Mapping[str, Any], ...]]
    transitive_ownership: Mapping[str, Mapping[str, Any]]
    postpayment_writable_by_entity: Mapping[str, Mapping[str, Any]]
    assets: Mapping[str, Any]
    once_per_rules: tuple[Mapping[str, Any], ...]
    upload_fields: tuple[Mapping[str, Any], ...]
    message_rules_by_trigger: Mapping[str, Mapping[str, Any]]
    filterable_fields: Mapping[str, tuple[str, ...]]
    sortable_fields: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class CompilationResult:
    """Résultat nommé d'une compilation backend réussie."""

    ir: CompilationIR
    generator: CompilationGenerator
    plans: CompilationPlans
