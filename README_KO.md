[English](README_EN.md) | 한국어 | [日本語](README_JA.md) | [中文](README_ZH.md)

# YouRich — Claude Code와 Codex를 위한 투자 리서치 프레임워크

> 구조화된 리서치. 결정론적 금융 계산. 추적 가능한 근거.

**YouRich**는 Claude Code와 Codex에서 사용하는 오픈소스 투자 리서치 Skill입니다. 공개기업 분석에 반복해서 사용할 수 있는 리서치 절차, 정확한 금융 계산, 가치평가, 재무건전성 분석, 리스크 점검, 근거 검증을 코딩 에이전트에 추가합니다.

YouRich는 자체 AI 모델을 제공하지 않으며 독립적인 주식 분석 앱도 아닙니다. Claude Code 또는 Codex가 추론과 정성적 리서치를 담당하고, YouRich는 그 아래에서 금융 계산과 검증 절차를 담당합니다.

**현재 버전: v0.4.2 — TTM Selection Correctness Hotfix**

v0.4.2는 annual-plus-YTD SEC fact로 rolling TTM을 올바르게 선택하고,
valuation label이 각 metric JSON의 명시적 basis를 따르도록 정리합니다.

[왜 YouRich인가?](#그냥-ai에게-물어보면-안-되나요) · [아키텍처](#아키텍처) · [기능](#기능) · [빠른 시작](#빠른-시작) · [v0.3 데이터 정확성](#v030-financial-data-correctness) · [방법론](#방법론)

---

## 그냥 AI에게 물어보면 안 되나요?

AI에게 특정 종목이 매력적인지 물어보는 것은 쉽습니다. 문제는 답변을 만들 수 있느냐가 아니라, 그 답변의 금융 숫자가 일관되고 재현 가능하며 근거를 추적할 수 있느냐입니다.

### 1. 중요한 금융 계산은 결정론적으로 처리합니다

LLM은 해석에는 유용하지만 중요한 금융 계산을 자유로운 추론에 맡기면 안 됩니다.

YouRich는 Python에서 금융 계산을 실행하고 중요한 연산에는 `Decimal`을 사용합니다.

```text
시장 데이터 + SEC 재무 데이터
            ↓
    결정론적 Python 스크립트
            ↓
 가치평가 / 재무품질 / 리스크
            ↓
       Claude 또는 Codex
            ↓
       최종 투자 리서치
```

에이전트는 시가총액, NCAV, Graham Number, 마진, 비율, 추세, 리스크 플래그 등을 다시 머릿속으로 계산하지 않고 YouRich가 계산한 값을 사용합니다.

### 2. 없는 데이터는 없는 상태로 남깁니다

YouRich가 값을 검증할 수 없으면 `null`, warning 또는 insufficient-data 상태로 반환합니다.

누락값을 0으로 바꾸거나 시장가격을 추측하거나 빈칸을 조용히 채우지 않습니다.

```json
{
  "price": null,
  "warnings": ["MARKET_PROVIDER_FAILED"]
}
```

### 3. 중요한 지표는 출처와 계산 근거를 남깁니다

YouRich는 재무 값의 출처와 파생 지표가 어떤 입력으로 계산되었는지 기록합니다.

대표적으로 다음 metadata를 추적합니다.

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

이를 통해 에이전트가 **보고된 사실**, **파생 지표**, **정성적 해석**을 구분할 수 있습니다.

### 4. 같은 리서치 절차를 반복해서 사용할 수 있습니다

YouRich는 기업 분석, 가치평가, 재무건전성, 재무 리스크, 기업 비교, 투자 thesis 작성에 같은 workflow를 적용합니다.

회사마다 전혀 다른 형식의 답변이 나오는 대신 동일한 기준으로 비교하기 쉬워집니다.

### 5. Claude Code와 Codex 안에서 바로 사용합니다

YouRich는 별도의 대시보드를 하나 더 만드는 프로젝트가 아닙니다.

한 번 설치한 뒤 평소처럼 에이전트에게 질문하면 됩니다.

```text
YouRich로 NVIDIA를 분석해줘.
AMD와 Intel을 투자 관점에서 비교해줘.
Microsoft는 비싼 편이야?
Tesla의 재무 리스크를 점검해줘.
```

---

## 아키텍처

```text
사용자
  ↓
Claude Code / Codex
  ↓
YouRich Skill
  ↓
구조화된 리서치 워크플로
  ├─ 재무 데이터
  ├─ 가치평가
  ├─ 재무건전성
  ├─ 리스크 점검
  └─ 근거 검증
  ↓
결정론적 Python 도구
  ↓
에이전트 추론 + 공개자료 정성 분석
  ↓
최종 투자 리서치
```

두 환경 모두 하나의 canonical skill을 사용합니다.

```text
skill/yourich/
├── SKILL.md
├── scripts/
├── references/
└── assets/
```

`SKILL.md`가 source of truth입니다. Claude Code와 Codex는 서로 다른 투자 로직을 유지하는 것이 아니라 같은 Skill을 각 플랫폼 방식으로 패키징합니다.

---

## 기능

### 리서치 모드

| 모드 | 목적 |
|---|---|
| 전체 분석 | 사업, 재무, 가치평가, 리스크, Bull/Bear Case, 결론 |
| Valuation | 가격 기반 가치평가 지표와 valuation 중심 결론 |
| Financials | 기업 재무 데이터 수집 및 정규화 |
| Risk | 재무건전성과 정량 리스크 점검 |
| Compare | 여러 종목에 동일한 방법론 적용 |
| Thesis | 정량 근거와 정성 리서치를 결합 |

### 가치평가 지표

필요한 데이터가 존재하는 경우 다음을 계산합니다.

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

### 재무 품질

다음 항목을 지원합니다.

- 매출 성장
- 이익 성장
- gross / operating / net margin
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

### 리스크 점검

정량적으로 다음과 같은 문제를 확인합니다.

- 유동성 약화
- 과도한 부채
- negative equity
- 이익 악화
- FCF 악화
- 마진 악화
- 주식 희석
- 밸류에이션 리스크

정성적 리스크는 Claude Code 또는 Codex가 공개 근거를 바탕으로 분석하며, 결정론적 결과와 구분합니다.

---

## v0.3.0 Financial Data Correctness

v0.3은 기능 수를 늘리는 대신 금융 입력값 자체의 정확성을 높이는 데 집중합니다.

### SEC Fact 선택

SEC Company Facts를 다음과 같은 metadata를 기준으로 정규화합니다.

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

중복 fact는 filing 시점과 reporting context를 고려해 정리하며 restatement는 best-effort 방식으로 감지합니다.

### Annual / Quarterly / TTM / Snapshot 구분

손익계산서와 현금흐름 항목은 기간을 구분합니다.

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

대차대조표 항목은 합산하지 않고 최신 snapshot을 사용합니다.

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

### 가치평가 계산 기준

```text
P/E       = Market Price / TTM Diluted EPS
P/S       = Market Cap / TTM Revenue
FCF Yield = TTM FCF / Market Cap
P/B       = Market Cap / Latest Equity
```

기간, 통화, 주식 수 데이터가 맞지 않으면 억지로 계산하지 않고 missing data 또는 warning을 반환합니다.

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

## 데이터 소스

### 재무 데이터

공개기업 fundamentals에는 **SEC Company Facts**를 사용합니다.

### 시장가격

기본 market quote fallback chain:

1. Yahoo chart endpoint — 비공식 / 지연 데이터
2. Stooq CSV endpoint — 비공식 / 지연 데이터
3. Alpha Vantage Global Quote — 선택형 API key provider

```text
YOURICH_MARKET_PROVIDER=alpha_vantage
YOURICH_MARKET_API_KEY=...
```

provider가 실패하면 warning을 반환하며 가격을 만들어내지 않습니다.

### Cache

- market quote: 15분
- SEC fundamentals: 24시간

```text
YOURICH_CACHE_DIR=...
```

---

## 빠른 시작

### 요구사항

- Python 3.11+
- Claude Code 또는 OpenAI Codex
- Git

### 1. Clone

```bash
git clone https://github.com/gaedsstudio/YouRich.git
cd YouRich
```

### 2. 설치

macOS / Linux:

```bash
./install.sh
```

Windows PowerShell:

```powershell
./install.ps1
```

설치 스크립트는 지원되는 에이전트 환경을 확인한 뒤 동일한 `skill/yourich` source를 설치합니다. 기존의 무관한 설정은 덮어쓰지 않습니다.

### 3. Claude Code

```text
YouRich를 사용해서 NVIDIA를 분석해줘.
AMD와 Intel을 비교해줘.
Microsoft의 valuation을 분석해줘.
Tesla의 재무 리스크를 확인해줘.
```

### 4. Codex

```text
$yourich Analyze NVIDIA.
```

또는 자연어로:

```text
YouRich를 사용해서 AAPL과 MSFT를 투자 관점에서 비교해줘.
```

---

## 내부 도구

```bash
cd skill/yourich

python scripts/fetch_financials.py AAPL
python scripts/fetch_financials.py AAPL --debug
python scripts/valuation.py --ticker AAPL
python scripts/financial_health.py --ticker AAPL
python scripts/risk.py --ticker AAPL
python scripts/compare.py AAPL MSFT
```

모든 스크립트는 구조화된 JSON을 출력합니다.

### SEC 선택 과정 Debug

```bash
python scripts/fetch_financials.py AAPL --debug
```

어떤 SEC concept가 선택되고 제외되었는지 확인할 수 있습니다.

---

## 방법론

전체 분석은 다음 순서를 따릅니다.

```text
1. 기업 / ticker 식별
2. 재무 데이터 수집
3. 기간과 field 정규화
4. missing data / data quality 확인
5. 필요한 경우 사업 정성 리서치
6. 결정론적 valuation 실행
7. 재무품질 검사
8. 정량 리스크 검사
9. 핵심 주장 근거 검증
10. Bull Case 작성
11. Bear Case 작성
12. 투자 thesis 작성
```

우선순위는 다음과 같습니다.

```text
YouRich deterministic data
        ↓
YouRich evidence / provenance
        ↓
public qualitative research
        ↓
Claude Code / Codex interpretation
```

### 기본 리서치 출력

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

직접적인 매수/매도 명령 대신 다음과 같은 근거 중심의 결론을 사용합니다.

- `ATTRACTIVE VALUATION`
- `FAIRLY VALUED`
- `EXPENSIVE`
- `HIGH FINANCIAL RISK`
- `INSUFFICIENT DATA`
- `HIGH QUALITY / EXPENSIVE`
- `LOW QUALITY / CHEAP`

---

## 개발

```bash
python -m pip install pytest ruff basedpyright

python -m ruff format .
python -m ruff check .
python -m basedpyright
python -m pytest -q
```

현재 v0.4 기준: **35 tests passed**.

---

## 설계 원칙

1. **재무 데이터를 만들어내지 않는다.**
2. **중요 계산은 deterministic tool을 사용한다.**
3. **reported fact와 derived metric을 구분한다.**
4. **기간, 단위, 통화, 출처를 추적한다.**
5. **불확실성을 숨기지 않는다.**
6. **독립 주식 앱이 아니라 agent-native framework로 유지한다.**

---

## 향후 방향

- 10-K / 10-Q 심층 리서치 workflow
- 더 풍부한 qualitative evidence template
- multiple-share-class 처리 강화
- SEC financial mapping 확장
- 기업 비교 및 audit workflow 강화

---

## 면책

YouRich는 교육 및 투자 리서치 보조 목적으로 제공됩니다.

개인화된 투자 자문, 수익 보장, 거래 실행, 확정적인 매수/매도 지시를 제공하지 않습니다. 시장 데이터는 지연되거나 제공되지 않을 수 있습니다. 중요한 정보는 직접 다시 확인하고 최종 투자 판단은 사용자가 내려야 합니다.

---

## 라이선스

MIT License

---

YouRich가 유용하다면 GitHub Star를 남겨주세요.

**Repository:** https://github.com/gaedsstudio/YouRich
