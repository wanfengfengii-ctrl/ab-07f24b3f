# Kharitonov 区间多项式稳健稳定性审计台

面向量产模拟控制器的全栈审计工具：控制工程师在浏览器中输入闭环特征多项式
各系数的**有限十进制上下界**（系数自常数项 a₀ 起编号，阶数 2–40），通过真实
HTTP API 发起审计，查看四个 Kharitonov 顶点多项式与逐阶 Hurwitz 判据。

**整个稳定性裁决不使用任何浮点求根或区间采样**：十进制输入被精确转换为
`fractions.Fraction` 有理数，四个顶点按标准四项循环取界模式构造，每个顶点以
Hurwitz 矩阵全部顺序主子式 Δ₁…Δₙ 的严格正性裁决（精确 Bareiss 消元）。

## 数学方法

对于区间多项式族 P(s) = a₀ + a₁s + … + aₙsⁿ，aᵢ ∈ [aᵢ⁻, aᵢ⁺]，aₙ⁻ > 0，
Kharitonov 定理指出：整族 Hurwitz 稳定，当且仅当以下四个顶点多项式均 Hurwitz
稳定（取界自 a₀ 起四项循环）：

| 顶点 | a₀ | a₁ | a₂ | a₃ | a₄ | a₅ | … |
|------|----|----|----|----|----|----|---|
| K1 | 上 | 上 | 下 | 下 | 上 | 上 | … |
| K2 | 上 | 下 | 下 | 上 | 上 | 下 | … |
| K3 | 下 | 下 | 上 | 上 | 下 | 下 | … |
| K4 | 下 | 上 | 上 | 下 | 下 | 上 | … |

每个顶点按 Routh–Hurwitz 定理裁决：n×n Hurwitz 矩阵（`H[i][j]=a_{n-1+i-2j}`，
越界补零）的全部 n 个顺序主子式严格为正。行列式以无分数 Bareiss 消元精确计算，
全部运算在 `Fraction` 上进行。判定不稳健时，报告给出**规范编号最小的失败顶点**
（K1<K2<K3<K4）及其**首个非正子式**。

## 目录结构

```
backend/          FastAPI 服务（精确有理数核心 + /api/audit、/api/health）
frontend/         React + Vite 前端，生产环境由 nginx 托管并代理 /api
verify/           Playwright 真实 Chromium 浏览器验收（compose 中的 verify 服务）
docker-compose.yml
```

## 快速启动（Docker Compose）

```bash
cp .env.example .env          # 可选：修改 WEB_PORT / API_PORT
docker compose up -d --build
# 浏览器打开 http://localhost:${WEB_PORT:-8080}
```

- Web：`http://localhost:8080`（端口可用 `WEB_PORT` 配置）
- API：`http://localhost:8000`（端口可用 `API_PORT` 配置），含 `/api/health`
- Web 与 API 容器均配置了 Docker 健康检查；`web` 等待 `api` 健康后才启动。

## 浏览器验收服务

`verify` 是一个一次性可执行服务，用真实 Chromium 驱动浏览器验证编辑、提交、
失败定位、精确分数展示，以及非法输入/请求失败时“清除旧报告但保留输入”：

```bash
docker compose build verify
docker compose run --rm verify
```

验收项全部通过时退出码为 0，任一失败为 1。

## API

`POST /api/audit`

```json
{
  "coeffs": [
    {"lower": "5.8", "upper": "6.2"},
    {"lower": "10.5", "upper": "11.5"},
    {"lower": "5.7", "upper": "6.3"},
    {"lower": "1", "upper": "1"}
  ]
}
```

系数自常数项起顺序给出（上例为 3 阶）。校验规则：阶数 2–40；每项为有限十进制
文本且下界 ≤ 上界；最高次项下界严格为正。非法请求返回 `400 {"detail": "..."}`。
响应包含四个顶点的系数（`十进制 (p/q)` 精确形式）、全部顺序主子式逐阶判据、
整族结论以及（若不稳健）失败定位。

## 本地开发 / 测试

```bash
# 后端
cd backend && python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pip install pytest httpx
PYTHONPATH=. python -m pytest -q
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend && npm install && npm run dev   # Vite 将 /api 代理到 8000
```

后端测试覆盖：十进制→有理数精确转换、四项循环取界模式、已知多项式 Hurwitz
主子式、输入校验、稳健/失稳裁决与失败定位。开发阶段另用 numpy 浮点求根对
数百个随机多项式做过交叉核对（仅用于测试置信度，**绝不参与审计裁决**）。
