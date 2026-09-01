[English](README_EN.md) | [한국어](README_KO.md) | 日本語 | [中文](README_ZH.md)

# YouRich — Claude Code / Codex 向け投資リサーチフレームワーク

> 構造化されたリサーチ。決定論的な金融計算。追跡可能な根拠。

**YouRich** は Claude Code と Codex で利用するオープンソースの投資リサーチ Skill です。上場企業の調査に、再利用可能なリサーチ手順、正確な金融計算、バリュエーション、財務品質分析、リスクチェック、エビデンス検証を追加します。

YouRich 自体は AI モデルを提供せず、単体の株式分析アプリでもありません。Claude Code または Codex が推論と定性的リサーチを担当し、YouRich はその下で金融計算と検証プロセスを担当します。

**現在のマイルストーン: v0.4.1 — Research Layer + Financial Correctness**

v0.4 では SEC 10-K/10-Q filing の取得、section parsing、compact research
context、business quality、management / capital allocation evidence を追加しました。
v0.3.1 では重複する SEC duration fact と TTM reconstruction を修正しました。
v0.4.1 はその両方を統合し、valuation metadata を実際の basis に合わせます。

---

## なぜ AI に直接聞くだけでは不十分なのか

AI に「この株は魅力的か」と聞くこと自体は簡単です。問題は回答を生成できるかではなく、その金融数値が一貫していて、再現可能で、根拠を追跡できるかです。

### 1. 重要な金融計算は決定論的に処理

LLM は解釈には有用ですが、重要な金融計算を自由形式の推論に任せるべきではありません。

YouRich は Python で金融計算を実行し、重要な計算では `Decimal` を使用します。

```text
市場データ + SEC 財務データ
            ↓
    決定論的 Python スクリプト
            ↓
 バリュエーション / 品質 / リスク
            ↓
       Claude または Codex
            ↓
        最終投資リサーチ
```

エージェントは時価総額、NCAV、Graham Number、各種マージン、比率、トレンド、リスクフラグを再計算せず、YouRich が算出した値を利用します。

### 2. 欠損データは欠損のまま

検証できない値は `null`、warning、または insufficient-data として返します。

欠損を 0 に置き換えたり、市場価格を推測したり、空欄を黙って埋めたりしません。

```json
{
  "price": null,
  "warnings": ["MARKET_PROVIDER_FAILED"]
}
```

### 3. 重要な指標には provenance を持たせる

YouRich は財務値の出所と、派生指標がどの入力から計算されたかを記録します。

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

これにより **reported fact**、**derived metric**、**qualitative interpretation** を区別できます。

### 4. 同じ研究工程を再利用できる

企業分析、バリュエーション、財務品質、財務リスク、企業比較、investment thesis に同じ workflow を適用します。

### 5. Claude Code / Codex の中で使う

YouRich は新しいダッシュボードを増やすためのプロジェクトではありません。

```text
YouRich で NVIDIA を分析して。
AMD と Intel を投資対象として比較して。
Microsoft は割高？
Tesla の財務リスクを確認して。
```

---

## アーキテクチャ

```text
ユーザー
  ↓
Claude Code / Codex
  ↓
YouRich Skill
  ↓
構造化リサーチワークフロー
  ├─ 財務データ
  ├─ バリュエーション
  ├─ 財務品質
  ├─ リスクチェック
  └─ エビデンス検証
  ↓
決定論的 Python Tools
  ↓
Agent Reasoning + 公開情報の定性分析
  ↓
最終投資リサーチ
```

両環境で同じ canonical skill を使用します。

```text
skill/yourich/
├── SKILL.md
├── scripts/
├── references/
└── assets/
```

`SKILL.md` が source of truth です。

---

## 機能

### リサーチモード

| モード | 用途 |
|---|---|
| Full analysis | 事業、財務、評価、リスク、Bull/Bear Case、結論 |
| Valuation | 価格依存の評価指標 |
| Financials | 財務データ取得と正規化 |
| Risk | 財務品質と定量リスク |
| Compare | 複数銘柄に同一方法論を適用 |
| Thesis | 定量エビデンスと定性リサーチを統合 |

### バリュエーション指標

必要なデータが存在する場合:

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

### 財務品質

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

### リスクチェック

- 流動性の弱さ
- 過剰負債
- negative equity
- 利益悪化
- FCF 悪化
- margin deterioration
- dilution
- valuation risk

定性的リスクは Claude Code / Codex が公開エビデンスに基づいて分析し、決定論的な結果と分離します。

