# Kharitonov 区间多项式稳健性审计台

量产后元件公差使闭环特征多项式的每个系数落入区间
`a_i ∈ [a_i⁻, a_i⁺]`。本工具对**整个区间族**给出严格 Hurwitz
稳健的解析判定，而不是抽样根轨迹：

1. 浏览器端录入 2–40 阶多项式各系数的**有限十进制**上下界
   （系数编号从常数项 `a₀` 开始，最高次项下界必须为正）；
2. 后端把十进制界**精确转换为有理数**（`Decimal → Fraction`，无任何浮点近似）；
3. 按**四项循环**标准取界模式构造四个 Kharitonov 顶点多项式；
4. 对每个顶点构造 Hurwitz 矩阵，用**精确 Bareiss 无分式消元**计算全部
   顺序主子式 Δ₁…Δ_n，以**严格正性**裁决；
5. 全族稳健 ⟺ 四个顶点全部严格稳定；否则页面定位**规范编号最小的失败顶点**
   及其**首个非正主子式**（含精确分数值）。

全过程禁止浮点求根、禁止区间采样：页面展示的分数即裁决所用的精确值。

## 四项循环取界模式

对系数下标 `i`（从常数项 0 起），按 `i mod 4` 循环取下界（−）或上界（+）：

| 顶点 | i≡0 | i≡1 | i≡2 | i≡3 | 模式       |
| ---- | --- | --- | --- | --- | ---------- |
| K1   | −   | −   | +   | +   | `--++` 循环 |
| K2   | +   | +   | −   | −   | `++--` 循环 |
| K3   | +   | −   | −   | +   | `+--+` 循环 |
| K4   | −   | +   | +   | −   | `-++-` 循环 |

## 快速开始（Docker）

```bash
docker compose up --build
```

- Web 界面：http://localhost:8080 （可用 `WEB_PORT` 覆盖）
- API：http://localhost:8000/api （可用 `API_PORT` 覆盖，文档见 `/docs`）

宿主机端口可配置：

```bash
WEB_PORT=9000 API_PORT=9001 docker compose up --build
```

`web` 与 `api` 均配置了健康检查；`web` 通过 nginx 将 `/api/*`
反向代理到 `api` 服务，前端同源调用、无跨域问题。

## 验收（浏览器自动化）

`verify` 服务等待 web/api 健康后，用 Playwright 驱动 Chromium
完成真实浏览器验收：编辑系数、提交审计、核对失败顶点/首个非正子式定位、
核对精确分数展示、核对非法输入清空旧报告且保留可编辑内容：

```bash
docker compose up --build --exit-code-from verify verify
```

退出码 0 表示全部验收项通过。

## 本地开发

后端（Python 3.11+）：

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
.venv/bin/python -m pytest tests/ -q
```

前端（Node 20+）：

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173，/api 代理到 8000
```

## API

### `POST /api/audit`

```json
{
  "coefficients": [
    { "index": 0, "lower": "1",   "upper": "2"   },
    { "index": 1, "lower": "2",   "upper": "3"   },
    { "index": 2, "lower": "2",   "upper": "4"   },
    { "index": 3, "lower": "1",   "upper": "1.5" }
  ]
}
```

- 系数个数 = 阶数 + 1，阶数 2–40；`index` 必须从 0 连续编号；
- `lower`/`upper` 为有限十进制（字符串或数字，支持 `1e-3` 形式），
  且 `lower ≤ upper`；最高次项 `lower` 必须严格为正；
- 非法输入返回 `422` 与中文错误说明。

响应（节选）：

```json
{
  "degree": 3,
  "robust": true,
  "firstFailure": null,
  "vertices": [
    {
      "id": 1, "name": "K1", "pattern": "LLUU", "patternLabel": "−−++",
      "stable": true, "firstNonPositive": null,
      "coefficients": [
        { "index": 0, "value": "1", "decimal": "1", "bound": "lower" }
      ],
      "minors": [
        { "order": 1, "value": "4", "decimal": "4", "positive": true },
        { "order": 2, "value": "13/2", "decimal": "6.5", "positive": true }
      ]
    }
  ]
}
```

不稳健时 `firstFailure` 形如
`{"vertexId": 3, "minorOrder": 2, "value": "-11/4", "decimal": "-2.75"}`，
即规范编号最小的失败顶点 K3 与其首个非正主子式 Δ₂ 的精确值。

### `GET /api/health`

健康检查，返回 `{"status": "ok"}`。

## 项目结构

```
├── docker-compose.yml      # api / web / verify 三服务，健康检查与端口配置
├── backend/                # FastAPI：精确有理数 Kharitonov + Hurwitz 裁决
│   ├── app/kharitonov.py   #   四项循环顶点构造、Bareiss 精确主子式
│   ├── app/main.py         #   /api/audit、/api/health
│   └── tests/              #   模式、主子式解析值、API 端到端测试
├── frontend/               # React + Vite，nginx 静态托管并反代 /api
└── verify/                 # Playwright 浏览器验收服务
```
