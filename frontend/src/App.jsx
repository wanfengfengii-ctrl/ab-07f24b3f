import { useCallback, useEffect, useState } from 'react'
import { fetchHealth, postAudit } from './api.js'

const MIN_DEGREE = 2
const MAX_DEGREE = 40

// Finite decimal grammar, shared in spirit with the backend parser:
// optional sign, digits with at most one decimal point, optional decimal
// exponent.  No NaN / Infinity / hex / fractions are accepted.
const DECIMAL_RE = /^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/

// Point-bound stable polynomial (s+1)(s+2)(s+3) = s^3 + 6 s^2 + 11 s + 6,
// coefficients indexed from the constant term.
const STABLE_PRESET = {
  degree: 3,
  rows: [
    { lower: '5.8', upper: '6.2' },
    { lower: '10.5', upper: '11.5' },
    { lower: '5.7', upper: '6.3' },
    { lower: '1', upper: '1' },
  ],
}

// Deliberately non-robust box: at every vertex the linear coefficient is
// negative, so the first Hurwitz minor Delta_1 is negative.
const UNSTABLE_PRESET = {
  degree: 2,
  rows: [
    { lower: '1', upper: '1' },
    { lower: '-1', upper: '-1' },
    { lower: '1', upper: '1' },
  ],
}

function resizeRows(rows, degree) {
  const next = []
  for (let i = 0; i <= degree; i += 1) {
    next.push(rows[i] ? { ...rows[i] } : { lower: '', upper: '' })
  }
  return next
}

function supPower(i) {
  if (i === 0) return ''
  const sup = { '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵',
    '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹' }
  return 's' + String(i).split('').map((d) => sup[d]).join('')
}

export default function App() {
  const [degree, setDegree] = useState(STABLE_PRESET.degree)
  const [rows, setRows] = useState(STABLE_PRESET.rows)
  const [report, setReport] = useState(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [healthy, setHealthy] = useState(null)

  useEffect(() => {
    let alive = true
    const ping = () => fetchHealth().then((ok) => { if (alive) setHealthy(ok) })
    ping()
    const timer = setInterval(ping, 10000)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])

  const onDegreeChange = useCallback((event) => {
    const nextDegree = Number(event.target.value)
    setDegree(nextDegree)
    setRows((prev) => resizeRows(prev, nextDegree))
    // Changing the order invalidates the structure of any previous report.
    setReport(null)
    setError('')
  }, [])

  const updateField = useCallback((index, field, value) => {
    setRows((prev) => {
      const next = prev.map((row) => ({ ...row }))
      next[index][field] = value
      return next
    })
  }, [])

  const loadPreset = useCallback((preset) => {
    setDegree(preset.degree)
    setRows(resizeRows(preset.rows, preset.degree))
    // A new input scenario invalidates any previously displayed report.
    setReport(null)
    setError('')
  }, [])

  const validateLocally = useCallback(() => {
    for (let i = 0; i <= degree; i += 1) {
      const { lower, upper } = rows[i]
      if (!lower.trim() || !upper.trim()) {
        return `系数 a_${i} 的上下界不能为空（请输入有限十进制数）`
      }
      if (!DECIMAL_RE.test(lower.trim())) {
        return `系数 a_${i} 的下界 ${lower} 不是有限十进制数`
      }
      if (!DECIMAL_RE.test(upper.trim())) {
        return `系数 a_${i} 的上界 ${upper} 不是有限十进制数`
      }
    }
    return null
  }, [degree, rows])

  const onSubmit = useCallback(async () => {
    setSubmitting(true)
    // Illegal input or a failed request must clear the previous report;
    // the editable content in `rows` is never touched.
    const localError = validateLocally()
    if (localError) {
      setError(localError)
      setReport(null)
      setSubmitting(false)
      return
    }
    const result = await postAudit(rows.map((r) => ({
      lower: r.lower.trim(),
      upper: r.upper.trim(),
    })))
    if (result.ok) {
      setReport(result.report)
      setError('')
    } else {
      setReport(null)
      setError(result.message)
    }
    setSubmitting(false)
  }, [rows, validateLocally])

  const failureKey = report?.failure
    ? `${report.failure.vertex}-${report.failure.first_failed_minor}`
    : null

  return (
    <div className="page">
      <header className="header">
        <h1>Kharitonov 区间多项式稳健稳定性审计台</h1>
        <div className="health" data-testid="health-indicator">
          {healthy === null ? '服务状态检测中…'
            : healthy ? <span className="ok">● API 在线</span>
            : <span className="bad">● API 不可达</span>}
        </div>
      </header>

      <p className="intro">
        系数按常数项起编号：P(s) = a₀ + a₁s + … + a<sub>n</sub>s<sup>n</sup>，
        阶数 2 ≤ n ≤ 40。后端将有限十进制上下界精确转换为有理数，按四项循环取界
        构造 K1–K4 四个顶点，并以 Hurwitz 矩阵全部顺序主子式 Δ₁…Δ<sub>n</sub> 的严格
        正性裁决，全程无浮点求根、无区间采样。
      </p>

      <section className="panel">
        <div className="controls">
          <label className="degree-control">
            阶数 n：
            <select
              data-testid="degree-select"
              value={degree}
              onChange={onDegreeChange}
            >
              {Array.from({ length: MAX_DEGREE - MIN_DEGREE + 1 }, (_, k) => {
                const n = MIN_DEGREE + k
                return <option key={n} value={n}>{n}</option>
              })}
            </select>
          </label>
          <button
            type="button"
            className="secondary"
            data-testid="preset-stable"
            onClick={() => loadPreset(STABLE_PRESET)}
          >
            载入稳健示例
          </button>
          <button
            type="button"
            className="secondary"
            data-testid="preset-unstable"
            onClick={() => loadPreset(UNSTABLE_PRESET)}
          >
            载入失稳示例
          </button>
          <button
            type="button"
            className="primary"
            data-testid="submit-button"
            disabled={submitting}
            onClick={onSubmit}
          >
            {submitting ? '审计中…' : '发起审计'}
          </button>
        </div>

        <div className="table-wrap">
          <table className="coeff-table">
            <thead>
              <tr>
                <th>编号</th>
                <th>项</th>
                <th>下界 a<sub>i</sub><sup>−</sup></th>
                <th>上界 a<sub>i</sub><sup>+</sup></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} className={i === degree ? 'leading-row' : ''}>
                  <td className="idx">a_{i}{i === degree ? '（最高次项）' : ''}</td>
                  <td className="term">{supPower(i) || '1'}</td>
                  <td>
                    <input
                      data-testid={`coeff-lower-${i}`}
                      value={row.lower}
                      onChange={(e) => updateField(i, 'lower', e.target.value)}
                      inputMode="decimal"
                    />
                  </td>
                  <td>
                    <input
                      data-testid={`coeff-upper-${i}`}
                      value={row.upper}
                      onChange={(e) => updateField(i, 'upper', e.target.value)}
                      inputMode="decimal"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {error && (
        <div className="banner error" data-testid="error-message" role="alert">
          <strong>输入非法或请求失败：</strong>{error}
          <div className="banner-note">旧审计报告已清除，输入内容已保留以便修改。</div>
        </div>
      )}

      {report && (
        <Report report={report} failureKey={failureKey} />
      )}
    </div>
  )
}

