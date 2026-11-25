# Converge frontend

Next.js frontend for [Converge](../README.md): search for a shared destination for two travelers, compare ranked itineraries, and check lounge access at a recommended destination.

## How it talks to the backend

The browser never calls the FastAPI backend directly. Pages call this app's own API routes, which forward requests on the server side to the URL in `BACKEND_URL`:

| Frontend route | Backend endpoint |
| --- | --- |
| `POST /api/meetups` | `POST /meetups/search` |
| `GET /api/lounges/cards` | `GET /lounges/cards` |
| `POST /api/lounges/search` | `POST /lounges/search` |

If `BACKEND_URL` is not set, the routes use `http://127.0.0.1:8000`.

## Project layout

```text
app/
  page.tsx             # search form and results UI
  layout.tsx           # root layout and fonts
  globals.css          # Tailwind styles
  api/
    meetups/route.ts         # proxy to /meetups/search
    lounges/cards/route.ts   # proxy to /lounges/cards
    lounges/search/route.ts  # proxy to /lounges/search
```

## Local development

Start the backend first, from the repository root:

```bash
FLIGHT_PROVIDER=mock uvicorn backend.app.api:app --reload
```

Then, in this directory:

```bash
npm install
npm run dev
```

Open http://localhost:3000.

To point at a different backend:

```bash
BACKEND_URL=https://your-backend.example.com npm run dev
```

## Scripts

| Command | What it does |
| --- | --- |
| `npm run dev` | Start the dev server |
| `npm run build` | Production build (run in CI) |
| `npm run start` | Serve the production build |
| `npm run lint` | Run ESLint |

## Deployment

Deployed on Vercel with `frontend/` as the project root. Set `BACKEND_URL` in the Vercel project's environment variables to the Railway backend URL.
