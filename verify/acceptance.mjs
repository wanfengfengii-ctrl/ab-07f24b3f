// Browser-driven acceptance verification for the Kharitonov audit bench.
//
// Runs against the fully containerised stack (BASE_URL defaults to the
// compose-internal nginx URL) and drives a real Chromium browser:
//
//   1. page load + live API health indicator
//   2. editing coefficient bounds / degree
//   3. submitting a robust box through the real API
//   4. exact rational display (decimal followed by the exact p/q fraction)
//   5. a non-robust box: location of the smallest-index failing vertex and
//      the first non-positive Hurwitz minor
//   6. illegal input clears the stale report while keeping the editable text
//   7. a failed request (network aborted) likewise clears the stale report
//      while preserving input content
//
// Exits 0 only if every check passes.

import { chromium } from 'playwright'

const BASE_URL = process.env.BASE_URL || 'http://web'

const results = []
function record(name, ok, detail = '') {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`)
}

async function assertStep(name, fn) {
  try {
    const detail = await fn()
    record(name, true, detail)
  } catch (error) {
    record(name, false, error.message)
  }
}

const browser = await chromium.launch({
  headless: true,
  // Required when the one-shot container runs as root; harmless locally.
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
})
const page = await browser.newPage()
page.on('pageerror', (error) => {
  record('browser console has no uncaught errors', false, error.message)
})

try {
  await assertStep('1. 打开页面并等待 API 健康指示在线', async () => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.getByTestId('health-indicator').getByText('API 在线').waitFor({
      timeout: 15000,
    })
  })

  await assertStep('2. 提交稳健示例并取得全族严格稳定结论（真实 API）', async () => {
    await page.getByTestId('preset-stable').click()
    await page.getByTestId('submit-button').click()
    await page.getByTestId('verdict').waitFor({ timeout: 15000 })
    const text = await page.getByTestId('verdict').innerText()
    if (!text.includes('整个区间系数族严格稳定')) {
      throw new Error(`结论文案不符: ${text}`)
    }
    for (const v of ['K1', 'K2', 'K3', 'K4']) {
      const card = page.getByTestId(`vertex-card-${v}`)
      if (!(await card.innerText()).includes('严格稳定')) {
        throw new Error(`顶点 ${v} 未显示严格稳定`)
      }
    }
  })

  await assertStep('3. 页面展示精确分数（十进制 (p/q)，无浮点近似）', async () => {
    // Stable preset a0 lower = 5.8 = 29/5; K1 takes the upper 6.2 = 31/5.
    const a0 = page.getByTestId('fraction-K1-0')
    await a0.waitFor()
    const text = (await a0.innerText()).replace(/\s+/g, ' ')
    if (!text.includes('6.2') || !text.includes('(31/5)')) {
      throw new Error(`a0 展示不是 6.2 (31/5): ${text}`)
    }
    // Every per-degree criterion on K1 shows an exact rational in parentheses.
    const minors = page.getByTestId('minor-K1-1')
    const minorText = await minors.innerText()
    if (!minorText.includes('/') || !minorText.includes('> 0')) {
      throw new Error(`逐阶判据缺少精确分数或正性判定: ${minorText}`)
    }
  })

  await assertStep('4. 编辑阶数与各系数上下界（二至四十阶可改）', async () => {
    await page.getByTestId('degree-select').selectOption('2')
    const inputs = [
      ['coeff-lower-0', '1'], ['coeff-upper-0', '1'],
      ['coeff-lower-1', '0.25'], ['coeff-upper-1', '0.75'],
      ['coeff-lower-2', '2'], ['coeff-upper-2', '2'],
    ]
    for (const [testId, value] of inputs) {
      await page.getByTestId(testId).fill(value)
    }
    const edited = await page.getByTestId('coeff-lower-1').inputValue()
    if (edited !== '0.25') throw new Error('编辑内容未保留')
  })

  await assertStep('5. 不稳健箱定位编号最小失败顶点 K1 与首个非正子式 Δ_1', async () => {
    // s^2 + a1 s + 1 with a1 in [-1,-1]: Delta_1 = a1 < 0 at every vertex.
    for (const [testId, value] of [
      ['coeff-lower-0', '1'], ['coeff-upper-0', '1'],
      ['coeff-lower-1', '-1'], ['coeff-upper-1', '-1'],
      ['coeff-lower-2', '1'], ['coeff-upper-2', '1'],
    ]) {
      await page.getByTestId(testId).fill(value)
    }
    await page.getByTestId('submit-button').click()
    await page.getByTestId('failure-location').waitFor({ timeout: 15000 })
    const locator = page.getByTestId('failure-location')
    const text = await locator.innerText()
    if (!text.includes('K1') || !text.includes('Δ_1')) {
      throw new Error(`失败定位文案不符: ${text}`)
    }
    const firstBad = page.getByTestId('minor-K1-1')
    const cls = await firstBad.getAttribute('class')
    if (cls !== 'first-failure') {
      throw new Error(`首个非正子式行未高亮，class=${cls}`)
    }
    const rowText = await firstBad.innerText()
    if (!rowText.includes('首个非正子式') || !rowText.includes('≤ 0')) {
      throw new Error(`首个非正子式标记不符: ${rowText}`)
    }
    // The failing vertex card is visually distinguished.
    const cardClass = await page.getByTestId('vertex-card-K1').getAttribute('class')
    if (!cardClass.includes('failing')) throw new Error('K1 卡片未标记为失败顶点')
  })

  await assertStep('6. 非法输入：清除旧报告、显示错误、保留可修改内容', async () => {
    await page.getByTestId('coeff-lower-0').fill('not-a-number')
    await page.getByTestId('submit-button').click()
    await page.getByTestId('error-message').waitFor({ timeout: 5000 })
    if (await page.getByTestId('report').count() !== 0) {
      throw new Error('非法输入后旧报告未被清除')
    }
    const retained = await page.getByTestId('coeff-lower-0').inputValue()
    if (retained !== 'not-a-number') throw new Error('非法输入内容未保留')
    // Restore a valid value so the next scenario starts from editable content.
    await page.getByTestId('coeff-lower-0').fill('1')
  })

  await assertStep('7. 请求失败：清除旧报告、显示错误、保留可修改内容', async () => {
    // First produce a valid report so there is something stale to clear.
    await page.getByTestId('submit-button').click()
    await page.getByTestId('report').waitFor({ timeout: 15000 })
    // Force every audit request to fail at the network layer.
    await page.route('**/api/audit', (route) => route.abort('failed'))
    await page.getByTestId('coeff-upper-1').fill('-0.5')
    await page.getByTestId('submit-button').click()
    await page.getByTestId('error-message').waitFor({ timeout: 10000 })
    const errorText = await page.getByTestId('error-message').innerText()
    if (!errorText.includes('请求失败')) throw new Error(`错误文案不符: ${errorText}`)
    if (await page.getByTestId('report').count() !== 0) {
      throw new Error('请求失败后旧报告未被清除')
    }
    const retained = await page.getByTestId('coeff-upper-1').inputValue()
    if (retained !== '-0.5') throw new Error('请求失败后输入内容未保留')
    await page.unroute('**/api/audit')
  })

  await assertStep('8. 阶数可增至四十阶（边界）', async () => {
    await page.getByTestId('degree-select').selectOption('40')
    const count = await page.locator('[data-testid^="coeff-lower-"]').count()
    if (count !== 41) throw new Error(`四十阶应有 41 个系数行，实际 ${count}`)
  })
} finally {
  await browser.close()
}

const failed = results.filter((r) => !r.ok)
console.log(`\n${results.length - failed.length}/${results.length} 项验收通过`)
process.exit(failed.length === 0 ? 0 : 1)
