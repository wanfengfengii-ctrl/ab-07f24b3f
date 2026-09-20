import { useState } from 'react'

const MIN_DEGREE = 2
const MAX_DEGREE = 40

const ROBUST_EXAMPLE = [
  { lower: '1', upper: '2' },
  { lower: '2', upper: '3' },
  { lower: '2', upper: '4' },
  { lower: '1', upper: '1.5' },
]

// a0 上界放宽到 2.5、a1 下界收窄到 0.5 后，K3 = 2.5 + 0.5s + 2s² + 1.5s³
// 的 Δ2 = 2·0.5 − 2.5·1.5 = −11/4 ≤ 0，区间族不再稳健。
const FRAGILE_EXAMPLE = [
  { lower: '1', upper: '2.5' },
  { lower: '0.5', upper: '3' },
  { lower: '2', upper: '4' },
  { lower: '1', upper: '1.5' },
]

function extractError(data, status) {
  if (data && typeof data.detail === 'string') return data.detail
  if (data && Array.isArray(data.detail)) {
    return data.detail.map((d) => d.msg || JSON.stringify(d)).join('；')
  }
  return `请求失败（HTTP ${status}）`
}

function TermList({ coeffs }) {
  const terms = []
  coeffs.forEach((c, i) => {
    const negative = c.value.startsWith('-')
    const abs = negative ? c.value.slice(1) : c.value
    terms.push(
      <span key={i} className="term">
        {i === 0 ? (negative ? '− ' : '') : negative ? ' − ' : ' + '}
        <span className="frac">{abs}</span>
        {i > 0 && (
          <>
            ·s{i > 1 && <sup>{i}</sup>}
          </>
        )}
      </span>,
    )
  })
  return <div className="poly-line">{terms}</div>
}

