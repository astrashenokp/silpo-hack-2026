# Smart Basket Web

Next.js frontend for the Smart Basket AI demo.

## Local Development

Start the backend API first, then run the frontend from this directory:

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

The app calls backend routes through same-origin `/api/...` requests configured
in `next.config.ts`.

## Checks

```bash
npm run lint
npm run build
```

The UI uses system fonts so the production build does not depend on fetching
Google Fonts.
