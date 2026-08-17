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

In development, API requests default to `http://127.0.0.1:8000`. To use another backend, set `VITE_API_URL` to its origin in a local Vite environment file such as `.env.development`:

```dotenv
VITE_API_URL=https://api.example.com
```

Production builds use same-origin API paths when `VITE_API_URL` is unset. API bearer tokens must not be added to Vite environment files. For an authenticated remote backend, enter the token at runtime under **Advanced / Remote API**. It is kept only in memory and `sessionStorage`, and is sent as an `Authorization: Bearer …` header.

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
