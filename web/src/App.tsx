import { useState } from 'react'
import { postResolve, ResolveResult } from './api'
import Drift from './Drift'
import Manual from './Manual'

export default function App() {
  const [input, setInput] = useState('')
  const [running, setRunning] = useState(false)
  const [results, setResults] = useState<ResolveResult[] | null>(null)
  const [run, setRun] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [driftGen, setDriftGen] = useState(0)

  async function resolve() {
    const symbols = input.split(/[\s,]+/).filter(Boolean)
    if (!symbols.length) return
    setRunning(true)
    setError('')
    try {
      const r = await postResolve(symbols)
      setResults(r.results)
      setRun(r.run)
    } catch (e) {
      setError((e as Error).message)
    }
    setRunning(false)
    setDriftGen((g) => g + 1)
  }

  const mapped = results ? results.filter((r) => r.kalshi_ticker !== null).length : 0

  return (
    <>
      <div className="mono">pmus-kalshi-mapper</div>
      <div className="grid">
        <section>
          <h2>resolve</h2>
          <textarea
            rows={5}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="pmus symbols, separated by commas, spaces or newlines"
          />
          <button onClick={resolve} disabled={running}>
            resolve
          </button>
          {error && <div className="error">{error}</div>}
          {results && (
            <>
              <div>{mapped} of {results.length} mapped{run && <> · run <span className="mono">{run}</span></>}</div>
              <table>
                <thead>
                  <tr>
                    <th>symbol</th>
                    <th>ticker</th>
                    <th>side</th>
                    <th>rung</th>
                    <th>reason</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r, i) => (
                    <tr key={i}>
                      <td className="mono">{r.symbol}</td>
                      <td className="mono">{r.kalshi_ticker ?? 'NONE'}</td>
                      <td>{r.side ?? ''}</td>
                      <td>{r.rung ?? ''}</td>
                      <td>{r.reason ?? ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </section>
        <section>
          <h2>drift</h2>
          <Drift refresh={driftGen} />
        </section>
      </div>
      <Manual />
    </>
  )
}
