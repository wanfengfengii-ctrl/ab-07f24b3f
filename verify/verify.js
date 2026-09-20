// 验收服务：通过真实浏览器操作验证编辑、提交、失败定位与精确分数展示。
// 退出码 0 = 全部通过；1 = 存在失败项。
const { chromium } = require('playwright')

const WEB_URL = process.env.WEB_URL || 'http://web'
const API_URL = process.env.API_URL || 'http://api:8000'

let failures = 0

function check(name, cond, extra = '') {
  if (cond) {
    console.log(`PASS  ${name}`)
  } else {
    failures += 1
    console.error(`FAIL  ${name}${extra ? ` —— ${extra}` : ''}`)
  }
}

async function submitAndWait(page) {
  const [resp] = await Promise.all([
    page.waitForResponse((r) => r.url().includes('/api/audit'), {
      timeout: 20000,
    }),
    page.click('[data-testid="submit"]'),
  ])
  return resp
}

async function main() {
  // 0. API 健康检查
  const health = await fetch(`${API_URL}/api/health`)
  check('API /api/health 返回 200', health.ok)

  const browser = await chromium.launch()
  try {
    const page = await browser.newPage()
    await page.goto(WEB_URL, { waitUntil: 'networkidle', timeout: 30000 })

    // 1. 页面加载：标题与默认系数行
    await page.waitForSelector('[data-testid="degree-input"]', { timeout: 20000 })
    const title = await page.textContent('h1')
    check('页面标题包含 Kharitonov', title.includes('Kharitonov'))
    check(
      '默认展示 3 阶（a0..a3 四行输入）',
      (await page.$('[data-testid="lower-3"]')) !== null &&
        (await page.$('[data-testid="lower-4"]')) === null,
    )

    // 2. 稳健示例：提交默认区间族
    await submitAndWait(page)
    await page.waitForSelector('[data-testid="verdict"]')
    const verdict1 = await page.textContent('[data-testid="verdict"]')
    check(
      '默认区间族判定为稳健',
      verdict1.includes('稳健') && !verdict1.includes('不稳健'),
      verdict1,
    )
    const k1 = await page.textContent('[data-testid="vertex-1"]')
    check('K1 顶点卡片存在', k1.includes('K1'))
    check('K1 系数精确分数 3/2 展示', k1.includes('3/2'))
    check('K1 主子式精确分数 13/2 展示', k1.includes('13/2'))
    const k2 = await page.textContent('[data-testid="vertex-2"]')
    check('K2 顶点卡片存在且稳定', k2.includes('K2') && k2.includes('严格稳定'))
    check(
      '四个顶点全部渲染',
      (await page.$$('[class*="vertex-card"]')).length === 4,
    )

    // 3. 编辑为失稳区间族：a0 上界 2.5、a1 下界 0.5
    await page.fill('[data-testid="upper-0"]', '2.5')
    await page.fill('[data-testid="lower-1"]', '0.5')
    await submitAndWait(page)
    await page.waitForSelector('[data-testid="verdict"]')
    const verdict2 = await page.textContent('[data-testid="verdict"]')
    check('编辑后区间族判定为不稳健', verdict2.includes('不稳健'), verdict2)
    const failure = await page.textContent('[data-testid="first-failure"]')
    check('失败定位为规范编号最小顶点 K3', failure.includes('K3'), failure)
    check('首个非正主子式定位为 Δ2', failure.includes('Δ2'), failure)
    check(
      '非正主子式精确值 -11/4 展示',
      failure.includes('-11/4'),
      failure,
    )
    const k3 = await page.textContent('[data-testid="vertex-3"]')
    check('K3 卡片标记不稳定', k3.includes('不稳定'))
    check('K3 卡片内 Δ2 = -11/4 精确展示', k3.includes('-11/4'))
    check(
      'K3 的 Δ2 行以失败样式标记',
      (await page.$('[data-testid="v3-minor-2"].minor-bad')) !== null,
    )

    // 4. 非法输入：最高次项下界为 0 -> 报错、清空旧报告、保留可编辑内容
    await page.fill('[data-testid="lower-3"]', '0')
    await submitAndWait(page)
    await page.waitForSelector('[data-testid="error"]')
    const err1 = await page.textContent('[data-testid="error"]')
    check('最高次项下界非正被拒绝', err1.includes('最高次项'), err1)
    check(
      '非法输入后旧报告被清除',
      (await page.$('[data-testid="report"]')) === null,
    )
    check(
      '非法输入后编辑内容保留（a1 下界仍为 0.5）',
      (await page.inputValue('[data-testid="lower-1"]')) === '0.5',
    )

    // 5. 非法输入：下界大于上界
    await page.fill('[data-testid="lower-3"]', '1')
    await page.fill('[data-testid="upper-2"]', '0.1')
    await submitAndWait(page)
    await page.waitForSelector('[data-testid="error"]')
    const err2 = await page.textContent('[data-testid="error"]')
    check('下界大于上界被拒绝', err2.includes('下界大于上界'), err2)
    check(
      '第二次非法输入后报告仍为空',
      (await page.$('[data-testid="report"]')) === null,
    )

    // 6. 阶数编辑：3 -> 4，新增系数行并可再次提交
    await page.fill('[data-testid="upper-2"]', '4')
    await page.fill('[data-testid="degree-input"]', '4')
    await page.click('[data-testid="degree-apply"]')
    await page.waitForSelector('[data-testid="lower-4"]')
    check('阶数调整为 4 后出现 a4 输入行', true)
    await submitAndWait(page)
    await page.waitForSelector('[data-testid="verdict"]')
    const verdict3 = await page.textContent('[data-testid="verdict"]')
    check(
      '4 阶区间族可提交并给出裁决',
      verdict3.includes('稳健'),
      verdict3,
    )
  } finally {
    await browser.close()
  }

  if (failures > 0) {
    console.error(`\n${failures} 项验收失败`)
    process.exit(1)
  }
  console.log('\n全部验收项通过')
}

main().catch((e) => {
  console.error('验收执行异常:', e)
  process.exit(1)
})
