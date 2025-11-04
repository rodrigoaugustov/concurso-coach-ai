export const API_URL = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '');
export const apiPath = (path: string) => `${API_URL}/${path.replace(/^\/+/, '')}`;

export async function postJSON(path: string, data: unknown, init: RequestInit = {}) {
  const res = await fetch(apiPath(path.endsWith('/') ? path : `${path}/`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...(init.headers || {})
    },
    body: JSON.stringify(data),
    redirect: 'follow',
    ...init,
  });
  return res;
}
