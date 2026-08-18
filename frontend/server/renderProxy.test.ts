import { describe, expect, it, vi } from 'vitest';
import {
  proxyRenderRequest,
  type ProxyRequest,
  type ProxyResponse
} from './renderProxy';

const VALID_ENV = {
  RENDER_BACKEND_URL: 'https://job-weaver.onrender.com/',
  JOB_WEAVER_API_TOKEN: 'server-only-secret'
};

function request(overrides: Partial<ProxyRequest> = {}): ProxyRequest {
  return {
    method: 'POST',
    url: '/api/parse-jd',
    headers: {},
    body: { raw_jd: 'A valid JD', client: 'mercor' },
    ...overrides
  };
}

function responseRecorder() {
  const headers = new Map<string, string>();
  let body = '';
  const response: ProxyResponse = {
    statusCode: 200,
    setHeader(name, value) {
      headers.set(name.toLowerCase(), value);
    },
    end(value = '') {
      body = value;
    }
  };
  return {
    response,
    headers,
    get body() {
      return body;
    }
  };
}

describe('Render API proxy', () => {
  it('forwards an allowed request and replaces browser authorization with the server token', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ success: true, id: 'generated-id' }),
      { status: 201, headers: { 'Content-Type': 'application/json' } }
    ));
    const recorder = responseRecorder();

    await proxyRenderRequest(
      request({
        method: 'POST',
        url: '/api/proxy?path=parse-jd',
        headers: {
          authorization: 'Bearer browser-controlled-value',
          origin: 'https://attacker.example',
          'content-type': 'application/json'
        },
        body: { raw_jd: 'A valid JD', client: 'mercor' }
      }),
      recorder.response,
      { env: VALID_ENV, fetchImpl }
    );

    expect(fetchImpl).toHaveBeenCalledOnce();
    const [url, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(url).toBe('https://job-weaver.onrender.com/parse-jd');
    expect(init.method).toBe('POST');
    expect(init.body).toBe(JSON.stringify({ raw_jd: 'A valid JD', client: 'mercor' }));
    expect(headers.get('authorization')).toBe('Bearer server-only-secret');
    expect(headers.has('origin')).toBe(false);
    expect(recorder.response.statusCode).toBe(201);
    expect(JSON.parse(recorder.body)).toEqual({ success: true, id: 'generated-id' });
    expect(recorder.headers.get('cache-control')).toBe('no-store');
  });

  it.each([
    ['/api/parse-jd', 'GET', 405],
    ['/api/history', 'GET', 404],
    ['/api/history/item', 'DELETE', 404],
    ['/api/history/item/extra', 'GET', 404],
    ['/api/https://attacker.example', 'POST', 404],
    ['/api/history/%2Fadmin', 'GET', 404]
  ])('blocks unsupported route %s or method %s', async (url, method, status) => {
    const fetchImpl = vi.fn();
    const recorder = responseRecorder();

    await proxyRenderRequest(
      request({ url, method }),
      recorder.response,
      { env: VALID_ENV, fetchImpl }
    );

    expect(recorder.response.statusCode).toBe(status);
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it.each([
    {},
    { RENDER_BACKEND_URL: 'http://job-weaver.onrender.com', JOB_WEAVER_API_TOKEN: 'secret' },
    { RENDER_BACKEND_URL: 'https://job-weaver.onrender.com/path', JOB_WEAVER_API_TOKEN: 'secret' },
    { RENDER_BACKEND_URL: 'https://job-weaver.onrender.com', JOB_WEAVER_API_TOKEN: '   ' }
  ])('fails closed when its server-only configuration is missing or unsafe', async env => {
    const fetchImpl = vi.fn();
    const recorder = responseRecorder();

    await proxyRenderRequest(request(), recorder.response, { env, fetchImpl });

    expect(recorder.response.statusCode).toBe(500);
    expect(JSON.parse(recorder.body)).toEqual({ detail: 'The API proxy is not configured' });
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it('turns network failures and non-JSON platform pages into readable JSON errors', async () => {
    const networkFailure = responseRecorder();
    await proxyRenderRequest(request(), networkFailure.response, {
      env: VALID_ENV,
      fetchImpl: vi.fn().mockRejectedValue(new Error('private network detail'))
    });
    expect(networkFailure.response.statusCode).toBe(502);
    expect(JSON.parse(networkFailure.body)).toEqual({
      detail: 'The backend service could not be reached'
    });

    const unreadable = responseRecorder();
    await proxyRenderRequest(request(), unreadable.response, {
      env: VALID_ENV,
      fetchImpl: vi.fn().mockResolvedValue(new Response('<html>Render error</html>', {
        status: 503,
        headers: { 'Content-Type': 'text/html' }
      }))
    });
    expect(unreadable.response.statusCode).toBe(502);
    expect(JSON.parse(unreadable.body)).toEqual({
      detail: 'The backend returned an unreadable response'
    });
  });

  it('rejects an unserializable request body without invoking Render', async () => {
    const fetchImpl = vi.fn();
    const recorder = responseRecorder();

    await proxyRenderRequest(
      request({ method: 'POST', url: '/api/proxy?path=parse-jd', body: { value: 1n } }),
      recorder.response,
      { env: VALID_ENV, fetchImpl }
    );

    expect(recorder.response.statusCode).toBe(400);
    expect(JSON.parse(recorder.body)).toEqual({ detail: 'The request body is not valid JSON' });
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it('preserves backend errors and rate-limit guidance', async () => {
    const recorder = responseRecorder();
    await proxyRenderRequest(request(), recorder.response, {
      env: VALID_ENV,
      fetchImpl: vi.fn().mockResolvedValue(new Response(
        JSON.stringify({ detail: 'Generation rate limit exceeded' }),
        { status: 429, headers: { 'Retry-After': '12' } }
      ))
    });

    expect(recorder.response.statusCode).toBe(429);
    expect(recorder.headers.get('retry-after')).toBe('12');
    expect(JSON.parse(recorder.body)).toEqual({ detail: 'Generation rate limit exceeded' });
  });
});
