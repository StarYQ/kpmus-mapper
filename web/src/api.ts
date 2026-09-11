// Client for the mapper API: types + one function per route.
// Non-ok responses throw the server's {"error"} text as an Error.

export interface ResolveResult {
  symbol: string
  kalshi_ticker: string | null
  side: string | null
  rung: string | null
  reason: string | null
}

export type Answer = [boolean, string | null, string | null, string | null]

export interface AnswerChange {
  symbol: string
  change: string
  was: Answer | null
  now: Answer
  run: string
}

export interface FieldChange {
  league: string
  field: string
  change: string
  was: string
  now: string
  run: string
}

export interface DriftReport {
  answers: AnswerChange[]
  fields: FieldChange[]
  kickoff_mismatch: string[]
  unexpected_kalshi_market: string[]
}

export interface Override {
  pmus_symbol: string
  kalshi_ticker: string
  side: string
  updated_at: string
}

export interface Alias {
  name: string
  alias: string
  source: string | null
}

export type AliasKind = 'players' | 'teams'

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`
    try {
      const body = (await r.json()) as { error?: string }
      if (body.error) msg = body.error
    } catch {
      // non-JSON error body: keep the status text
    }
    throw new Error(msg)
  }
  return r.json() as Promise<T>
}

const send = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const postResolve = (symbols: string[]) =>
  req<{ run: string | null; results: ResolveResult[] }>('/resolve', send('POST', { symbols }))

export const getDrift = () => req<DriftReport>('/drift')

export const getOverrides = () => req<{ overrides: Override[] }>('/overrides')

export const putOverride = (symbol: string, kalshi_ticker: string, side: string) =>
  req<Override>(`/overrides/${encodeURIComponent(symbol)}`, send('PUT', { kalshi_ticker, side }))

export const deleteOverride = (symbol: string) =>
  req<{ deleted: string }>(`/overrides/${encodeURIComponent(symbol)}`, { method: 'DELETE' })

export const getAliases = (kind: AliasKind, source = '') =>
  req<{ aliases: Alias[] }>(`/aliases/${kind}${source ? `?source=${encodeURIComponent(source)}` : ''}`)

export const putAlias = (kind: AliasKind, name: string, alias: string) =>
  req<Alias>(`/aliases/${kind}`, send('PUT', { name, alias }))

export const deleteAlias = (kind: AliasKind, name: string, alias: string) =>
  req<{ deleted: string }>(
    `/aliases/${kind}/${encodeURIComponent(name)}/${encodeURIComponent(alias)}`,
    { method: 'DELETE' },
  )
