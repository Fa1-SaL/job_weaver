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

API requests default to the local backend at `http://127.0.0.1:8000` in both development and production builds. To use another backend, set `VITE_API_URL` to its origin in a Vite environment file for the relevant mode:

```dotenv
VITE_API_URL=https://api.example.com
```

API bearer tokens must not be added to Vite environment files or bundled into frontend code. Authenticated remote deployments should provide credentials through their runtime integration or an authenticated same-origin proxy.

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

To verify the production bundle locally against the backend on port 8000:

```bash
npm run preview
```
