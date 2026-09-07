# Frontend architecture

The frontend is a Next.js application using TypeScript and Tailwind CSS. A
shared dashboard shell provides navigation, the dark visual theme, and common
status indicators across pages.

## Pages

- `/` presents the system summary and an empty state when no monitors exist.
- `/monitors` presents the paginated monitor inventory.
- `/monitors/[id]` presents monitor metadata, aggregate statistics, charts, and
  paginated history.

## Data flow

Browser components fetch read-only data from the FastAPI service using the
published host URL. The frontend does not connect directly to PostgreSQL or
Redis. Loading, error, and empty states are shared components so API
availability problems are presented consistently.

## Future work

Authentication-aware data fetching, query caching, richer filters, and
operator workflows such as alert acknowledgement should be added only after
the corresponding backend contracts are defined.
