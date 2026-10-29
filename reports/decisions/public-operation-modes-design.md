# Public operation modes — product concept

2026-10-29. Agreed product direction after PR #14.
Status: design only; not implemented or published as a hosted service.

The interface offers three mutually exclusive modes:

| Mode | Visitor experience |
| --- | --- |
| Живой режим | Live scenario when available, plus recorded examples |
| Пауза | Temporary unavailability notice and recorded examples |
| Только демонстрация | Recorded examples without live controls or promises of return |

Demonstration-only mode is reversible. Recorded examples must remain usable
independently of live inference. Notices must describe actual availability
without inventing a reason for unavailability.

Model proposals remain subject to runtime validation and operator confirmation.
A mode label is not evidence of readiness, successful execution or recovery.

This public document describes product behavior only. Deployment instructions,
operational procedures and environment-specific configuration are outside its
scope. Examples intended for publication must use placeholders.
