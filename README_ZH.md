[English](README_EN.md) | [한국어](README_KO.md) | [日本語](README_JA.md) | 中文

# YouRich — 面向 Claude Code 与 Codex 的投资研究框架

> 结构化研究。确定性金融计算。可追溯证据。

**YouRich** 是一个用于 Claude Code 与 Codex 的开源投资研究 Skill。它为上市公司研究提供可重复的研究流程、精确金融计算、估值、财务质量分析、风险检查与证据验证。

YouRich 不提供自己的 AI 模型，也不是一个独立的股票分析应用。Claude Code 或 Codex 负责推理与定性研究，YouRich 负责底层的金融计算与验证纪律。

**当前里程碑：v0.3.1 — TTM Correctness Hotfix**

v0.4 增加 SEC 10-K/10-Q filing 获取、section parsing、compact research
context、business quality、management / capital allocation evidence，以及定性
结论所需的 `Claim -> Evidence -> Interpretation` 规则。

---

## 为什么不能直接问 AI？

直接问 AI “这只股票是否值得投资”很容易。真正的问题不是 AI 能不能生成答案，而是答案中的金融数据是否一致、可复现并且能够追溯到来源。

### 1. 重要金融计算必须是确定性的

LLM 很适合解释，但关键金融计算不应该依赖自由形式推理。

YouRich 使用 Python 执行金融计算，并在重要计算中使用 `Decimal`。

```text
市场数据 + SEC 财务数据
            ↓
      确定性 Python 脚本
            ↓
   估值 / 财务质量 / 风险
            ↓
       Claude 或 Codex
            ↓
         最终投资研究
```

Agent 应使用 YouRich 计算出的市值、NCAV、Graham Number、利润率、比率、趋势与风险标记，而不是在模型推理中重新计算。

### 2. 缺失数据保持缺失

如果 YouRich 无法验证某个值，就返回 `null`、warning 或 insufficient-data 状态。

不会把缺失值替换成 0，不会猜测市场价格，也不会悄悄补全空白。

```json
{
  "price": null,
  "warnings": ["MARKET_PROVIDER_FAILED"]
}
```

### 3. 重要指标具有完整来源信息

YouRich 会记录财务数值来自哪里，以及派生指标使用了哪些输入。

- SEC concept
- unit
- fiscal year / fiscal period
- filing form
- filing date
- accession number
- period start / end
- market provider
- mapping confidence
- restatement status
- metric inputs

这样 Agent 可以区分 **reported fact**、**derived metric** 和 **qualitative interpretation**。

### 4. 同一研究流程可以重复使用

YouRich 为公司分析、估值、财务质量、财务风险、公司比较和投资 thesis 定义一致的 workflow。

### 5. 直接运行在 Claude Code / Codex 中

YouRich 不是另一个需要一直打开的 Dashboard。

安装后，像平时一样向 Agent 提问即可：

```text
使用 YouRich 分析 NVIDIA。
从投资角度比较 AMD 和 Intel。
Microsoft 是否估值过高？
检查 Tesla 的财务风险。
```

---

## 架构

```text
用户
  ↓
Claude Code / Codex
  ↓
YouRich Skill
  ↓
结构化研究工作流
  ├─ 财务数据
  ├─ 估值
  ├─ 财务质量
  ├─ 风险检查
  └─ 证据验证
  ↓
确定性 Python Tools
  ↓
Agent 推理 + 公开资料定性研究
  ↓
最终投资研究
```

两个环境使用同一个 canonical skill。

```text
skill/yourich/
├── SKILL.md
├── scripts/
├── references/
└── assets/
```

`SKILL.md` 是 source of truth。

---

## 功能

### 研究模式

| 模式 | 用途 |
|---|---|
| Full analysis | 业务、财务、估值、风险、Bull/Bear Case、结论 |
| Valuation | 与价格相关的估值指标 |
| Financials | 获取并标准化财务数据 |
| Risk | 财务质量与定量风险检查 |
| Compare | 对多个 ticker 应用同一方法 |
| Thesis | 将定量证据与定性研究结合 |

### 估值指标

在数据可用时可计算：

- Market Cap
- TTM P/E
- latest P/B
- TTM P/S
- TTM FCF Yield
- TTM Earnings Yield
- NCAV
- NCAV per share
- Price / NCAV
- Graham Number
- Margin of Safety
- Normalized EPS

### 财务质量

- revenue growth
- earnings growth
- gross / operating / net margins
- FCF margin
- ROE
- ROA
- ROIC
- current ratio
- quick ratio
- debt / equity
- debt / assets
- earnings consistency
- FCF consistency
- share dilution

### 风险检查

- 流动性不足
- 负债过高
- negative equity
- 盈利恶化
- FCF 恶化
- margin deterioration
- dilution
- valuation risk

定性风险由 Claude Code / Codex 基于公开证据分析，并与确定性结果分离。

---

## v0.3.0 Financial Data Correctness

v0.3 的重点不是增加更多表面功能，而是提高金融输入数据的正确性。

### SEC Fact Selection

SEC Company Facts 使用以下 metadata 进行标准化：

```text
concept
unit
FY / FP
form
filed date
start / end
frame
accession number
amendment status
```