---

## v0.3.0 Financial Data Correctness

v0.3 は機能追加よりも、金融入力データそのものの正確性を改善することに重点を置いています。

### SEC Fact Selection

SEC Company Facts を次の metadata で正規化します。

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

重複 fact は filing の新しさと reporting context を考慮して整理し、restatement は best-effort で検出します。

### Annual / Quarterly / TTM / Snapshot

損益計算書・キャッシュフロー項目は期間を区別します。

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

貸借対照表項目は合算せず、最新の適切な snapshot を使用します。

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

### 評価計算の基準

```text
P/E       = Market Price / TTM Diluted EPS
P/S       = Market Cap / TTM Revenue
FCF Yield = TTM FCF / Market Cap
P/B       = Market Cap / Latest Equity
```

期間、通貨、株式数データが比較可能でなければ、無理に計算せず missing data または warning を返します。

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

## データソース

### Fundamentals

上場企業の fundamentals には **SEC Company Facts** を使用します。

### Market Price

デフォルトの market quote fallback:

1. Yahoo chart endpoint — 非公式 / delayed
2. Stooq CSV endpoint — 非公式 / delayed
3. Alpha Vantage Global Quote — optional API key provider

```text
YOURICH_MARKET_PROVIDER=alpha_vantage
YOURICH_MARKET_API_KEY=...
```

provider が失敗しても価格を推測しません。

### Cache

- market quote: 15 分
- SEC fundamentals: 24 時間

```text
YOURICH_CACHE_DIR=...
```

---

## クイックスタート

### 必要環境

- Python 3.11+
- Claude Code または OpenAI Codex
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
YouRich を使って NVIDIA を分析して。
AMD と Intel を比較して。
Microsoft の valuation を調べて。
Tesla の財務リスクを確認して。
```

### 4. Codex

```text
$yourich Analyze NVIDIA.
```

または自然言語:

```text
Use YouRich to compare AAPL and MSFT as investments.
```

---

## 内部ツール

```bash
cd skill/yourich

python scripts/fetch_financials.py AAPL
python scripts/fetch_financials.py AAPL --debug
python scripts/valuation.py --ticker AAPL
python scripts/financial_health.py --ticker AAPL
python scripts/risk.py --ticker AAPL
python scripts/compare.py AAPL MSFT
```

すべて構造化 JSON を出力します。

---

## 方法論

```text
1. 企業 / ticker を特定
2. 財務データ取得
3. 期間と field の正規化
4. missing data / data quality 確認
5. 必要に応じて事業の定性リサーチ
6. deterministic valuation
7. 財務品質チェック
8. 定量リスクチェック
9. 重要 claim の evidence 検証
10. Bull Case
11. Bear Case
12. Investment Thesis
```

優先順位:

```text
YouRich deterministic data
        ↓
YouRich evidence / provenance
        ↓
public qualitative research
        ↓
Claude Code / Codex interpretation
```

### デフォルト出力

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

推奨する結論表現:

- `ATTRACTIVE VALUATION`
- `FAIRLY VALUED`
- `EXPENSIVE`
- `HIGH FINANCIAL RISK`
- `INSUFFICIENT DATA`
- `HIGH QUALITY / EXPENSIVE`
- `LOW QUALITY / CHEAP`

---

## 開発

```bash
python -m pip install pytest ruff basedpyright

python -m ruff format .
python -m ruff check .
python -m basedpyright
python -m pytest -q
```

現在の v0.4 baseline: **35 tests passing**.

---

## 設計原則

1. 金融データを捏造しない。
2. 重要な計算は deterministic tool を使う。
3. reported fact と derived metric を分離する。
4. 期間、単位、通貨、出所を追跡する。
5. 不確実性を隠さない。
6. 単体株式アプリではなく agent-native framework として維持する。

---

## 今後の方向

- 10-K / 10-Q の深いリサーチ workflow
- qualitative evidence template の強化
- multiple-share-class 対応
- SEC financial mapping の拡張
- comparison / audit workflow の改善

---

## 免責事項

YouRich は教育および投資リサーチ支援を目的としています。

個別の投資助言、利益保証、取引執行、確定的な BUY / SELL 指示は提供しません。市場データは遅延または取得不能になる場合があります。重要な情報は必ず再確認し、最終的な投資判断は利用者自身で行ってください。

---

## ライセンス

MIT License

---

YouRich が役に立ったら GitHub Star をお願いします。

**Repository:** https://github.com/gaedsstudio/YouRich