function VertexCard({ vertex }) {
  return (
    <div
      className={`vertex-card ${vertex.stable ? 'vertex-ok' : 'vertex-bad'}`}
      data-testid={`vertex-${vertex.id}`}
    >
      <div className="vertex-head">
        <span className="vertex-name">{vertex.name}</span>
        <span className="vertex-pattern" title="四项循环取界模式（− 下界 / + 上界）">
          {vertex.patternLabel}
        </span>
        <span className={`badge ${vertex.stable ? 'badge-ok' : 'badge-bad'}`}>
          {vertex.stable ? '严格稳定' : '不稳定'}
        </span>
      </div>

      <TermList coeffs={vertex.coefficients} />

      <table className="mini-table">
        <thead>
          <tr>
            <th>系数</th>
            <th>取界</th>
            <th>精确值</th>
            <th>近似</th>
          </tr>
        </thead>
        <tbody>
          {vertex.coefficients.map((c) => (
            <tr key={c.index}>
              <td>
                a<sub>{c.index}</sub>
              </td>
              <td>{c.bound === 'lower' ? '下界' : '上界'}</td>
              <td className="mono">{c.value}</td>
              <td className="mono dim">{c.decimal}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="minors-title">Hurwitz 顺序主子式（逐阶判据）</div>
      <ul className="minor-list">
        {vertex.minors.map((m) => (
          <li
            key={m.order}
            data-testid={`v${vertex.id}-minor-${m.order}`}
            className={m.positive ? 'minor-ok' : 'minor-bad'}
          >
            <span className="minor-mark">{m.positive ? '✓' : '✗'}</span>
            <span className="mono">
              Δ<sub>{m.order}</sub> = {m.value}
            </span>
            <span className="mono dim"> ≈ {m.decimal}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function App() {
  const [rows, setRows] = useState(ROBUST_EXAMPLE)
  const [degreeText, setDegreeText] = useState(String(ROBUST_EXAMPLE.length - 1))
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const degree = rows.length - 1

  function loadExample(example) {
    setRows(example.map((r) => ({ ...r })))
    setDegreeText(String(example.length - 1))
    setReport(null)
    setError(null)
  }

  function applyDegree() {
    const parsed = Number.parseInt(degreeText, 10)
    if (Number.isNaN(parsed)) {
      setDegreeText(String(degree))
      return
    }
    const clamped = Math.min(MAX_DEGREE, Math.max(MIN_DEGREE, parsed))
    setDegreeText(String(clamped))
    setRows((prev) => {
      const next = prev.slice(0, clamped + 1)
      while (next.length < clamped + 1) next.push({ lower: '1', upper: '1' })
      return next
    })
    setReport(null)
    setError(null)
  }

  function updateRow(index, field, value) {
    setRows((prev) =>
      prev.map((r, i) => (i === index ? { ...r, [field]: value } : r)),
    )
    setReport(null)
    setError(null)
  }

  async function submit() {
    setLoading(true)
    setError(null)
    try {
      const resp = await fetch('/api/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          coefficients: rows.map((r, i) => ({
            index: i,
            lower: r.lower,
            upper: r.upper,
          })),
        }),
      })
      const data = await resp.json().catch(() => null)
      if (!resp.ok) {
        setReport(null)
        setError(extractError(data, resp.status))
        return
      }
      setReport(data)
    } catch (e) {
      setReport(null)
      setError(`无法连接后端审计服务：${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <header>
        <h1>Kharitonov 区间多项式稳健性审计台</h1>
        <p className="subtitle">
          区间多项式族 p(s) = a<sub>0</sub> + a<sub>1</sub>s + … + a<sub>n</sub>sⁿ，
          系数编号从常数项开始。后端将十进制界精确化为有理数，按四项循环模式构造
          K1–K4 四个 Kharitonov 顶点多项式，并以 Hurwitz
          矩阵全部顺序主子式的严格正性裁决全族稳健性——不做浮点求根，不做区间采样。
        </p>
      </header>

      <section className="controls">
        <label>
          阶数 n（{MIN_DEGREE}–{MAX_DEGREE}）：
          <input
            data-testid="degree-input"
            type="number"
            min={MIN_DEGREE}
            max={MAX_DEGREE}
            value={degreeText}
            onChange={(e) => setDegreeText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && applyDegree()}
          />
        </label>
        <button data-testid="degree-apply" onClick={applyDegree}>
          设置阶数
        </button>
        <span className="spacer" />
        <button data-testid="example-robust" onClick={() => loadExample(ROBUST_EXAMPLE)}>
          载入稳健示例
        </button>
        <button data-testid="example-fragile" onClick={() => loadExample(FRAGILE_EXAMPLE)}>
          载入失稳示例
        </button>
      </section>

      <section className="editor">
        <table className="coeff-table">
          <thead>
            <tr>
              <th>系数</th>
              <th>下界（有限十进制）</th>
              <th>上界（有限十进制）</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                <td>
                  a<sub>{i}</sub>
                  {i === 0 && <span className="tag">常数项</span>}
                  {i === degree && <span className="tag tag-top">最高次项</span>}
                </td>
                <td>
                  <input
                    data-testid={`lower-${i}`}
                    value={row.lower}
                    onChange={(e) => updateRow(i, 'lower', e.target.value)}
                    placeholder="如 0.5"
                  />
                </td>
                <td>
                  <input
                    data-testid={`upper-${i}`}
                    value={row.upper}
                    onChange={(e) => updateRow(i, 'upper', e.target.value)}
                    placeholder="如 1.5"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="submit-row">
          <button
            data-testid="submit"
            className="primary"
            onClick={submit}
            disabled={loading}
          >
            {loading ? '审计中…' : '发起审计'}
          </button>
          <span className="hint">
            最高次项 a<sub>{degree}</sub> 的下界必须为正
          </span>
        </div>
      </section>

      {error && (
        <div className="error-box" data-testid="error" role="alert">
          {error}
        </div>
      )}

      {report && (
        <section className="report" data-testid="report">
          <div
            className={`verdict ${report.robust ? 'verdict-ok' : 'verdict-bad'}`}
            data-testid="verdict"
          >
            {report.robust
              ? `稳健：${report.degree} 阶区间族的四个 Kharitonov 顶点多项式全部严格 Hurwitz 稳定`
              : `不稳健：${report.degree} 阶区间族未通过全族严格稳定性裁决`}
          </div>

          {!report.robust && report.firstFailure && (
            <div className="first-failure" data-testid="first-failure">
              首个失败顶点：K{report.firstFailure.vertexId}；首个非正主子式：Δ
              <sub>{report.firstFailure.minorOrder}</sub> ={' '}
              <span className="mono">{report.firstFailure.value}</span>
              <span className="mono dim"> ≈ {report.firstFailure.decimal}</span>
            </div>
          )}

          <div className="vertex-grid">
            {report.vertices.map((v) => (
              <VertexCard key={v.id} vertex={v} />
            ))}
          </div>
        </section>
      )}

      <footer>
        判定依据：Kharitonov 定理 + Hurwitz 行列式判据；全部计算使用精确有理数
        （分数）运算，页面展示的分数即后端裁决所用的精确值。
      </footer>
    </div>
  )
}