重复 fact 会结合 filing 时间和 reporting context 处理，restatement 采用 best-effort 检测。

### Annual / Quarterly / TTM / Snapshot

利润表与现金流数据区分期间。

```text
Revenue
Operating Income
Net Income
EPS
Operating Cash Flow
CapEx
Free Cash Flow
        ↓
       TTM
```

资产负债表数据不会累加，而是使用最新合适 snapshot。

```text
Cash
Current Assets
Current Liabilities
Total Assets
Total Liabilities
Debt
Equity
Shares Outstanding
        ↓
 latest balance-sheet snapshot
```

### 估值计算基准

```text
P/E       = Market Price / TTM Diluted EPS
P/S       = Market Cap / TTM Revenue
FCF Yield = TTM FCF / Market Cap
P/B       = Market Cap / Latest Equity
```

如果期间、货币或股份数据不可比较，YouRich 返回 missing data 或 warning，而不是强行计算。

### Data Quality

```json
{
  "data_quality": {
    "market_data": "delayed",
    "fundamentals": "current",
    "ttm_coverage": "complete",
    "mapping_confidence": "high",
    "currency_match": true
  }
}
```

---

## 数据源

### Fundamentals

上市公司 fundamentals 使用 **SEC Company Facts**。

### Market Price

默认 market quote fallback：

1. Yahoo chart endpoint — 非官方 / delayed
2. Stooq CSV endpoint — 非官方 / delayed
3. Alpha Vantage Global Quote — 可选 API key provider

```text
YOURICH_MARKET_PROVIDER=alpha_vantage
YOURICH_MARKET_API_KEY=...
```

Provider 失败时返回 warning，不会伪造价格。

### Cache

- market quote：15 分钟
- SEC fundamentals：24 小时

```text
YOURICH_CACHE_DIR=...
```

---

## 快速开始

### 要求

- Python 3.11+
- Claude Code 或 OpenAI Codex
- Git

### 1. Clone

```bash
git clone https://github.com/gaedsstudio/YouRich.git
cd YouRich
```

### 2. Install

macOS / Linux:

```bash
./install.sh
```

Windows PowerShell:

```powershell
./install.ps1
```

### 3. Claude Code

```text
使用 YouRich 分析 NVIDIA。
比较 AMD 与 Intel。
分析 Microsoft 的 valuation。
检查 Tesla 的财务风险。
```

### 4. Codex

```text
$yourich Analyze NVIDIA.
```

也可以直接使用自然语言：

```text
Use YouRich to compare AAPL and MSFT as investments.
```

---

## 内部工具

```bash
cd skill/yourich

python scripts/fetch_financials.py AAPL
python scripts/fetch_financials.py AAPL --debug
python scripts/valuation.py --ticker AAPL
python scripts/financial_health.py --ticker AAPL
python scripts/risk.py --ticker AAPL
python scripts/compare.py AAPL MSFT
```

所有脚本输出结构化 JSON。

---

## 方法论

```text
1. 识别公司 / ticker
2. 获取财务数据
3. 标准化期间和 field
4. 检查 missing data / data quality
5. 必要时进行业务定性研究
6. 执行 deterministic valuation
7. 执行财务质量检查
8. 执行定量风险检查
9. 验证重要 claim 的 evidence
10. 构建 Bull Case
11. 构建 Bear Case
12. 形成 Investment Thesis
```

优先级：

```text
YouRich deterministic data
        ↓
YouRich evidence / provenance
        ↓
public qualitative research
        ↓
Claude Code / Codex interpretation
```

### 默认研究输出

```text
Company
Ticker

Investment Summary

Business
Financial Quality
Valuation
Risks

Bull Case
Bear Case

Key Evidence

Conclusion
```

推荐使用基于证据的结论：

- `ATTRACTIVE VALUATION`
- `FAIRLY VALUED`
- `EXPENSIVE`
- `HIGH FINANCIAL RISK`
- `INSUFFICIENT DATA`
- `HIGH QUALITY / EXPENSIVE`
- `LOW QUALITY / CHEAP`

---

## 开发

```bash
python -m pip install pytest ruff basedpyright

python -m ruff format .
python -m ruff check .
python -m basedpyright
python -m pytest -q
```

当前 v0.4 baseline：**35 tests passing**。

---

## 设计原则

1. 不伪造金融数据。
2. 重要计算使用 deterministic tool。
3. 区分 reported fact 与 derived metric。
4. 追踪期间、单位、货币与来源。
5. 暴露不确定性，而不是隐藏它。
6. 保持 agent-native framework，而不是变成独立股票 App。

---

## 未来方向

- 更深入的 10-K / 10-Q 研究 workflow
- 更丰富的 qualitative evidence template
- 改进 multiple-share-class 处理
- 扩展 SEC financial mapping
- 加强 company comparison / audit workflow

---

## 免责声明

YouRich 仅用于教育与投资研究辅助。

它不提供个性化投资建议、不保证收益、不执行交易，也不发出确定性的 BUY / SELL 指令。市场数据可能延迟或暂时不可用。请自行核验重要信息，并独立做出最终投资判断。

---

## 许可证

MIT License

---

如果 YouRich 对你有帮助，欢迎给项目一个 GitHub Star。

**Repository:** https://github.com/gaedsstudio/YouRich
