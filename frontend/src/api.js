const BASE = '/api'

/**
 * Submit the coefficient box to the real audit API.
 *
 * Returns ``{ ok: true, report }`` or ``{ ok: false, message }``.  The caller
 * is responsible for clearing any stale report on failure; the editable input
 * content is always preserved.
 */
export async function postAudit(coeffs) {
  let response
  try {
    response = await fetch(`${BASE}/audit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ coeffs }),
    })
  } catch (networkError) {
    return {
      ok: false,
      message: `请求失败，无法连接审计服务：${networkError.message}`,
    }
  }
  let payload = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }
  if (!response.ok) {
    const detail =
      payload && typeof payload.detail === 'string'
        ? payload.detail
        : `审计服务返回错误状态 ${response.status}`
    return { ok: false, message: detail }
  }
  return { ok: true, report: payload }
}

export async function fetchHealth() {
  try {
    const response = await fetch(`${BASE}/health`)
    return response.ok
  } catch {
    return false
  }
}
