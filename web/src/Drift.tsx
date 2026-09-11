import { useEffect, useState } from 'react'
import { Answer, DriftReport, getDrift } from './api'

const fmt = (a: Answer | null) => (a ? `${a[1] ?? a[3] ?? 'NONE'}${a[2] ? ` ${a[2]}` : ''}` : 'NONE')

export default function Drift({ refresh }: { refresh: number }) {
  const [r, setR] = useState<DriftReport | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getDrift()
      .then((x) => {
        setR(x)
        setError('')
      })
      .catch((e: Error) => setError(e.message))
  }, [refresh])

  if (error) return <div className="error">{error}</div>
  if (!r) return <div>loading</div>
  const empty =
    !r.answers.length && !r.fields.length && !r.kickoff_mismatch.length && !r.unexpected_kalshi_market.length
  if (empty) return <div>no drift between the last two runs</div>
  return (
    <div>
      {r.answers.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>change</th>
              <th>symbol</th>
              <th>was → now</th>
            </tr>
          </thead>
          <tbody>
            {r.answers.map((a, i) => (
              <tr key={i}>
                <td>{a.change}</td>
                <td className="mono">{a.symbol}</td>
                <td className="mono">
                  {fmt(a.was)} → {fmt(a.now)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {r.fields.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>league</th>
              <th>field</th>
              <th>change</th>
              <th>was → now</th>
            </tr>
          </thead>
          <tbody>
            {r.fields.map((f, i) => (
              <tr key={i}>
                <td>{f.league}</td>
                <td className="mono">{f.field}</td>
                <td>{f.change}</td>
                <td className="mono">
                  {f.was} → {f.now}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {r.kickoff_mismatch.map((s) => (
        <div key={s} className="mono">
          kickoff mismatch: {s}
        </div>
      ))}
      {r.unexpected_kalshi_market.map((s) => (
        <div key={s} className="mono">
          unexpected kalshi market: {s}
        </div>
      ))}
    </div>
  )
}
