# Rental Property

Rental Property is a location-aware rental marketplace and occupancy-management platform for landlords, tenants, house seekers, and platform administrators.

## Product direction

The platform is being built around the full rental lifecycle:

`discover -> verify -> book -> occupy -> give notice -> vacate -> re-advertise`

The initial architecture uses:

- Flutter mobile application
- FastAPI backend
- PostgreSQL + PostGIS
- Alembic migrations
- Redis for caching, locks, events, and short-lived booking reservations
- WebSockets for real-time application events
- Object storage for property media and verification documents

## Repository layout

The repository will contain the mobile client, backend API, infrastructure configuration, and project documentation.

Development begins on feature branches and is merged through pull requests after validation.
