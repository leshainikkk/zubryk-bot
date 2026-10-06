import { telegram, isTelegram } from './telegram';

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (isTelegram()) headers.set('Authorization', `tma ${telegram()!.initData}`);
  if (options.body) headers.set('Content-Type', 'application/json');
  let response: Response;
  try { response = await fetch(`/api${path}`, { ...options, headers, cache: 'no-store' }); }
  catch (error) {
    if ((error as Error).name === 'AbortError') throw error;
    throw new ApiError(0, 'network', 'Проверьте соединение и попробуйте ещё раз');
  }
  let data;
  try { data = await response.json(); }
  catch { throw new ApiError(response.status, 'unavailable', 'Сервис временно недоступен. Откройте приложение через кнопку «Зубрик» в боте'); }
  if (!response.ok) throw new ApiError(response.status, data.error ?? 'unknown', data.message ?? 'Не удалось загрузить данные');
  return data as T;
}
