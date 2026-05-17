# Backend

## Trust boundaries and naming

Naming follows the trust boundary where values originate:

- `*Request`: raw API-edge models.
- `*Response`: validated API models.
- `*Input`: typed internal payloads that still need domain checks.
- bare names: internal validated models.
