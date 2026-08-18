type HeaderValue = string | string[] | undefined;

export interface ProxyRequest {
  method?: string;
  url?: string;
  headers: Record<string, HeaderValue>;
  body?: unknown;
}

export interface ProxyResponse {
  statusCode: number;
  setHeader(name: string, value: string): void;
  end(body?: string): void;
}

interface ProxyRuntime {
  env?: Record<string, string | undefined>;
  fetchImpl?: typeof fetch;
}

const JSON_CONTENT_TYPE = 'application/json; charset=utf-8';

function firstHeader(value: HeaderValue) {
  return Array.isArray(value) ? value[0] : value;
}

function writeJson(response: ProxyResponse, status: number, payload: object) {
  response.statusCode = status;
  response.setHeader('Content-Type', JSON_CONTENT_TYPE);
  response.setHeader('Cache-Control', 'no-store');
  response.setHeader('X-Content-Type-Options', 'nosniff');
  response.end(JSON.stringify(payload));
}

function backendPathFromRequest(requestUrl: string | undefined) {
  const url = new URL(requestUrl || '/', 'https://job-weaver.invalid');
  if (url.pathname === '/api/proxy') {
    const rewrittenPath = url.searchParams.get('path');
    return rewrittenPath ? `/${rewrittenPath.replace(/^\/+/, '')}` : '/';
  }
  return url.pathname.startsWith('/api/')
    ? url.pathname.slice('/api'.length)
    : url.pathname;
}

function methodsForPath(path: string) {
  if (path === '/parse-jd') return ['POST'];
  return [];
}

function readServerConfig(env: Record<string, string | undefined>) {
  const configuredUrl = env.RENDER_BACKEND_URL?.trim();
  const token = env.JOB_WEAVER_API_TOKEN?.trim();

  if (!configuredUrl || !token || /[\r\n]/.test(token)) return null;

  try {
    const url = new URL(configuredUrl);
    const hasUnexpectedUrlParts = Boolean(
      url.username ||
      url.password ||
      url.search ||
      url.hash ||
      (url.pathname && url.pathname !== '/')
    );
    if (url.protocol !== 'https:' || hasUnexpectedUrlParts) return null;
    return { backendOrigin: url.origin, token };
  } catch {
    return null;
  }
}

function serializeRequestBody(body: unknown) {
  if (body === undefined || body === null) return undefined;
  if (typeof body === 'string') return body;
  if (body instanceof Uint8Array) return new TextDecoder().decode(body);
  return JSON.stringify(body);
}

export async function proxyRenderRequest(
  request: ProxyRequest,
  response: ProxyResponse,
  runtime: ProxyRuntime = {}
) {
  const method = (request.method || '').toUpperCase();
  const backendPath = backendPathFromRequest(request.url);
  const allowedMethods = methodsForPath(backendPath);

  if (allowedMethods.length === 0) {
    writeJson(response, 404, { detail: 'API route not found' });
    return;
  }
  if (!allowedMethods.includes(method)) {
    response.setHeader('Allow', allowedMethods.join(', '));
    writeJson(response, 405, { detail: 'Method not allowed' });
    return;
  }

  const config = readServerConfig(runtime.env || process.env);
  if (!config) {
    writeJson(response, 500, { detail: 'The API proxy is not configured' });
    return;
  }

  const headers = new Headers({
    Accept: 'application/json',
    Authorization: `Bearer ${config.token}`
  });
  let body: string | undefined;
  try {
    body = method === 'POST' ? serializeRequestBody(request.body) : undefined;
  } catch {
    writeJson(response, 400, { detail: 'The request body is not valid JSON' });
    return;
  }
  if (body !== undefined) {
    headers.set(
      'Content-Type',
      firstHeader(request.headers['content-type']) || JSON_CONTENT_TYPE
    );
  }

  try {
    const upstream = await (runtime.fetchImpl || fetch)(
      `${config.backendOrigin}${backendPath}`,
      {
        method,
        headers,
        body,
        redirect: 'manual'
      }
    );
    const upstreamBody = await upstream.text();

    if (upstream.status === 204 && !upstreamBody) {
      response.statusCode = 204;
      response.setHeader('Cache-Control', 'no-store');
      response.end();
      return;
    }

    try {
      JSON.parse(upstreamBody);
    } catch {
      writeJson(response, 502, { detail: 'The backend returned an unreadable response' });
      return;
    }

    response.statusCode = upstream.status;
    response.setHeader('Content-Type', JSON_CONTENT_TYPE);
    response.setHeader('Cache-Control', 'no-store');
    response.setHeader('X-Content-Type-Options', 'nosniff');
    const retryAfter = upstream.headers.get('retry-after');
    if (retryAfter) response.setHeader('Retry-After', retryAfter);
    response.end(upstreamBody);
  } catch {
    writeJson(response, 502, { detail: 'The backend service could not be reached' });
  }
}
