import { useLayoutEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import DOMPurify, { type Config } from 'dompurify';
import {
  ArrowRight, ArrowLeft, History, Link, Check, Moon, Sun
} from 'lucide-react';
import TetrisLoading from './components/ui/tetris-loader';

const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();
const API_URL = (
  configuredApiUrl || (import.meta.env.DEV ? "http://127.0.0.1:8000" : "")
).replace(/\/+$/, "");

const API_TOKEN_SESSION_KEY = 'job_weaver_api_token';
const API_CACHE_SCOPE_SESSION_KEY = 'job_weaver_api_cache_scope';
const CACHE_SCOPE_MARKER_KEY = 'job_weaver_cache_scope_v2';
const LAST_RUN_CACHE_KEY = 'job_weaver_last_run_v2';
const LEGACY_LAST_RUN_CACHE_KEY = 'job_weaver_last_run';
const HISTORY_CACHE_KEY = 'job_weaver_history_v2';
const LEGACY_HISTORY_CACHE_KEY = 'job_weaver_history';
const DETAIL_CACHE_PREFIX = 'jw_detail_v2_';
const LEGACY_DETAIL_CACHE_PREFIX = 'jw_detail_';
const LOCAL_CACHE_SCOPE = 'local';
const COLOR_THEME_STORAGE_KEY = 'job-weaver-color-theme';

type ColorTheme = 'light' | 'dark';

function getInitialColorTheme(): ColorTheme {
  try {
    const storedTheme = localStorage.getItem(COLOR_THEME_STORAGE_KEY);
    if (storedTheme === 'light' || storedTheme === 'dark') return storedTheme;
  } catch {
    // Fall through to the operating-system preference when storage is blocked.
  }
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

const DOMAIN_PAGES = new Set([
  'crossing_hurdles',
  'codegeniusrecruit',
  'curasenseai',
  'legaltrustai',
  'capitexai',
  'stemsyncai',
  'linguasenseai',
  'designmeshai'
]);

type OutputSelection = { inmail: boolean; jd: boolean };

const RICH_TEXT_SANITIZE_CONFIG: Config = {
  ALLOWED_TAGS: [
    'a', 'b', 'blockquote', 'br', 'code', 'div', 'em', 'h1', 'h2', 'h3',
    'h4', 'h5', 'h6', 'i', 'li', 'ol', 'p', 'pre', 's', 'span', 'strong',
    'u', 'ul'
  ],
  ALLOWED_ATTR: ['href', 'style', 'title'],
  ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|tel):|[^a-z]|[a-z0-9+.-]+(?:[^a-z0-9+.-:]|$))/i,
  ALLOW_ARIA_ATTR: false,
  ALLOW_DATA_ATTR: false
};

const SAFE_INLINE_STYLE_PROPERTIES = [
  'color',
  'font-weight',
  'text-decoration'
] as const;

const OUTPUT_HTML_FIELDS = [
  'jd',
  'email',
  'email_draft',
  'inmail_draft',
  'structuredJd',
  'emailTemplate'
] as const;

function sanitizeHtml(value: unknown) {
  if (typeof value !== 'string' || !value) return '';

  const purified = DOMPurify.sanitize(value, RICH_TEXT_SANITIZE_CONFIG);
  const template = document.createElement('template');
  template.innerHTML = purified;

  template.content.querySelectorAll<HTMLElement>('[style]').forEach(element => {
    const safeDeclarations: string[] = [];
    SAFE_INLINE_STYLE_PROPERTIES.forEach(property => {
      const propertyValue = element.style.getPropertyValue(property).trim();
      if (!propertyValue) return;
      const priority = element.style.getPropertyPriority(property);
      safeDeclarations.push(`${property}: ${propertyValue}${priority ? ` !${priority}` : ''}`);
    });

    if (safeDeclarations.length > 0) {
      element.setAttribute('style', safeDeclarations.join('; '));
    } else {
      element.removeAttribute('style');
    }
  });

  return template.innerHTML;
}

function sanitizeOutputPayload(payload: any) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return payload;
  const sanitized = { ...payload };
  OUTPUT_HTML_FIELDS.forEach(field => {
    if (typeof sanitized[field] === 'string') {
      sanitized[field] = sanitizeHtml(sanitized[field]);
    }
  });
  return sanitized;
}

function normalizeStringArray(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : [];
}

function normalizeCachedTitleText(value: unknown) {
  return typeof value === 'string' ? value : '';
}

function apiEndpoint(path: string) {
  return `${API_URL}${path}`;
}

function apiFetch(path: string, token: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  const normalizedToken = token.trim();
  if (normalizedToken) {
    headers.set('Authorization', `Bearer ${normalizedToken}`);
  }
  return fetch(apiEndpoint(path), { ...init, headers });
}

function readSessionApiToken() {
  try {
    return sessionStorage.getItem(API_TOKEN_SESSION_KEY) || '';
  } catch {
    return '';
  }
}

function persistSessionApiToken(token: string) {
  try {
    if (token) {
      sessionStorage.setItem(API_TOKEN_SESSION_KEY, token);
    } else {
      sessionStorage.removeItem(API_TOKEN_SESSION_KEY);
    }
  } catch (error) {
    console.warn('The API token could not be saved for this browser session.', error);
  }
}

function safeLocalStorageSet(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
    return true;
  } catch (error) {
    console.warn(`Local cache write failed for ${key}.`, error);
    return false;
  }
}

function removeLocalJobData() {
  const keys = new Set([
    LAST_RUN_CACHE_KEY,
    LEGACY_LAST_RUN_CACHE_KEY,
    HISTORY_CACHE_KEY,
    LEGACY_HISTORY_CACHE_KEY,
    CACHE_SCOPE_MARKER_KEY
  ]);

  try {
    for (let index = 0; index < localStorage.length; index++) {
      const key = localStorage.key(index);
      if (key && (key.startsWith('job_weaver_') || key.startsWith('jw_detail_'))) {
        keys.add(key);
      }
    }
  } catch (error) {
    console.error('Could not enumerate all local Job Weaver data:', error);
  }

  keys.forEach(key => {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error(`Could not remove local cache key ${key}:`, error);
    }
  });
}

