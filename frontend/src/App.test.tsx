import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App, { resolveApiUrl, shouldUseServerHistory } from './App';

const LAST_RUN_CACHE_KEY = 'job_weaver_last_run_v2';
const HISTORY_CACHE_KEY = 'job_weaver_history_v2';
const DETAIL_CACHE_PREFIX = 'jw_detail_v2_';
const API_TOKEN_SESSION_KEY = 'job_weaver_api_token';
const API_CACHE_SCOPE_SESSION_KEY = 'job_weaver_api_cache_scope';
const CACHE_SCOPE_MARKER_KEY = 'job_weaver_cache_scope_v2';
const COLOR_THEME_STORAGE_KEY = 'job-weaver-color-theme';

function mockSystemTheme(dark: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: query === '(prefers-color-scheme: dark)' && dark,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn()
    }))
  });
}

function jsonResponse(data: any, ok = true, status = ok ? 200 : 400) {
  return {
    ok,
    status,
    json: vi.fn().mockResolvedValue(data)
  } as unknown as Response;
}

function generatedResult(overrides: Record<string, any> = {}) {
  return {
    success: true,
    id: 'history-id',
    jd: '<p>Fresh JD</p>',
    email: '<p>Fresh email</p>',
    subject: 'Fresh subject',
    linkedin_title: 'Fresh LinkedIn title',
    titles: ['Fresh title'],
    skills: ['Fresh skill'],
    job_functions: ['Analytics'],
    industries: ['Technology, Information and Media'],
    justifications: {},
    is_domain_page: false,
    ...overrides
  };
}

function cachedRun(overrides: Record<string, any> = {}) {
  return {
    rawJd: 'Same raw JD',
    jobUrl: 'https://old.example/job',
    client: 'mercor',
    domainPageSelection: 'crossing_hurdles',
    outputCheckmarks: { inmail: true, jd: true },
    structuredJd: '<p>Old cached JD</p>',
    emailTemplate: '<p>Old cached email</p>',
    suggestedTitles: 'Cached title',
    subject: 'Cached subject',
    linkedinTitle: 'Cached LinkedIn title',
    skills: ['Cached skill'],
    jobFunctions: ['Analytics'],
    industries: ['Technology, Information and Media'],
    justifications: {},
    isDomainView: false,
    ...overrides
  };
}

class TestBlob {
  parts: any[];
  options: any;
  constructor(parts: any[], options: any) {
    this.parts = parts;
    this.options = options;
  }
}

class TestClipboardItem {
  data: Record<string, TestBlob>;
  constructor(data: Record<string, TestBlob>) {
    this.data = data;
  }
}

function installHtmlClipboard() {
  const clipboardWrite = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { write: clipboardWrite, writeText: vi.fn() }
  });
  vi.stubGlobal('Blob', TestBlob);
  vi.stubGlobal('ClipboardItem', TestClipboardItem);
  return clipboardWrite;
}

function copiedHtml(clipboardWrite: ReturnType<typeof vi.fn>) {
  const item = clipboardWrite.mock.calls[0][0][0] as TestClipboardItem;
  return String(item.data['text/html'].parts[0]);
}

