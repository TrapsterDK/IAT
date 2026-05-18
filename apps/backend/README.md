# Backend

## Trust boundaries and naming

Naming follows the trust boundary where values originate:

- `schemas/`: API-edge request and response models used by routers.
- `models/`: shared internal data models used across backend layers.
- `domain/`: business rules, validation, planning, and scoring logic.
- `*Request`: raw API-edge models.
- `*Response`: validated API models.
- `*Input`: typed internal payloads that still need domain checks.
- bare names: internal validated models.
