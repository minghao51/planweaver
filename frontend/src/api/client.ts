export const API_BASE = '/api/v1';

export class RateLimitError extends Error {
  retryAfter: number;
  constructor(message: string, retryAfter: number) {
    super(message);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

export async function fetchJson<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const requestPath = `${API_BASE}${path}`;
  const requestUrl =
    typeof window !== 'undefined'
      ? new URL(requestPath, window.location.origin).toString()
      : requestPath;

  const response = await fetch(requestUrl, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let errorMessage = `HTTP error! status: ${response.status}`;
    let retryAfter = 0;

    if (response.status === 429) {
      try {
        const errorData = await response.json();
        if (errorData?.detail) {
          errorMessage = errorData.detail;
        }
        retryAfter = parseInt(
          response.headers.get('Retry-After') || errorData?.retry_after || '60',
          10
        );
      } catch {
        retryAfter = 60;
      }
      throw new RateLimitError(errorMessage, retryAfter);
    }

    try {
      const errorData = await response.json();
      if (errorData?.detail) {
        errorMessage = errorData.detail;
      }
    } catch {
      errorMessage = response.statusText || errorMessage;
    }
    throw new Error(errorMessage);
  }

  return response.json() as Promise<T>;
}
