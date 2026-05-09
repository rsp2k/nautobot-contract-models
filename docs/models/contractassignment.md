# Contract Assignment

A generic-FK link between a `Contract` and any Nautobot object that has a UUID PK. One model handles Contract-to-Device, Contract-to-Circuit, Contract-to-VirtualMachine, Contract-to-Tenant, etc. without per-target-type tables.

## Fields

| Field | Type | Notes |
|---|---|---|
| `contract` | FK Contract | Parent contract. CASCADE on delete. |
| `content_type` | FK ContentType | Type of the assigned object. |
| `object_id` | UUID | PK of the assigned object. |
| `object` | GenericForeignKey | Resolved at access time. |
| `coverage_start` | date | When coverage of this target begins. Null = follows the contract's `start_date`. |
| `coverage_end` | date | When coverage of this target ends. Null = follows the contract's `end_date`. |
| `scope_notes` | string | Optional qualifier (e.g. "chassis only, not modules"; "firmware updates excluded"). |
| `is_primary` | bool | When the same target is covered by multiple contracts, this flag picks the primary one for display / on-call routing. |

## Why a generic FK rather than per-target M2M?

Vendor support contracts typically cover a *fleet* — devices, circuits, virtual machines, sometimes a whole tenant or location. Modeling this as a Device M2M would mean separate models for every assignable target type. The generic FK lets one `ContractAssignment` row cover any Nautobot model with a UUID PK (which is every Nautobot model).

## Why subclass `PrimaryModel` rather than `BaseModel`?

`NautobotModelForm` requires `RelationshipModelMixin`, which `PrimaryModel` provides but `BaseModel` doesn't. Phase 2's earlier `BaseModel` choice 500'd the create form. Promoting to `PrimaryModel` matches Nautobot's own `ContactAssociation` model — the canonical GFK-link pattern.

## Constraints

- `UniqueConstraint(contract, content_type, object_id)` — one assignment per (contract, target) pair.

## Indexes

- `(content_type, object_id)` — speeds up the transitive coverage query that joins on the GFK target.

## Transitive coverage

The `helpers.coverage_assignments(target)` helper walks `(self, tenant, location, rack, device)` ancestry and returns *all* assignments covering the target — including ones attached at the Tenant or Location level. A Tenant-level contract assignment automatically covers every Device under that Tenant.

See [Using the App — Coverage Gaps](../user/app_use_cases.md#coverage-gaps) for the operator-facing surface.

## Extras features enabled

`custom_fields`, `custom_links`, `custom_validators`, `export_templates`, `graphql`, `relationships`, `webhooks`.
