# Job Weaver frontend

React frontend for Job Weaver, built with Vite and tested with Vitest.

## Requirements

- Node.js `^20.19.0` or `>=22.12.0`
- npm 10 or newer

## Install and run

```bash
npm install
npm run dev
```

The development server is available at [http://localhost:5173](http://localhost:5173). `npm start` is an alias for the same Vite development server.

Development API requests default to the local backend at `http://127.0.0.1:8000`. To use another development backend, set `VITE_API_URL` in a local Vite environment file:

```dotenv
VITE_API_URL=https://api.example.com
```

Production builds default to the same-origin `/api` Vercel proxy. Configure these server-only variables in the Vercel project for Production and Preview, then redeploy:

```dotenv
RENDER_BACKEND_URL=https://job-weaver.onrender.com
JOB_WEAVER_API_TOKEN=replace-with-the-same-secret-used-on-render
```

Leave `VITE_API_URL` unset on Vercel. The proxy adds the Render bearer token on the server, forwards only JD generation, and prevents the secret from being bundled into browser code. History remains local to each browser so a public deployment cannot expose one visitor's saved job descriptions to another. API bearer tokens must never be added to Vite environment files or renamed with a `VITE_` prefix.

The Vercel project's Root Directory must be `frontend` so that both `vercel.json` and the `api` function are deployed.

## Checks

```bash
npm run typecheck
npm test
npm run test:watch
npm audit
```

`npm test` runs the suite once; `npm run test:watch` starts interactive watch mode.

## Production build

```bash
npm run build
```

Vite writes deployable production assets to `dist/`.

To inspect the static production bundle locally:

```bash
npm run preview
```

`vite preview` does not emulate Vercel Functions. Use Vercel's local development command when an end-to-end test of the production proxy is needed.
