// Manual config rows: symbol overrides plus player/team name aliases.
import { useEffect, useState } from 'react'
import * as api from './api'

function Overrides() {
  const [rows, setRows] = useState<api.Override[]>([])
  const [error, setError] = useState('')
  const [symbol, setSymbol] = useState('')
  const [ticker, setTicker] = useState('')
  const [side, setSide] = useState('yes')

  const load = () =>
    api.getOverrides()
      .then((r) => { setRows(r.overrides); setError('') })
      .catch((e: Error) => setError(e.message))
  useEffect(() => { void load() }, [])

  async function add() {
    if (!symbol.trim() || !ticker.trim()) return
    try {
      await api.putOverride(symbol.trim(), ticker.trim(), side)
      setSymbol(''); setTicker('')
      await load()
    } catch (e) { setError((e as Error).message) }
  }
  async function del(s: string) {
    try { await api.deleteOverride(s); await load() } catch (e) { setError((e as Error).message) }
  }

  return (
    <section>
      <h2>overrides</h2>
      {rows.length > 0 && (
        <table>
          <thead><tr><th>symbol</th><th>ticker</th><th>side</th><th></th></tr></thead>
          <tbody>
            {rows.map((o) => (
              <tr key={o.pmus_symbol}>
                <td className="mono">{o.pmus_symbol}</td>
                <td className="mono">{o.kalshi_ticker}</td>
                <td>{o.side}</td>
                <td><button onClick={() => del(o.pmus_symbol)}>delete</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="row">
        <input className="mono" placeholder="symbol" value={symbol} onChange={(e) => setSymbol(e.target.value)} />
        <input className="mono" placeholder="ticker" value={ticker} onChange={(e) => setTicker(e.target.value)} />
        <select value={side} onChange={(e) => setSide(e.target.value)}>
          <option value="yes">yes</option>
          <option value="no">no</option>
        </select>
        <button onClick={add}>add</button>
      </div>
      {error && <div className="error">{error}</div>}
    </section>
  )
}

function Aliases({ kind, title }: { kind: api.AliasKind; title: string }) {
  const teams = kind === 'teams'
  const [rows, setRows] = useState<api.Alias[]>([])
  const [error, setError] = useState('')
  const [name, setName] = useState('')
  const [alias, setAlias] = useState('')
  const [sources, setSources] = useState(teams ? 'review,manual' : '')
  const [query, setQuery] = useState('')

  const load = () =>
    api.getAliases(kind, sources)
      .then((r) => { setRows(r.aliases); setError('') })
      .catch((e: Error) => setError(e.message))
  useEffect(() => { void load() }, [sources])

  async function add() {
    if (!name.trim() || !alias.trim()) return
    try {
      await api.putAlias(kind, name.trim(), alias.trim())
      setName(''); setAlias('')
      await load()
    } catch (e) { setError((e as Error).message) }
  }
  async function del(n: string, a: string) {
    try { await api.deleteAlias(kind, n, a); await load() } catch (e) { setError((e as Error).message) }
  }

  const q = query.trim().toLowerCase()
  const shown = q ? rows.filter((r) => r.name.toLowerCase().includes(q) || r.alias.toLowerCase().includes(q)) : rows

  return (
    <section>
      <h2>{title}</h2>
      {teams && <div className="note">decided by the review model by default; rows added here override it</div>}
      <div className="row">
        <input placeholder="search" value={query} onChange={(e) => setQuery(e.target.value)} />
        {teams && (
          <select value={sources} onChange={(e) => setSources(e.target.value)}>
            <option value="review,manual">review + manual</option>
            <option value="">all, seed included</option>
          </select>
        )}
        <span>{shown.length} rows</span>
      </div>
      {shown.length > 0 && (
        <table>
          <thead><tr><th>name</th><th>alias</th>{teams && <th>source</th>}<th></th></tr></thead>
          <tbody>
            {shown.map((r, i) => (
              <tr key={i}>
                <td className="mono">{r.name}</td>
                <td className="mono">{r.alias}</td>
                {teams && <td>{r.source ?? ''}</td>}
                <td><button onClick={() => del(r.name, r.alias)}>delete</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="row">
        <input className="mono" placeholder="name" value={name} onChange={(e) => setName(e.target.value)} />
        <input className="mono" placeholder="alias" value={alias} onChange={(e) => setAlias(e.target.value)} />
        <button onClick={add}>add</button>
      </div>
      {error && <div className="error">{error}</div>}
    </section>
  )
}

export default function Manual() {
  return (
    <>
      <Overrides />
      <Aliases kind="players" title="player aliases" />
      <Aliases kind="teams" title="team aliases" />
    </>
  )
}