describe('Job Weaver frontend regressions', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem(CACHE_SCOPE_MARKER_KEY, 'local');
    document.documentElement.removeAttribute('data-theme');
    document.documentElement.style.colorScheme = '';
    mockSystemTheme(false);
    vi.stubGlobal('fetch', vi.fn());
  });

  it('uses localhost for development and the Vercel proxy for production', () => {
    expect(resolveApiUrl(undefined, true)).toBe('http://127.0.0.1:8000');
    expect(resolveApiUrl('   ', true)).toBe('http://127.0.0.1:8000');
    expect(resolveApiUrl(undefined, false)).toBe('/api');
    expect(resolveApiUrl('   ', false)).toBe('/api');
    expect(resolveApiUrl('https://api.example.test///', false)).toBe('https://api.example.test');
    expect(shouldUseServerHistory('/api')).toBe(false);
    expect(shouldUseServerHistory('https://api.example.test')).toBe(true);
  });

  it('uses the system dark preference when no theme has been saved', () => {
    mockSystemTheme(true);
    render(<App />);

    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
    expect(document.documentElement.style.colorScheme).toBe('dark');
    const themeToggle = screen.getByRole('button', { name: 'Dark mode' });
    expect(themeToggle).toHaveAttribute('aria-pressed', 'true');
    expect(themeToggle).toHaveTextContent('');
    expect(localStorage.getItem(COLOR_THEME_STORAGE_KEY)).toBe('dark');
  });

  it('restores a saved light theme even when the system prefers dark', () => {
    mockSystemTheme(true);
    localStorage.setItem(COLOR_THEME_STORAGE_KEY, 'light');
    render(<App />);

    expect(document.documentElement).toHaveAttribute('data-theme', 'light');
    expect(screen.getByRole('button', { name: 'Dark mode' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('toggles and persists dark mode across remounts and API identity changes', () => {
    const firstRender = render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Dark mode' }));

    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
    expect(document.documentElement.style.colorScheme).toBe('dark');
    expect(localStorage.getItem(COLOR_THEME_STORAGE_KEY)).toBe('dark');

    firstRender.unmount();
    sessionStorage.setItem(API_TOKEN_SESSION_KEY, 'new-owner-token');
    sessionStorage.removeItem(API_CACHE_SCOPE_SESSION_KEY);
    render(<App />);
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
    expect(screen.getByRole('button', { name: 'Dark mode' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('requires raw JD text even when a job URL is present', () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText('JOB LINK (OPTIONAL)'), {
      target: { value: 'https://example.test/job' }
    });
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }));

    expect(screen.getByText('Please paste the job description. The job link is optional.')).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('rejects non-http job links before sending them to the backend', () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText('JOB LINK (OPTIONAL)'), {
      target: { value: 'javascript:alert(1)' }
    });
    fireEvent.change(screen.getByLabelText('PASTE RAW JOB DESCRIPTION'), {
      target: { value: 'A valid raw JD' }
    });
    fireEvent.submit(screen.getByRole('button', { name: 'Generate' }).closest('form')!);

    expect(screen.getByText('Please enter a valid job link beginning with http:// or https://.')).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('restores the session token and authorizes every API endpoint without leaking it', async () => {
    const token = 'remote-session-secret';
    const summary = {
      id: 'secure-history-id',
      timestamp: '2026-01-01T00:00:00Z',
      client: 'mercor',
      role: 'Secure role',
      raw_jd_snippet: 'Secure raw JD'
    };
    sessionStorage.setItem(API_TOKEN_SESSION_KEY, token);
    vi.mocked(fetch).mockImplementation(async (input, init) => {
      const path = String(input);
      if (path.endsWith('/parse-jd')) {
        return jsonResponse(generatedResult({ id: undefined, _id: undefined }));
      }
      if (path.endsWith('/history/secure-history-id')) {
        return jsonResponse({
          success: true,
          data: {
            ...generatedResult({ id: undefined }),
            _raw_jd: 'Secure raw JD',
            _url: '',
            _client: 'mercor'
          }
        });
      }
      if (init?.method === 'DELETE') {
        return jsonResponse({ success: true });
      }
      return jsonResponse({ success: true, history: [summary] });
    });

    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: 'History' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Load Output' }));
    await screen.findByText('Fresh JD');
    fireEvent.click(screen.getByRole('button', { name: 'History' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Clear All' }));
    await screen.findByText('History and local cache cleared!');

    fireEvent.click(screen.getByRole('button', { name: 'Job Weaver' }));
    fireEvent.change(screen.getByLabelText('PASTE RAW JOB DESCRIPTION'), {
      target: { value: 'Secure raw JD' }
    });
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }));
    await screen.findByText('Fresh JD');

    await waitFor(() => {
      const calls = vi.mocked(fetch).mock.calls;
      expect(calls.some(([input]) => String(input).endsWith('/parse-jd'))).toBe(true);
      expect(calls.some(([input]) => String(input).endsWith('/history/secure-history-id'))).toBe(true);
      expect(calls.some(([input, init]) => String(input).endsWith('/history') && init?.method === 'DELETE')).toBe(true);
      expect(calls.filter(([input, init]) => String(input).endsWith('/history') && !init?.method).length).toBeGreaterThanOrEqual(2);
    });

    vi.mocked(fetch).mock.calls.forEach(([, init]) => {
      expect(new Headers(init?.headers).get('Authorization')).toBe(`Bearer ${token}`);
      expect(String(init?.body || '')).not.toContain(token);
    });
    for (let index = 0; index < localStorage.length; index++) {
      const key = localStorage.key(index)!;
      expect(key).not.toBe(API_TOKEN_SESSION_KEY);
      expect(localStorage.getItem(key)).not.toContain(token);
    }
    expect(sessionStorage.getItem(API_TOKEN_SESSION_KEY)).toBe(token);
  });

  it('keeps the remote API token control out of the interface', () => {
    render(<App />);

    expect(screen.queryByText('Advanced / Remote API')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('BEARER TOKEN')).not.toBeInTheDocument();
  });

  it('clears cached user data when the API identity changes', () => {
    const aliceScope = 'alice-session-scope';
    const aliceCacheKey = `${LAST_RUN_CACHE_KEY}_${aliceScope}`;
    sessionStorage.setItem(API_TOKEN_SESSION_KEY, 'alice-token');
    sessionStorage.setItem(API_CACHE_SCOPE_SESSION_KEY, aliceScope);
    localStorage.setItem(CACHE_SCOPE_MARKER_KEY, aliceScope);
    localStorage.setItem(aliceCacheKey, JSON.stringify(cachedRun({ rawJd: 'Alice private JD' })));

    const aliceRender = render(<App />);
    expect(screen.getByRole('button', { name: /Forward/ })).toBeInTheDocument();
    aliceRender.unmount();
    sessionStorage.setItem(API_TOKEN_SESSION_KEY, 'bob-token');
    sessionStorage.removeItem(API_CACHE_SCOPE_SESSION_KEY);
    render(<App />);

    expect(localStorage.getItem(aliceCacheKey)).toBeNull();
    expect(screen.queryByRole('button', { name: /Forward/ })).not.toBeInTheDocument();
    expect(screen.getByLabelText('PASTE RAW JOB DESCRIPTION')).toHaveValue('');
    expect(JSON.stringify(localStorage)).not.toContain('Alice private JD');
    expect(sessionStorage.getItem(API_TOKEN_SESSION_KEY)).toBe('bob-token');
    expect(sessionStorage.getItem(API_CACHE_SCOPE_SESSION_KEY)).not.toBe(aliceScope);
  });

  it('drops authenticated cache data when its session identity is no longer present', () => {
    const staleScope = 'closed-alice-session';
    const staleCacheKey = `${LAST_RUN_CACHE_KEY}_${staleScope}`;
    localStorage.setItem(CACHE_SCOPE_MARKER_KEY, staleScope);
    localStorage.setItem(staleCacheKey, JSON.stringify(cachedRun({ rawJd: 'Stale private JD' })));

    render(<App />);

    expect(localStorage.getItem(staleCacheKey)).toBeNull();
    expect(screen.queryByRole('button', { name: /Forward/ })).not.toBeInTheDocument();
    expect(JSON.stringify(localStorage)).not.toContain('Stale private JD');
  });

  it('omits Authorization when no runtime token is configured', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(generatedResult()));
    render(<App />);
    fireEvent.change(screen.getByLabelText('PASTE RAW JOB DESCRIPTION'), {
      target: { value: 'A valid raw JD' }
    });
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }));

    await screen.findByText('Fresh JD');
    const [requestUrl, init] = vi.mocked(fetch).mock.calls[0];
    expect(requestUrl).toBe('http://127.0.0.1:8000/parse-jd');
    expect(new Headers(init?.headers).get('Authorization')).toBeNull();
  });

  it('stores a generated history summary and detail in the browser cache', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(generatedResult({
      structured_data: { role: 'Locally saved role' }
    })));
    render(<App />);
    fireEvent.change(screen.getByLabelText('PASTE RAW JOB DESCRIPTION'), {
      target: { value: 'A locally saved raw JD' }
    });
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }));

    await screen.findByText('Fresh JD');
    await waitFor(() => {
      const history = JSON.parse(localStorage.getItem(HISTORY_CACHE_KEY) || '[]');
      expect(history).toEqual(expect.arrayContaining([
        expect.objectContaining({
          id: 'history-id',
          client: 'mercor',
          role: 'Locally saved role',
          raw_jd_snippet: 'A locally saved raw JD'
        })
      ]));
      expect(localStorage.getItem(`${DETAIL_CACHE_PREFIX}history-id`)).toContain('Fresh JD');
    });
  });

  it('reports the API location and status for a non-JSON response', async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 404,
      json: vi.fn().mockRejectedValue(new SyntaxError('Unexpected end of JSON input'))
    } as unknown as Response);
    render(<App />);
    fireEvent.change(screen.getByLabelText('PASTE RAW JOB DESCRIPTION'), {
      target: { value: 'A valid raw JD' }
    });
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }));

    expect(await screen.findByText(
      'The Job Weaver API returned an unreadable response (HTTP 404). Make sure the backend is running at http://127.0.0.1:8000.'
    )).toBeInTheDocument();
  });

  it('surfaces a 401 without exposing or persisting the bearer token', async () => {
    const token = 'rejected-secret-token';
    sessionStorage.setItem(API_TOKEN_SESSION_KEY, token);
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ detail: 'Invalid API token' }, false, 401));
    render(<App />);
    fireEvent.change(screen.getByLabelText('PASTE RAW JOB DESCRIPTION'), {
      target: { value: 'A valid raw JD' }
    });
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }));

    const error = await screen.findByText('Invalid API token');
    expect(error).not.toHaveTextContent(token);
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(new Headers(init?.headers).get('Authorization')).toBe(`Bearer ${token}`);
    expect(JSON.stringify(localStorage)).not.toContain(token);
    expect(sessionStorage.getItem(API_TOKEN_SESSION_KEY)).toBe(token);
  });

  it('surfaces an application-level backend error instead of showing empty output', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ success: false, error: 'Backend generation failed' }));
    render(<App />);
    fireEvent.change(screen.getByLabelText('PASTE RAW JOB DESCRIPTION'), {
      target: { value: 'A valid raw JD' }
    });
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }));

    expect(await screen.findByText('Backend generation failed')).toBeInTheDocument();
    expect(screen.queryByText('Job Description')).not.toBeInTheDocument();
  });

  it('formats FastAPI validation details into a readable error', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({
      detail: [{ loc: ['body', 'raw_jd'], msg: 'Field required', type: 'missing' }]
    }, false));
    render(<App />);
    fireEvent.change(screen.getByLabelText('PASTE RAW JOB DESCRIPTION'), {
      target: { value: 'A valid raw JD' }
    });
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }));

    expect(await screen.findByText('raw_jd: Field required')).toBeInTheDocument();
  });

  it('sanitizes generated HTML before rendering or caching it', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(generatedResult({
      id: 'unsafe-generated-id',
      jd: '<p onclick="alert(1)">Safe <a href="javascript:alert(2)" onmouseover="alert(3)" style="color: #0066cc; position: fixed">link</a><img src="x" onerror="alert(4)"><script>alert(5)</script></p>'
    })));
    render(<App />);
    fireEvent.change(screen.getByLabelText('PASTE RAW JOB DESCRIPTION'), {
      target: { value: 'A valid raw JD' }
    });
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }));

    const editor = await screen.findByRole('textbox', { name: 'Editable job description' });
    const paragraph = editor.querySelector('p')!;
    const link = editor.querySelector('a')!;
    expect(paragraph).not.toHaveAttribute('onclick');
    expect(link).not.toHaveAttribute('href');
    expect(link).not.toHaveAttribute('onmouseover');
    expect(link.getAttribute('style')).toContain('color');
    expect(link.getAttribute('style')).not.toContain('position');
    expect(editor.querySelector('img')).toBeNull();
    expect(editor.querySelector('script')).toBeNull();

    const cached = JSON.parse(localStorage.getItem(`${DETAIL_CACHE_PREFIX}unsafe-generated-id`)!);
    expect(cached.jd).not.toMatch(/onclick|onmouseover|javascript:|<script|<img/i);
  });

  it('sanitizes persisted history HTML before restoring it', async () => {
    const summary = {
      id: 'unsafe-history-id',
      timestamp: '2026-01-01T00:00:00Z',
      client: 'mercor',
      role: 'History role'
    };
    vi.mocked(fetch).mockImplementation(async input =>
      String(input).endsWith('/history')
        ? jsonResponse({ success: true, history: [summary] })
        : jsonResponse({
          success: true,
          data: {
            ...generatedResult({ id: undefined }),
            jd: '<p onfocus="alert(1)">History <a href="javascript:alert(2)">link</a></p>',
            _raw_jd: 'History raw JD',
            _client: 'mercor'
          }
        })
    );
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'History' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Load Output' }));

    const editor = await screen.findByRole('textbox', { name: 'Editable job description' });
    expect(editor.querySelector('p')).not.toHaveAttribute('onfocus');
    expect(editor.querySelector('a')).not.toHaveAttribute('href');
    const cached = JSON.parse(localStorage.getItem(`${DETAIL_CACHE_PREFIX}unsafe-history-id`)!);
    expect(cached.jd).not.toMatch(/onfocus|javascript:/i);
  });

  it('does not reuse last-run output when the job URL changes', async () => {
    localStorage.setItem(LAST_RUN_CACHE_KEY, JSON.stringify(cachedRun()));
    vi.mocked(fetch).mockResolvedValue(jsonResponse(generatedResult()));
    render(<App />);
    fireEvent.change(screen.getByLabelText('JOB LINK (OPTIONAL)'), {
      target: { value: 'https://new.example/job' }
    });
    fireEvent.change(screen.getByLabelText('PASTE RAW JOB DESCRIPTION'), {
      target: { value: 'Same raw JD' }
    });
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }));

    expect(await screen.findByText('Fresh JD')).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('ignores and removes the pre-versioned last-run cache', () => {
    localStorage.setItem('job_weaver_last_run', JSON.stringify(cachedRun()));
    localStorage.setItem('job_weaver_history', JSON.stringify([{ id: 'old-id' }]));
    localStorage.setItem('jw_detail_old-id', JSON.stringify({ jd: 'Old unsafe output' }));
    render(<App />);

    expect(screen.queryByRole('button', { name: /Forward/ })).not.toBeInTheDocument();
    expect(localStorage.getItem('job_weaver_last_run')).toBeNull();
    expect(localStorage.getItem('job_weaver_history')).toBeNull();
    expect(localStorage.getItem('jw_detail_old-id')).toBeNull();
  });

  it('includes domain output selection in the last-run cache identity', async () => {
    localStorage.setItem(LAST_RUN_CACHE_KEY, JSON.stringify(cachedRun({
      client: 'domain_page',
      isDomainView: true,
      jobUrl: ''
    })));
    vi.mocked(fetch).mockResolvedValue(jsonResponse(generatedResult({
      inmail_draft: '<p>Fresh domain email</p>',
      email: '',
      is_domain_page: true
    })));
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Domain Page' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Job Description' }));
    fireEvent.change(screen.getByLabelText('PASTE RAW JOB DESCRIPTION'), {
      target: { value: 'Same raw JD' }
    });
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }));

    expect(await screen.findByText('Fresh domain email')).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('preserves empty generated metadata instead of inventing fallback values', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(generatedResult({
      titles: [],
      skills: [],
      job_functions: [],
      industries: []
    })));
    render(<App />);
    fireEvent.change(screen.getByLabelText('PASTE RAW JOB DESCRIPTION'), {
      target: { value: 'A role without metadata' }
    });
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }));

    await screen.findByText('Fresh JD');
    expect(screen.queryByText('Data Evaluation')).not.toBeInTheDocument();
    expect(screen.queryByText('Content Analyst (Media & Insights)')).not.toBeInTheDocument();
    const cached = JSON.parse(localStorage.getItem(LAST_RUN_CACHE_KEY)!);
    expect(cached.suggestedTitles).toBe('');
    expect(cached.skills).toEqual([]);
    expect(cached.jobFunctions).toEqual([]);
    expect(cached.industries).toEqual([]);
  });

  it('keeps successful output visible when browser storage quota is exhausted', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(generatedResult()));
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('Quota exceeded', 'QuotaExceededError');
    });
    render(<App />);
    fireEvent.change(screen.getByLabelText('PASTE RAW JOB DESCRIPTION'), {
      target: { value: 'A valid raw JD' }
    });
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }));

    expect(await screen.findByText('Fresh JD')).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Editable job description' })).toBeInTheDocument();
  });

  it('sanitizes and copies the current contentEditable HTML rather than stale state', async () => {
    localStorage.setItem(LAST_RUN_CACHE_KEY, JSON.stringify(cachedRun()));
    const clipboardWrite = installHtmlClipboard();

    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /Forward/ }));
    const editor = await screen.findByRole('textbox', { name: 'Editable job description' });
    editor.innerHTML = '<p onclick="alert(1)">Edited <a href="javascript:alert(2)" onmouseover="alert(3)">JD</a></p>';
    fireEvent.click(screen.getByRole('button', { name: 'Copy JD' }));

    await waitFor(() => expect(clipboardWrite).toHaveBeenCalled());
    const copiedContainer = document.createElement('div');
    copiedContainer.innerHTML = copiedHtml(clipboardWrite);
    expect(copiedContainer.textContent).toBe('Edited JD');
    expect(copiedContainer.querySelector('p')).not.toHaveAttribute('onclick');
    expect(copiedContainer.querySelector('a')).not.toHaveAttribute('href');
    expect(copiedContainer.querySelector('a')).not.toHaveAttribute('onmouseover');
  });

  it('copies an intentionally emptied editor instead of falling back to stale HTML', async () => {
    localStorage.setItem(LAST_RUN_CACHE_KEY, JSON.stringify(cachedRun()));
    const clipboardWrite = installHtmlClipboard();
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /Forward/ }));
    const editor = await screen.findByRole('textbox', { name: 'Editable job description' });
    editor.innerHTML = '';
    fireEvent.click(screen.getByRole('button', { name: 'Copy JD' }));

    await waitFor(() => expect(clipboardWrite).toHaveBeenCalled());
    expect(copiedHtml(clipboardWrite)).toBe('');
  });

  it('clears server history and every Job Weaver local cache key', async () => {
    const summary = {
      id: 'history-id',
      timestamp: '2026-01-01T00:00:00Z',
      client: 'mercor',
      role: 'Private role'
    };
    localStorage.setItem(LAST_RUN_CACHE_KEY, JSON.stringify(cachedRun()));
    localStorage.setItem(HISTORY_CACHE_KEY, JSON.stringify([summary]));
    localStorage.setItem(`${DETAIL_CACHE_PREFIX}history-id`, JSON.stringify({ _raw_jd: 'Private JD' }));
    localStorage.setItem(COLOR_THEME_STORAGE_KEY, 'dark');
    localStorage.setItem('unrelated_key', 'keep');
    vi.mocked(fetch).mockImplementation(async (_input, init) =>
      init?.method === 'DELETE'
        ? jsonResponse({ success: true })
        : jsonResponse({ success: true, history: [summary] })
    );

    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'History' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Clear All' }));

    expect(await screen.findByText('History and local cache cleared!')).toBeInTheDocument();
    expect(localStorage.getItem(LAST_RUN_CACHE_KEY)).toBeNull();
    expect(localStorage.getItem(HISTORY_CACHE_KEY)).toBeNull();
    expect(localStorage.getItem(`${DETAIL_CACHE_PREFIX}history-id`)).toBeNull();
    expect(localStorage.getItem(COLOR_THEME_STORAGE_KEY)).toBe('dark');
    expect(localStorage.getItem('unrelated_key')).toBe('keep');
  });

  it('clears local history and reports a partial failure when the server clear fails', async () => {
    const summary = {
      id: 'history-id',
      timestamp: '2026-01-01T00:00:00Z',
      client: 'mercor',
      role: 'Private role'
    };
    localStorage.setItem(HISTORY_CACHE_KEY, JSON.stringify([summary]));
    localStorage.setItem(`${DETAIL_CACHE_PREFIX}history-id`, JSON.stringify({ _raw_jd: 'Private JD' }));
    vi.mocked(fetch).mockImplementation(async (_input, init) =>
      init?.method === 'DELETE'
        ? jsonResponse({ success: false, error: 'Server refused to clear history' })
        : jsonResponse({ success: true, history: [summary] })
    );

    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'History' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Clear All' }));

    expect(await screen.findByText('Local history cleared, but server history could not be cleared: Server refused to clear history')).toBeInTheDocument();
    expect(localStorage.getItem(HISTORY_CACHE_KEY)).toBeNull();
    expect(localStorage.getItem(`${DETAIL_CACHE_PREFIX}history-id`)).toBeNull();
  });

  it('persists a generated history detail as soon as the API returns its id', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(generatedResult({ id: 'generated-id' })));
    render(<App />);
    fireEvent.change(screen.getByLabelText('PASTE RAW JOB DESCRIPTION'), {
      target: { value: 'A generated raw JD' }
    });
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }));

    await screen.findByText('Fresh JD');
    await waitFor(() => expect(localStorage.getItem(`${DETAIL_CACHE_PREFIX}generated-id`)).not.toBeNull());
    const detail = JSON.parse(localStorage.getItem(`${DETAIL_CACHE_PREFIX}generated-id`)!);
    expect(detail._raw_jd).toBe('A generated raw JD');
    expect(detail._output_selection).toEqual({ inmail: true, jd: true });
  });

  it('uses native buttons for client, domain, and output selectors', async () => {
    render(<App />);
    const domainClient = screen.getByRole('button', { name: 'Domain Page' });
    expect(domainClient.tagName).toBe('BUTTON');
    fireEvent.click(domainClient);

    expect((await screen.findByRole('button', { name: 'STEMSyncAI' })).tagName).toBe('BUTTON');
    expect(screen.getByRole('button', { name: 'InMail Draft' }).tagName).toBe('BUTTON');
  });
});
