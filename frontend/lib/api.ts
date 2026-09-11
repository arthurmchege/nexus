export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8001';
}

export function buildApiUrl(path: string) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${getApiBaseUrl()}${normalizedPath}`;
}

export function apiFetch(path: string, init?: RequestInit) {
  return fetch(buildApiUrl(path), { ...init, credentials: 'include' });
}

export function getApiErrorMessage(payload: unknown, fallback: string) {
  if (typeof payload === 'object' && payload !== null && 'detail' in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => (typeof item === 'object' && item !== null && 'msg' in item ? String(item.msg) : String(item)))
        .join(', ');
    }
  }
  return fallback;
}

export function getApiResponseErrorMessage(
  response: Response,
  payload: unknown,
  fallback: string,
) {
  if (response.status === 429) {
    const retryAfter = response.headers.get('Retry-After');
    return retryAfter
      ? `Too many attempts. Please try again in ${retryAfter} seconds.`
      : 'Too many attempts. Please try again later.';
  }
  return getApiErrorMessage(payload, fallback);
}