function removeLegacyLocalData() {
  try {
    localStorage.removeItem(LEGACY_LAST_RUN_CACHE_KEY);
    localStorage.removeItem(LEGACY_HISTORY_CACHE_KEY);
    const legacyDetailKeys: string[] = [];
    for (let index = 0; index < localStorage.length; index++) {
      const key = localStorage.key(index);
      if (key?.startsWith(LEGACY_DETAIL_CACHE_PREFIX) && !key.startsWith(DETAIL_CACHE_PREFIX)) {
        legacyDetailKeys.push(key);
      }
    }
    legacyDetailKeys.forEach(key => localStorage.removeItem(key));
  } catch (error) {
    console.error('Could not remove legacy Job Weaver cache data:', error);
  }
}

function createCacheScope() {
  try {
    if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    return Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
  } catch {
    return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }
}

function persistSessionCacheScope(scope: string | null) {
  try {
    if (scope) sessionStorage.setItem(API_CACHE_SCOPE_SESSION_KEY, scope);
    else sessionStorage.removeItem(API_CACHE_SCOPE_SESSION_KEY);
  } catch (error) {
    console.warn('The API cache scope could not be saved for this browser session.', error);
  }
}

function prepareCacheScope(token: string) {
  removeLegacyLocalData();
  const authenticated = Boolean(token.trim());
  let scope = LOCAL_CACHE_SCOPE;
  try {
    if (authenticated) {
      scope = sessionStorage.getItem(API_CACHE_SCOPE_SESSION_KEY) || createCacheScope();
      persistSessionCacheScope(scope);
    } else {
      persistSessionCacheScope(null);
    }

    const marker = localStorage.getItem(CACHE_SCOPE_MARKER_KEY);
    // No cache is trusted without the exact session/local identity marker.
    if (marker !== scope) {
      removeLocalJobData();
    }
    safeLocalStorageSet(CACHE_SCOPE_MARKER_KEY, scope);
  } catch (error) {
    console.error('Could not prepare the local Job Weaver cache scope:', error);
  }
  return scope;
}

function rotateCacheScope(token: string) {
  removeLocalJobData();
  const scope = token.trim() ? createCacheScope() : LOCAL_CACHE_SCOPE;
  persistSessionCacheScope(token.trim() ? scope : null);
  safeLocalStorageSet(CACHE_SCOPE_MARKER_KEY, scope);
  return scope;
}

function scopedCacheKey(baseKey: string, scope: string) {
  return scope === LOCAL_CACHE_SCOPE ? baseKey : `${baseKey}_${scope}`;
}

function detailCacheKey(itemId: string, scope: string) {
  return `${DETAIL_CACHE_PREFIX}${scope === LOCAL_CACHE_SCOPE ? '' : `${scope}_`}${itemId}`;
}

function normalizeOutputSelection(value: any): OutputSelection {
  return {
    inmail: value?.inmail !== false,
    jd: value?.jd !== false
  };
}

function outputSelectionsMatch(left: any, right: OutputSelection) {
  const normalized = normalizeOutputSelection(left);
  return normalized.inmail === right.inmail && normalized.jd === right.jd;
}

function normalizeRawJd(text: string) {
  return (text || "")
    .replace(/\r\n?/g, "\n")
    .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, "")
    .split("\n")
    .map(line => line.trim())
    .filter(Boolean)
    .join("\n");
}

function buildHistorySnippet(text: string) {
  const normalized = normalizeRawJd(text);
  return normalized.slice(0, 150) + (normalized.length > 150 ? "..." : "");
}

