# ChoreTracker

ChoreTracker is a demonstration household chore-management and simulated
allowance application.

## Financial demonstration notice

All money shown by ChoreTracker is simulated.

No real funds are transferred. LunchMoneyPay is a mock payment processor, and
all financial values are for demonstration and learning purposes only.

## Environments

- Development and local testing: macOS
- Staging: Debian 13
- Production: Debian 13

Debian 13 is the authoritative runtime target.

## Current status

The project is in its initial backend-platform foundation milestone.

## Development ports

ChoreTracker uses configurable, non-standard host ports to avoid collisions
with other local projects.

Initial development defaults:

- FastAPI: `8110`
- PostgreSQL host port: `55410`
- Vite frontend: `51810`

PostgreSQL continues to use port `5432` inside its container.