function Report({ report, failureKey }) {
  return (
    <section className="panel report" data-testid="report">
      <h2>审计报告（{report.degree} 阶）</h2>
      {report.robust ? (
        <div className="banner robust" data-testid="verdict">
          ✔ 整个区间系数族严格稳定：四个 Kharitonov 顶点多项式的全部顺序主子式
          Δ₁…Δ_{report.degree} 均严格为正。
        </div>
      ) : (
        <div className="banner not-robust" data-testid="verdict">
          ✘ 区间族不稳健。
          <div data-testid="failure-location" className="failure-location">
            规范编号最小的失败顶点：<strong>{report.failure.vertex}</strong>；
            首个非正顺序主子式：
            <strong> Δ_{report.failure.first_failed_minor}</strong>。
          </div>
        </div>
      )}

      <div className="vertices">
        {report.vertices.map((v) => {
          const isFailureVertex = report.failure?.vertex === v.vertex
          return (
            <article
              key={v.vertex}
              data-testid={`vertex-card-${v.vertex}`}
              className={`vertex ${isFailureVertex ? 'failing' : ''} ${v.stable ? 'is-stable' : 'is-unstable'}`}
            >
              <header>
                <h3>
                  顶点 {v.vertex}
                  <span className={`badge ${v.stable ? 'ok' : 'bad'}`}>
                    {v.stable ? '严格稳定' : '不稳定'}
                  </span>
                </h3>
                <p className="pattern-hint">{patternHint(v.vertex)}</p>
              </header>

              <div className="polynomial" data-testid={`vertex-polynomial-${v.vertex}`}>
                {v.coefficients.map((c, i) => (
                  <span key={c.index} className="term-chip">
                    {i > 0 && <span className="plus">+</span>}
                    <span data-testid={`fraction-${v.vertex}-${i}`} className="frac">
                      {c.value}
                    </span>
                    {i > 0 && <span className="power">·s{supForInline(i)}</span>}
                  </span>
                ))}
              </div>

              <table className="minor-table">
                <thead>
                  <tr><th>逐阶判据</th><th>精确值（十进制 (精确分数)）</th><th>判定</th></tr>
                </thead>
                <tbody>
                  {v.minor_checks.map((m) => {
                    const isFirstFailure =
                      failureKey === `${v.vertex}-${m.index}`
                    return (
                      <tr
                        key={m.index}
                        data-testid={`minor-${v.vertex}-${m.index}`}
                        className={isFirstFailure ? 'first-failure' : ''}
                      >
                        <td>Δ_{m.index}{isFirstFailure && ' ◀ 首个非正子式'}</td>
                        <td className="frac">{m.value}</td>
                        <td>{m.positive
                          ? <span className="ok">✓ &gt; 0</span>
                          : <span className="bad">✗ ≤ 0</span>}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </article>
          )
        })}
      </div>
    </section>
  )
}

function supForInline(i) {
  if (i === 1) return ''
  return `^${i}`
}

function patternHint(name) {
  const hints = {
    K1: '取界模式（自 a₀ 起四项循环）：上、上、下、下',
    K2: '取界模式（自 a₀ 起四项循环）：上、下、下、上',
    K3: '取界模式（自 a₀ 起四项循环）：下、下、上、上',
    K4: '取界模式（自 a₀ 起四项循环）：下、上、上、下',
  }
  return hints[name]
}