function isSafeJobUrl(value: string) {
  if (!value.trim()) return true;
  try {
    const parsed = new URL(value.trim());
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function apiErrorMessage(data: any, fallback: string) {
  const detail = data?.detail ?? data?.error;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map(item => {
      if (typeof item === "string") return item;
      const message = typeof item?.msg === "string" ? item.msg : "";
      const location = Array.isArray(item?.loc)
        ? item.loc.filter((part: any) => part !== "body").join(".")
        : "";
      return location && message ? `${location}: ${message}` : message;
    }).filter(Boolean);
    if (messages.length > 0) return messages.join("; ");
  }
  if (detail && typeof detail === "object" && typeof detail.msg === "string") {
    return detail.msg;
  }
  return fallback;
}

function splitParts(text: string) {
  if (!text) return { prefix: "", suffix: "" };
  const parts = text.split("|");
  return {
    prefix: parts[0]?.trim() || "",
    suffix: parts.slice(1).join("|").trim()
  };
}

export default function App() {
  const [colorTheme, setColorTheme] = useState<ColorTheme>(getInitialColorTheme);
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [client, setClient] = useState('mercor');
  const [jobUrl, setJobUrl] = useState('');
  const [rawJd, setRawJd] = useState('');
  const [structuredJd, setStructuredJd] = useState('');
  const [emailTemplate, setEmailTemplate] = useState('');
  const [suggestedTitles, setSuggestedTitles] = useState('');
  const [subject, setSubject] = useState('');
  const [linkedinTitle, setLinkedinTitle] = useState('');
  const [skills, setSkills] = useState<string[]>([]);
  const [jobFunctions, setJobFunctions] = useState<string[]>([]);
  const [industries, setIndustries] = useState<string[]>([]);
  const [justifications, setJustifications] = useState<Record<string, string>>({});
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [mirrorSync, setMirrorSync] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingStep, setLoadingStep] = useState("");
  const [isDomainView, setIsDomainView] = useState(false);
  const [domainPageSelection, setDomainPageSelection] = useState("crossing_hurdles");
  const [outputCheckmarks, setOutputCheckmarks] = useState<OutputSelection>({ inmail: true, jd: true });
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [historyItems, setHistoryItems] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [hoveredLinkUrl, setHoveredLinkUrl] = useState<string | null>(null);
  const [apiToken, setApiToken] = useState(readSessionApiToken);
  const [cacheScope, setCacheScope] = useState(() => prepareCacheScope(apiToken));

  const [lastRunData, setLastRunData] = useState<any>(() => {
    try {
      const saved = localStorage.getItem(scopedCacheKey(LAST_RUN_CACHE_KEY, cacheScope));
      return saved ? sanitizeOutputPayload(JSON.parse(saved)) : null;
    } catch (e) {
      return null;
    }
  });

  useLayoutEffect(() => {
    document.documentElement.dataset.theme = colorTheme;
    document.documentElement.style.colorScheme = colorTheme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute(
      'content',
      colorTheme === 'dark' ? '#080f1d' : '#f8fafc'
    );
    try {
      localStorage.setItem(COLOR_THEME_STORAGE_KEY, colorTheme);
    } catch (error) {
      console.warn('The color theme preference could not be saved.', error);
    }
  }, [colorTheme]);

  const handleApiTokenChange = (token: string) => {
    if (token.trim() !== apiToken.trim()) {
      setCacheScope(rotateCacheScope(token));
      setLastRunData(null);
      setHistoryItems([]);
      setRawJd('');
      setJobUrl('');
      setStructuredJd('');
      setEmailTemplate('');
      setSuggestedTitles('');
      setSubject('');
      setLinkedinTitle('');
      setSkills([]);
      setJobFunctions([]);
      setIndustries([]);
      setJustifications({});
      setError(null);
      setStep(1);
    }
    setApiToken(token);
    persistSessionApiToken(token);
  };


  const fetchHistory = async () => {
    try {
      setLoadingHistory(true);
      const localStr = localStorage.getItem(scopedCacheKey(HISTORY_CACHE_KEY, cacheScope));
      let localHist: any[] = [];
      if (localStr) {
        try {
          const parsed = JSON.parse(localStr);
          localHist = Array.isArray(parsed) ? parsed : [];
        } catch (e) { }
      }
      setHistoryItems(localHist);

      const res = await apiFetch("/history", apiToken);
      const data = await res.json();
      if (res.ok === false || !data.success) {
        throw new Error(apiErrorMessage(data, "Could not fetch history."));
      }
      if (data.success && Array.isArray(data.history)) {
        const map = new Map();
        [...data.history, ...localHist].forEach((it: any) => {
          if (it && it.id && !map.has(it.id)) map.set(it.id, it);
        });
        const merged = Array.from(map.values()).sort((a: any, b: any) =>
          new Date(b.timestamp || 0).getTime() - new Date(a.timestamp || 0).getTime()
        );
        setHistoryItems(merged);
        safeLocalStorageSet(scopedCacheKey(HISTORY_CACHE_KEY, cacheScope), JSON.stringify(merged));
      }
    } catch (e) {
      console.error("Error fetching history from backend, showing local cache:", e);
    } finally {
      setLoadingHistory(false);
    }
  };

  const loadHistoryItem = async (itemId: string) => {
    try {
      setLoadingStep("Loading from cache...");
      setStep(2);
      setShowHistoryModal(false);
      let payload: any = null;

      try {
        const res = await apiFetch(`/history/${encodeURIComponent(itemId)}`, apiToken);
        const data = await res.json();
        if (res.ok !== false && data.success && data.data) {
          let cachedSelection: any = outputCheckmarks;
          const existingDetail = localStorage.getItem(detailCacheKey(itemId, cacheScope));
          if (existingDetail) {
            try {
              cachedSelection = JSON.parse(existingDetail)?._output_selection || outputCheckmarks;
            } catch (e) { }
          }
          payload = sanitizeOutputPayload({
            ...data.data,
            _output_selection: normalizeOutputSelection(data.data._output_selection || cachedSelection)
          });
          safeLocalStorageSet(detailCacheKey(itemId, cacheScope), JSON.stringify(payload));
        }
      } catch (err) {
        console.error("Backend fetch failed, checking localStorage detail...");
      }

      if (!payload) {
        const localDetailStr = localStorage.getItem(detailCacheKey(itemId, cacheScope));
        if (localDetailStr) {
          try {
            payload = sanitizeOutputPayload(JSON.parse(localDetailStr));
            safeLocalStorageSet(detailCacheKey(itemId, cacheScope), JSON.stringify(payload));
          } catch (e) { }
        }
      }

      if (payload) {
        const restoredRawJd = typeof payload._raw_jd === "string" ? payload._raw_jd : rawJd;
        const restoredJobUrl = typeof payload._url === "string" ? payload._url : jobUrl;
        const restoredSelection = normalizeOutputSelection(payload._output_selection || outputCheckmarks);
        const restoredClient = DOMAIN_PAGES.has(payload._client) ? "domain_page" : (payload._client || client);

        setRawJd(restoredRawJd);
        setJobUrl(restoredJobUrl);
        setOutputCheckmarks(restoredSelection);
        if (payload._client) {
          if (DOMAIN_PAGES.has(payload._client)) {
            setClient("domain_page");
            setDomainPageSelection(payload._client);
          } else {
            setClient(payload._client);
          }
        }

        const loadedTitles = normalizeStringArray(payload.titles);
        const loadedSkills = normalizeStringArray(payload.skills);
        const loadedFunctions = normalizeStringArray(payload.job_functions);
        const loadedIndustries = normalizeStringArray(payload.industries);

        setStructuredJd(payload.jd || "");
        setEmailTemplate(payload.email || payload.inmail_draft || "");
        setSuggestedTitles(loadedTitles.join("\n"));
        setSubject(payload.subject || "");
        setLinkedinTitle(payload.linkedin_title || "");
        setSkills(loadedSkills);
        setJobFunctions(loadedFunctions);
        setIndustries(loadedIndustries);
        setJustifications(payload.justifications || {});
        setIsDomainView(payload.is_domain_page || DOMAIN_PAGES.has(payload._client) || payload._client === "domain_page");

        const restoredRun = {
          rawJd: restoredRawJd,
          jobUrl: restoredJobUrl,
          client: restoredClient,
          domainPageSelection: DOMAIN_PAGES.has(payload._client) ? payload._client : domainPageSelection,
          outputCheckmarks: restoredSelection,
          structuredJd: payload.jd || "",
          emailTemplate: payload.email || payload.inmail_draft || "",
          suggestedTitles: loadedTitles.join("\n"),
          subject: payload.subject || "",
          linkedinTitle: payload.linkedin_title || "",
          skills: loadedSkills,
          jobFunctions: loadedFunctions,
          industries: loadedIndustries,
          justifications: payload.justifications || {},
          isDomainView: payload.is_domain_page || DOMAIN_PAGES.has(payload._client)
        };
        setLastRunData(restoredRun);
        safeLocalStorageSet(scopedCacheKey(LAST_RUN_CACHE_KEY, cacheScope), JSON.stringify(restoredRun));

        setStep(3);
      } else {
        showToast("Could not load history item.");
        setStep(1);
      }
    } catch (e) {
      console.error(e);
      showToast("Error loading history item.");
      setStep(1);
    }
  };

  const clearHistory = async () => {
    const keysToRemove = new Set([
      HISTORY_CACHE_KEY,
      LEGACY_HISTORY_CACHE_KEY,
      LAST_RUN_CACHE_KEY,
      LEGACY_LAST_RUN_CACHE_KEY
    ]);
    let localCleanupFailed = false;

    try {
      for (let index = 0; index < localStorage.length; index++) {
        const key = localStorage.key(index);
        if (key && (key.startsWith("job_weaver_") || key.startsWith("jw_detail_"))) {
          keysToRemove.add(key);
        }
      }
    } catch (error) {
      localCleanupFailed = true;
      console.error('Could not enumerate all local Job Weaver data:', error);
    }

    keysToRemove.forEach(key => {
      try {
        localStorage.removeItem(key);
      } catch (error) {
        localCleanupFailed = true;
        console.error(`Could not remove local cache key ${key}:`, error);
      }
    });
    setHistoryItems([]);
    setLastRunData(null);
    safeLocalStorageSet(CACHE_SCOPE_MARKER_KEY, cacheScope);

    let serverError: Error | null = null;
    try {
      const res = await apiFetch("/history", apiToken, { method: "DELETE" });
      const data = await res.json();
      if (res.ok === false || !data.success) {
        throw new Error(apiErrorMessage(data, "Could not clear server history."));
      }
    } catch (error: any) {
      serverError = error instanceof Error
        ? error
        : new Error("Could not clear server history.");
      console.error("Error clearing server history:", error);
    }

    if (serverError) {
      showToast(`Local history cleared, but server history could not be cleared: ${serverError.message}`);
    } else if (localCleanupFailed) {
      showToast("Server history cleared, but some local cache data could not be removed.");
    } else {
      showToast("History and local cache cleared!");
    }
  };

  const persistGeneratedHistory = async (
    data: any,
    effectiveClient: string,
    selection: OutputSelection
  ) => {
    const sanitizedData = sanitizeOutputPayload(data);
    const detail = {
      ...sanitizedData,
      _raw_jd: rawJd,
      _url: jobUrl,
      _client: effectiveClient,
      _output_selection: selection
    };
    let itemId = sanitizedData._id || sanitizedData.id;

    if (itemId) {
      try {
        safeLocalStorageSet(detailCacheKey(itemId, cacheScope), JSON.stringify(detail));
      } catch (e) {
        console.error("Generated output could not be saved locally:", e);
      }
      return;
    }

    try {
      const res = await apiFetch("/history", apiToken);
      const historyData = await res.json();
      if (res.ok === false || !historyData.success || !Array.isArray(historyData.history)) {
        throw new Error(apiErrorMessage(historyData, "Could not sync local history."));
      }

      const localStr = localStorage.getItem(scopedCacheKey(HISTORY_CACHE_KEY, cacheScope));
      let localHistory: any[] = [];
      if (localStr) {
        try {
          const parsed = JSON.parse(localStr);
          localHistory = Array.isArray(parsed) ? parsed : [];
        } catch (e) { }
      }

      const historyMap = new Map<string, any>();
      [...historyData.history, ...localHistory].forEach((item: any) => {
        if (item?.id && !historyMap.has(item.id)) historyMap.set(item.id, item);
      });
      const mergedHistory = Array.from(historyMap.values()).sort((a: any, b: any) =>
        new Date(b.timestamp || 0).getTime() - new Date(a.timestamp || 0).getTime()
      );
      safeLocalStorageSet(scopedCacheKey(HISTORY_CACHE_KEY, cacheScope), JSON.stringify(mergedHistory));
      setHistoryItems(mergedHistory);

      const expectedSnippet = buildHistorySnippet(rawJd);
      const matchingItem = historyData.history.find((item: any) =>
        item?.client === effectiveClient &&
        (item?.url || "").trim() === jobUrl.trim() &&
        item?.raw_jd_snippet === expectedSnippet
      );
      itemId = matchingItem?.id;
    } catch (e) {
      console.error("Generated output could not be synced to local history:", e);
    }

    if (itemId) {
      try {
        safeLocalStorageSet(detailCacheKey(itemId, cacheScope), JSON.stringify(detail));
      } catch (e) {
        console.error("Generated output could not be saved locally:", e);
      }
    }
  };

  const showToast = (message: string) => {
    setToastMessage(message);
    const timeout = (window as any)._toastTimeout;
    if (timeout) clearTimeout(timeout);
    (window as any)._toastTimeout = setTimeout(() => {
      setToastMessage(null);
    }, 2000);
  };

  const copyToClipboard = async (text: string, label?: string) => {
    try {
      if (text) {
        await navigator.clipboard.writeText(text);
        showToast(label ? `Copied ${label}!` : "Copied to clipboard!");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSubjectChange = (e: any) => {
    const val = e.target.value;
    setSubject(val);
    if (mirrorSync) {
      const { prefix: newPrefix } = splitParts(val);
      if (!newPrefix) return;
      setLinkedinTitle(prev => {
        if (!prev) return prev;
        const { prefix: oldPrefix, suffix } = splitParts(prev);
        if (oldPrefix === newPrefix) return prev;
        return suffix ? `${newPrefix} | ${suffix}` : newPrefix;
      });
    }
  };

  const handleLinkedinChange = (e: any) => {
    const val = e.target.value;
    setLinkedinTitle(val);
    if (mirrorSync) {
      const { prefix: newPrefix } = splitParts(val);
      if (!newPrefix) return;
      setSubject(prev => {
        if (!prev) return prev;
        const { prefix: oldPrefix, suffix } = splitParts(prev);
        if (oldPrefix === newPrefix) return prev;
        return suffix ? `${newPrefix} | ${suffix}` : newPrefix;
      });
    }
  };

  const jdRef = useRef<HTMLDivElement>(null);
  const emailRef = useRef<HTMLDivElement>(null);

  const handleGenerate = async () => {
    if (!rawJd.trim()) {
      setError('Please paste the job description. The job link is optional.');
      return;
    }
    if (!isSafeJobUrl(jobUrl)) {
      setError('Please enter a valid job link beginning with http:// or https://.');
      return;
    }

    const effectiveClient = client === "domain_page" ? domainPageSelection : client;
    const currentSelection = { ...outputCheckmarks };

    if (lastRunData &&
      typeof lastRunData.rawJd === "string" &&
      lastRunData.rawJd.trim() === rawJd.trim() &&
      (lastRunData.jobUrl || "").trim() === jobUrl.trim() &&
      lastRunData.client === client &&
      outputSelectionsMatch(lastRunData.outputCheckmarks, currentSelection) &&
      (client !== "domain_page" || lastRunData.domainPageSelection === domainPageSelection)) {
      const loadedTitles = normalizeCachedTitleText(lastRunData.suggestedTitles);
      const loadedSkills = normalizeStringArray(lastRunData.skills);
      const loadedFunctions = normalizeStringArray(lastRunData.jobFunctions);
      const loadedIndustries = normalizeStringArray(lastRunData.industries);

      setStructuredJd(lastRunData.structuredJd || "");
      setEmailTemplate(lastRunData.emailTemplate || "");
      setSuggestedTitles(loadedTitles);
      setSubject(lastRunData.subject || "");
      setLinkedinTitle(lastRunData.linkedinTitle || "");
      setSkills(loadedSkills);
      setJobFunctions(loadedFunctions);
      setIndustries(loadedIndustries);
      setJustifications(lastRunData.justifications || {});
      setIsDomainView(lastRunData.isDomainView);
      setStep(3);
      showToast("Loaded from cache memory!");
      return;
    }

    setStep(2);
    setError(null);
    setLoadingStep("Analyzing job description...");

    const t1 = setTimeout(() => {
      setLoadingStep("Extracting key insights...");
    }, 1200);

    const t2 = setTimeout(() => {
      setLoadingStep("Generating structured output...");
    }, 2400);

    try {
      const res = await apiFetch("/parse-jd", apiToken, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          raw_jd: rawJd,
          url: jobUrl.trim(),
          client: effectiveClient,
          output_selection: client === "domain_page" ? currentSelection : null
        })
      });

      let data: any;
      try {
        data = await res.json();
      } catch {
        throw new Error("The server returned an unreadable response.");
      }
      if (res.ok === false || !data?.success) {
        throw new Error(apiErrorMessage(data, "The server could not process this job description."));
      }
      data = sanitizeOutputPayload(data);

      const loadedTitles = normalizeStringArray(data.titles);
      const loadedSkills = normalizeStringArray(data.skills);
      const loadedFunctions = normalizeStringArray(data.job_functions);
      const loadedIndustries = normalizeStringArray(data.industries);

      setStructuredJd(data.jd || "");
      setEmailTemplate(data.email || data.inmail_draft || "");
      setSuggestedTitles(loadedTitles.join("\n"));
      setSubject(data.subject || "");
      setLinkedinTitle(data.linkedin_title || "");
      setSkills(loadedSkills);
      setJobFunctions(loadedFunctions);
      setIndustries(loadedIndustries);
      setJustifications(data.justifications || {});
      setIsDomainView(data.is_domain_page || DOMAIN_PAGES.has(effectiveClient) || client === "domain_page");

      const runData = {
        rawJd,
        jobUrl,
        client,
        domainPageSelection,
        outputCheckmarks: currentSelection,
        structuredJd: data.jd || "",
        emailTemplate: data.email || data.inmail_draft || "",
        suggestedTitles: loadedTitles.join("\n"),
        subject: data.subject || "",
        linkedinTitle: data.linkedin_title || "",
        skills: loadedSkills,
        jobFunctions: loadedFunctions,
        industries: loadedIndustries,
        justifications: data.justifications || {},
        isDomainView: data.is_domain_page || DOMAIN_PAGES.has(effectiveClient) || client === "domain_page"
      };
      setLastRunData(runData);
      safeLocalStorageSet(scopedCacheKey(LAST_RUN_CACHE_KEY, cacheScope), JSON.stringify(runData));

      clearTimeout(t1);
      clearTimeout(t2);
      setStep(3);
      void persistGeneratedHistory(data, effectiveClient, currentSelection);
    } catch (err: any) {
      clearTimeout(t1);
      clearTimeout(t2);
      setError(err.message || "Error processing your request.");
      setStep(1);
    }
  };

  const copyHtml = async (html: string, label?: string) => {
    try {
      const sanitizedHtml = sanitizeHtml(html);
      const blob = new Blob([sanitizedHtml], { type: "text/html" });
      const data = [new ClipboardItem({ "text/html": blob })];
      await navigator.clipboard.write(data);
      showToast(label ? `Copied ${label}!` : "Copied to clipboard!");
    } catch (e) {
      console.error(e);
      showToast("Could not copy this output.");
    }
  };
  //Name suggested by Samarth
  return (
    <div className="layout-root">

      {step !== 2 && (
        <nav className="nav-top">
          <div className="nav-left">
            <button type="button" className="logo logo-button" onClick={() => setStep(1)} title="Go to Homepage">Job Weaver</button>
            {step === 1 && <span className="logo-sub">CROSSING HURDLES</span>}
          </div>

          <div className="nav-right">
            <button
              type="button"
              className="btn-ghost-box theme-toggle"
              onClick={() => setColorTheme(theme => theme === 'dark' ? 'light' : 'dark')}
              aria-label="Dark mode"
              aria-pressed={colorTheme === 'dark'}
              title={`Switch to ${colorTheme === 'dark' ? 'light' : 'dark'} mode`}
            >
              {colorTheme === 'dark'
                ? <Sun className="w-4 h-4" aria-hidden="true" />
                : <Moon className="w-4 h-4" aria-hidden="true" />}
              <span>{colorTheme === 'dark' ? 'Light' : 'Dark'}</span>
            </button>
            <button
              className="btn-ghost-box"
              onClick={() => {
                setShowHistoryModal(true);
                fetchHistory();
              }}
              style={{ marginRight: "12px", display: "flex", alignItems: "center", gap: "6px" }}
              title="View History / Cache"
            >
              <History className="w-4 h-4 text-slate-600" />
              History
            </button>
            {step === 1 && (
              <>
                <div className="step-indicator">
                  STEP 1 OF 2
                  <div className="progress-bars">
                    <div className="bar active"></div>
                    <div className="bar"></div>
                  </div>
                </div>
                {lastRunData && (
                  <button
                    className="btn-back"
                    onClick={() => {
                      const loadedTitles = normalizeCachedTitleText(lastRunData.suggestedTitles);
                      const loadedSkills = normalizeStringArray(lastRunData.skills);
                      const loadedFunctions = normalizeStringArray(lastRunData.jobFunctions);
                      const loadedIndustries = normalizeStringArray(lastRunData.industries);

                      setStructuredJd(lastRunData.structuredJd || "");
                      setEmailTemplate(lastRunData.emailTemplate || "");
                      setSuggestedTitles(loadedTitles);
                      setSubject(lastRunData.subject || "");
                      setLinkedinTitle(lastRunData.linkedinTitle || "");
                      setSkills(loadedSkills);
                      setJobFunctions(loadedFunctions);
                      setIndustries(loadedIndustries);
                      setJustifications(lastRunData.justifications || {});
                      setIsDomainView(lastRunData.isDomainView);
                      setOutputCheckmarks(normalizeOutputSelection(lastRunData.outputCheckmarks));
                      setStep(3);
                      showToast("Returned to output view!");
                    }}
                    title="Forward to Output"
                  >
                    Forward <ArrowRight className="w-4 h-4" />
                  </button>
                )}
              </>
            )}
            {step === 3 && (
              <>
                <div className="step-indicator">
                  STEP 2 OF 2
                  <div className="progress-bars">
                    <div className="bar active"></div>
                    <div className="bar active"></div>
                  </div>
                </div>
                <button className="btn-back" onClick={() => setStep(1)}>
                  <ArrowLeft className="w-4 h-4" /> Back to Input
                </button>
              </>
            )}
          </div>
        </nav>
      )}

      <main className="main-content">

        {step === 1 && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="wizard-input-view"
          >
            <div className="hero">
              <h1>Define Your Search</h1>
              <p>Paste the job description below to begin the structural analysis<br />of role requirements and latent expectations.</p>
            </div>

            <form
              className="card form-card"
              onSubmit={(e) => {
                e.preventDefault();
                handleGenerate();
              }}
            >
              <div className="input-label" id="target-client-label">SELECT TARGET CLIENT</div>
              <div className="selection-grid client-grid" role="group" aria-labelledby="target-client-label">
                {[
                  { id: "mercor", name: "Mercor" },
                  { id: "micro1", name: "Micro1" },
                  { id: "turing", name: "Turing" },
                  { id: "domain_page", name: "Domain Page" }
                ].map((item) => {
                  const isSelected = client === item.id;
                  return (
                    <motion.button
                      key={item.id}
                      type="button"
                      className="selection-card"
                      aria-pressed={isSelected}
                      whileHover={{ scale: 1.02, translateY: -2 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => setClient(item.id)}
                      style={{
                        padding: "18px 16px",
                        borderRadius: "14px",
                        border: isSelected ? "2px solid var(--primary-blue)" : "1.5px solid var(--border-light)",
                        backgroundColor: isSelected ? "var(--accent-soft)" : "var(--bg-card)",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        boxShadow: isSelected ? "0 10px 25px -5px rgba(37, 99, 235, 0.25)" : "0 2px 4px rgba(0,0,0,0.02)",
                        transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)"
                      }}
                    >
                      <span style={{ fontWeight: 700, fontSize: "1.05rem", color: isSelected ? "var(--accent-text)" : "var(--text-main)" }}>{item.name}</span>
                    </motion.button>
                  );
                })}
              </div>

              <AnimatePresence>
                {client === "domain_page" && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.3, ease: "easeInOut" }}
                    style={{ marginBottom: "28px", padding: "24px", backgroundColor: "var(--surface-subtle)", border: "1.5px solid var(--border-light)", borderRadius: "16px", overflow: "hidden" }}
                  >
                    <div className="input-label" id="domain-page-label">SELECT DOMAIN PAGE</div>
                    <div className="selection-grid domain-grid" role="group" aria-labelledby="domain-page-label">
                      {[
                        { id: "crossing_hurdles", name: "Crossing Hurdles" },
                        { id: "codegeniusrecruit", name: "CodeGeniusRecruit" },
                        { id: "curasenseai", name: "CuraSenseAI" },
                        { id: "legaltrustai", name: "LegalTrustAI" },
                        { id: "capitexai", name: "CapitexAI" },
                        { id: "stemsyncai", name: "STEMSyncAI" },
                        { id: "linguasenseai", name: "LinguaSenseAI" },
                        { id: "designmeshai", name: "DesignMeshAI" }
                      ].map((dom) => {
                        const isDomSelected = domainPageSelection === dom.id;
                        return (
                          <motion.button
                            key={dom.id}
                            type="button"
                            className="selection-card"
                            aria-pressed={isDomSelected}
                            whileHover={{ scale: 1.03 }}
                            whileTap={{ scale: 0.97 }}
                            onClick={() => setDomainPageSelection(dom.id)}
                            style={{
                              padding: "12px 14px",
                              borderRadius: "10px",
                              border: isDomSelected ? "2px solid var(--primary-blue)" : "1px solid var(--border-color)",
                              backgroundColor: isDomSelected ? "var(--primary-blue)" : "var(--bg-card)",
                              color: isDomSelected ? "var(--on-primary)" : "var(--text-main)",
                              cursor: "pointer",
                              fontSize: "0.86rem",
                              fontWeight: isDomSelected ? 700 : 600,
                              textAlign: "center",
                              boxShadow: isDomSelected ? "0 6px 16px rgba(37, 99, 235, 0.35)" : "0 1px 2px rgba(0,0,0,0.02)",
                              transition: "all 0.18s ease",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center"
                            }}
                          >
                            {dom.name}
                          </motion.button>
                        );
                      })}
                    </div>

                    <div className="input-label" id="output-options-label">OPTIONS</div>
                    <div className="output-option-grid" role="group" aria-labelledby="output-options-label">
                      {[
                        { key: "inmail", label: "InMail Draft" },
                        { key: "jd", label: "Job Description" }
                      ].map((opt) => {
                        const isChecked = outputCheckmarks[opt.key as "inmail" | "jd"];
                        return (
                          <motion.button
                            key={opt.key}
                            type="button"
                            className="selection-card output-option"
                            aria-pressed={isChecked}
                            whileHover={{ scale: 1.015 }}
                            whileTap={{ scale: 0.985 }}
                            onClick={() => {
                              if (isChecked && outputCheckmarks.inmail && outputCheckmarks.jd) {
                                setOutputCheckmarks({ ...outputCheckmarks, [opt.key]: false });
                              } else if (!isChecked) {
                                setOutputCheckmarks({ ...outputCheckmarks, [opt.key]: true });
                              } else {
                                showToast("At least one output option must be selected.");
                              }
                            }}
                            style={{
                              flex: 1,
                              padding: "16px 18px",
                              borderRadius: "12px",
                              border: isChecked ? "2px solid var(--primary-blue)" : "1.5px solid var(--border-color)",
                              backgroundColor: isChecked ? "var(--bg-card)" : "var(--bg-gray)",
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              gap: "14px",
                              boxShadow: isChecked ? "0 8px 20px -4px rgba(37, 99, 235, 0.15)" : "none",
                              transition: "all 0.2s ease"
                            }}
                          >
                            <div style={{
                              width: "24px",
                              height: "24px",
                              borderRadius: "6px",
                              border: isChecked ? "none" : "2px solid var(--text-light)",
                              backgroundColor: isChecked ? "var(--primary-blue)" : "transparent",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              color: "var(--on-primary)"
                            }}>
                              {isChecked && <Check className="w-4 h-4 stroke-[3]" />}
                            </div>
                            <div style={{ flex: 1, fontWeight: 700, fontSize: "0.98rem", color: isChecked ? "var(--text-main)" : "var(--text-muted)" }}>
                              {opt.label}
                            </div>
                          </motion.button>
                        );
                      })}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              <details className="advanced-api-section">
                <summary>Advanced / Remote API</summary>
                <div className="advanced-api-content">
                  <label className="input-label" htmlFor="remote-api-token">BEARER TOKEN</label>
                  <input
                    id="remote-api-token"
                    type="password"
                    className="input-field-clean advanced-api-token"
                    value={apiToken}
                    onChange={(event) => handleApiTokenChange(event.target.value)}
                    autoComplete="off"
                    spellCheck={false}
                    aria-describedby="remote-api-token-help"
                    placeholder="Required only when the remote backend enables authentication"
                  />
                  <p id="remote-api-token-help" className="advanced-api-help">
                    Sent only as an Authorization header and retained for this browser tab session.
                    Clear this field to forget it.
                  </p>
                </div>
              </details>

              <label className="input-label" htmlFor="job-url">JOB LINK (OPTIONAL)</label>
              <div className="input-with-icon" style={{ marginBottom: "26px" }}>
                <Link className="w-4 h-4 text-slate-400" />
                <input
                  id="job-url"
                  type="url"
                  className="input-field-clean"
                  placeholder="Paste the target job URL..."
                  value={jobUrl}
                  onChange={(e) => setJobUrl(e.target.value)}
                />
              </div>

              <label className="input-label" htmlFor="raw-job-description">PASTE RAW JOB DESCRIPTION</label>
              <textarea
                id="raw-job-description"
                className="input-field-clean textarea-large"
                placeholder="Paste the full job description or specification here..."
                value={rawJd}
                onChange={(e) => setRawJd(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    handleGenerate();
                  }
                }}
              />

              {error && <motion.p initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className="error-text">{error}</motion.p>}

              <div className="form-actions">
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => { setRawJd(''); setJobUrl(''); setError(null); }}
                >
                  Clear
                </button>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  type="submit"
                  className="btn-primary"
                >
                  Generate
                </motion.button>
              </div>
            </form>

            <div className="version-label">2.0 ALPHA</div>
          </motion.div>
        )}

        {step === 2 && (
          <div className="wizard-processing-view">
            <TetrisLoading 
              size="md" 
              speed="normal" 
              showLoadingText={true} 
              loadingText={loadingStep || "Analyzing Job Description..."} 
            />
          </div>
        )}

        {step === 3 && (
          <div
            className="wizard-output-view animate-fade-in"
            onMouseOver={(e) => {
              const target = (e.target as HTMLElement).closest('a');
              if (target && target.href) {
                setHoveredLinkUrl(target.href);
              }
            }}
            onMouseOut={(e) => {
              const target = (e.target as HTMLElement).closest('a');
              if (target) {
                setHoveredLinkUrl(null);
              }
            }}
            onClick={(e) => {
              const target = (e.target as HTMLElement).closest('a');
              if (target && target.href && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                window.open(target.href, '_blank', 'noopener,noreferrer');
              }
            }}
          >

            <div className="output-col-left">
              {(!isDomainView || outputCheckmarks.inmail) && (
                <div className="output-section">
                  <div className="section-header">
                    <div>
                      <h3>{isDomainView ? "InMail Draft" : "Outreach Email"}</h3>
                    </div>
                    <div className="header-actions">
                      <label style={{ display: 'flex', alignItems: 'center', fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)', cursor: 'pointer', marginRight: '8px' }}>
                        <input
                          type="checkbox"
                          checked={mirrorSync}
                          onChange={(e) => setMirrorSync(e.target.checked)}
                          style={{ marginRight: '6px' }}
                        />
                        Mirror Prefix
                      </label>
                      <button
                        className="btn-primary-box"
                        onClick={() => copyHtml(emailRef.current?.innerHTML ?? emailTemplate, isDomainView ? "InMail Draft" : "template")}
                      >
                        <CopyIcon /> {isDomainView ? "Copy InMail" : "Copy Template"}
                      </button>
                    </div>
                  </div>

                  {subject && (
                    <div className="metadata-row">
                      <div style={{ flex: 1, marginRight: "16px" }}>
                        <div className="mini-title metadata-label">SUBJECT LINE</div>
                        <input
                          value={subject}
                          onChange={handleSubjectChange}
                          aria-label="Email subject line"
                          className="metadata-input"
                        />
                      </div>
                      <button className="btn-ghost-box" onClick={() => copyToClipboard(subject, "subject")} title="Copy Subject">
                        <CopyIcon /> Copy
                      </button>
                    </div>
                  )}

                  <div className="card output-card">
                    <div
                      className="rich-text-content"
                      ref={emailRef}
                      contentEditable
                      suppressContentEditableWarning
                      role="textbox"
                      aria-label={isDomainView ? "Editable InMail draft" : "Editable outreach email"}
                      style={{ whiteSpace: 'normal' }}
                      dangerouslySetInnerHTML={{ __html: sanitizeHtml(emailTemplate || "<p>No data</p>") }}
                    />
                  </div>
                </div>
              )}

              {(!isDomainView || outputCheckmarks.jd) && (
                <div className="output-section" style={{ marginTop: (!isDomainView || outputCheckmarks.inmail) ? "48px" : "0px" }}>
                  <div className="section-header">
                    <div>
                      <h3>Job Description</h3>
                    </div>
                    <div className="header-actions">
                      <button
                        className="btn-primary-box"
                        onClick={() => copyHtml(jdRef.current?.innerHTML ?? structuredJd, "JD")}
                      >
                        <CopyIcon /> Copy JD
                      </button>
                    </div>
                  </div>

                  {linkedinTitle && (
                    <div className="metadata-row">
                      <div style={{ flex: 1, marginRight: "16px" }}>
                        <div className="mini-title metadata-label">LINKEDIN TITLE</div>
                        <input
                          value={linkedinTitle}
                          onChange={handleLinkedinChange}
                          aria-label="LinkedIn title"
                          className="metadata-input"
                        />
                      </div>
                      <button className="btn-ghost-box" onClick={() => copyToClipboard(linkedinTitle, "LinkedIn title")} title="Copy LinkedIn Title">
                        <CopyIcon /> Copy
                      </button>
                    </div>
                  )}
                  <div className="card output-card">
                    <div
                      className="rich-text-content"
                      ref={jdRef}
                      contentEditable
                      suppressContentEditableWarning
                      role="textbox"
                      aria-label="Editable job description"
                      style={{ whiteSpace: 'normal' }}
                      dangerouslySetInnerHTML={{ __html: sanitizeHtml(structuredJd || "<p>No data</p>") }}
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="output-col-right">
              {/* 1. SUGGESTED TITLES */}
              {suggestedTitles && (
                <div className="card gray-card" style={{ padding: "24px" }}>
                  <div className="mini-title" style={{ marginBottom: "12px" }}>SUGGESTED TITLES (TAP TO COPY)</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                    {suggestedTitles.split("\n").filter(Boolean).map((t: string, i: number) => {
                      const cleanT = t.replace(/^- /, '').trim();
                      return (
                        <button
                          type="button"
                          key={i}
                          className="clickable-pill"
                          onClick={() => copyToClipboard(cleanT, "title")}
                          title={justifications[cleanT] || "Alternative job title matching role requirements."}
                        >
                          {cleanT}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 2. INDUSTRIES */}
              {industries && industries.length > 0 && (
                <div className="card gray-card" style={{ marginTop: "16px", padding: "24px" }}>
                  <div className="mini-title" style={{ marginBottom: "12px" }}>INDUSTRIES (TAP TO COPY)</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                    {industries.map((s: string, i: number) => (
                      <button
                        type="button"
                        key={i}
                        className="clickable-pill"
                        onClick={() => copyToClipboard(s, "industry")}
                        title={justifications[s] || "Industry sector relevant to the role's domain."}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* 3. JOB FUNCTIONS */}
              {jobFunctions && jobFunctions.length > 0 && (
                <div className="card gray-card" style={{ marginTop: "16px", padding: "24px" }}>
                  <div className="mini-title" style={{ marginBottom: "12px" }}>JOB FUNCTIONS (TAP TO COPY)</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                    {jobFunctions.map((s: string, i: number) => (
                      <button
                        type="button"
                        key={i}
                        className="clickable-pill"
                        onClick={() => copyToClipboard(s, "job function")}
                        title={justifications[s] || "Core function related to the primary responsibilities."}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* 4. TARGET SKILLS */}
              {skills && skills.length > 0 && (
                <div className="card gray-card" style={{ marginTop: "16px", padding: "24px" }}>
                  <div className="mini-title" style={{ marginBottom: "12px" }}>TARGET SKILLS (TAP TO COPY)</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                    {skills.map((s: string, i: number) => (
                      <button
                        type="button"
                        key={i}
                        className="clickable-pill"
                        onClick={() => copyToClipboard(s, "skill")}
                        title={justifications[s] || "Technical skill or framework required for the role."}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {hoveredLinkUrl && (
              <div className="link-preview">
                {hoveredLinkUrl}
              </div>
            )}
          </div>
        )}
      </main>

      {toastMessage && (
        <div className="toast-notification">
          {toastMessage}
        </div>
      )}

      {showHistoryModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="history-dialog-title"
          className="history-modal-overlay"
          style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "var(--overlay-bg)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          zIndex: 1000,
          padding: "24px"
          }}
        >
          <div className="card animate-fade-in" style={{
            backgroundColor: "var(--bg-card)",
            borderRadius: "12px",
            width: "100%",
            maxWidth: "680px",
            maxHeight: "80vh",
            display: "flex",
            flexDirection: "column",
            boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
            overflow: "hidden"
          }}>
            <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border-color)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 id="history-dialog-title" style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700, color: "var(--text-main)" }}>Recent Generation History</h3>
              <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                {historyItems.length > 0 && (
                  <button className="btn-ghost-box" onClick={clearHistory} style={{ color: "var(--danger-text)", fontSize: "0.85rem" }}>
                    Clear All
                  </button>
                )}
                <button
                  onClick={() => setShowHistoryModal(false)}
                  aria-label="Close history"
                  style={{ background: "none", border: "none", fontSize: "1.5rem", cursor: "pointer", color: "var(--text-muted)", lineHeight: 1 }}
                >
                  &times;
                </button>
              </div>
            </div>

            <div style={{ padding: "20px 24px", overflowY: "auto", flex: 1 }}>
              {loadingHistory ? (
                <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-muted)" }}>Loading history cache...</div>
              ) : historyItems.length === 0 ? (
                <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-muted)" }}>No cached history found yet. Generate a job description to get started!</div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  {historyItems.map((item) => (
                    <div
                      key={item.id}
                      style={{
                        padding: "16px",
                        border: "1px solid var(--border-color)",
                        borderRadius: "8px",
                        backgroundColor: "var(--surface-subtle)",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        gap: "16px",
                        transition: "all 0.15s ease"
                      }}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                          <span style={{ fontWeight: 700, fontSize: "1rem", color: "var(--text-main)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                            {item.role || "Untitled Job"}
                          </span>
                          <span style={{ fontSize: "0.75rem", padding: "2px 8px", borderRadius: "9999px", backgroundColor: "var(--pill-bg)", color: "var(--pill-text)", fontWeight: 600, textTransform: "uppercase" }}>
                            {item.client}
                          </span>
                        </div>
                        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {item.raw_jd_snippet || item.url || "No details provided"}
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-light)", marginTop: "4px" }}>
                          {new Date(item.timestamp).toLocaleString()}
                        </div>
                      </div>
                      <button
                        className="btn-primary-box"
                        onClick={() => loadHistoryItem(item.id)}
                        style={{ padding: "8px 16px", fontSize: "0.85rem", whiteSpace: "nowrap" }}
                      >
                        Load Output
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Inline SVGs tailored for the mockups

const CopyIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
);
