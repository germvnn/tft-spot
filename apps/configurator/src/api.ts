function messageFromResponse(payload: unknown): string {
  if (
    typeof payload === 'object' &&
    payload !== null &&
    'detail' in payload
  ) {
    const detail = payload.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((entry) =>
          typeof entry === 'object' &&
          entry !== null &&
          'msg' in entry
            ? String(entry.msg)
            : 'Nieprawidłowa wartość',
        )
        .join(', ')
    }
  }
  return 'Wystąpił nieoczekiwany błąd'
}

export async function readJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  const payload: unknown = await response.json().catch(() => null)
  if (payload === null) {
    throw new Error('Serwer zwrócił nieprawidłową odpowiedź. Spróbuj ponownie.')
  }
  if (!response.ok) throw new Error(messageFromResponse(payload))
  return payload as T
}
