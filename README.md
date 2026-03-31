# ESG ETF 점수 분석 엔진 (ESG ETF Scoring Engine)

## 📌 프로젝트 개요

본 프로젝트는 ETF를 구성하는 종목의 ESG(Environmental, Social, Governance) 등급과 비중 데이터를 기반으로 ETF의 실제 ESG 수준을 정량적으로 분석하는 데이터 기반 ESG 점수 계산 엔진이다.

기존 ESG 투자는 상품명이나 마케팅 정보에 의존하는 경우가 많지만 본 프로젝트는 실제 편입 종목과 ESG 데이터를 결합하여 ETF의 ESG 수준을 객관적으로 평가하는 것을 목표로 한다.

---

## 🚀 핵심 기능

### 1️⃣ ESG 점수 계산 엔진

- KCGS ESG 등급(S, A+, A, B+, B, C, D)을 수치화
- ETF 구성 종목 비중을 반영한 가중 평균 방식 적용

```
ETF ESG = Σ (ESG × 비중)
ETF E   = Σ (E × 비중)
ETF S   = Σ (S × 비중)
ETF G   = Σ (G × 비중)
```

---

### 2️⃣ 데이터 파이프라인

- ESG 데이터 전처리 (KCGS)
- ETF 구성 데이터 정리
- 종목코드 기준 데이터 조인
- 비중 정규화

---

### 3️⃣ ETF 비교 분석

- ETF별 ESG / E / S / G 점수 제공
- ETF 간 상대 비교 가능

---

### 4️⃣ 핵심 인사이트 (실험 결과)

> "친환경(태양광) ETF가 반드시 ESG 점수가 높은 것은 아니다"

실제 분석 결과:

| ETF                 |        ESG |    E |          S |          G |
| ------------------- | ---------: | ---: | ---------: | ---------: |
| KODEX_200ESG        |       5.00 | 5.08 |       5.62 |       4.67 |
| TIGER_GREEN_NEWDEAL |       5.00 | 5.08 |       5.62 |       4.67 |
| SOL_CLIMATE         |       5.00 | 5.08 |       5.62 |       4.67 |
| SOLAR_THEME         | **4.85 ↓** | 5.02 | **5.45 ↓** | **4.46 ↓** |

"친환경(태양광) ETF가 반드시 ESG 점수가 높은 것은 아니다"

본 프로젝트에서는 ESG ETF 3종(KODEX_200ESG, TIGER_GREEN_NEWDEAL, SOL_CLIMATE)과 태양광 테마 ETF(SOLAR_THEME)를 대상으로 ESG 점수를 비교하였다.

📊 전체 ESG 보정 점수
KODEX_200ESG: 5.004066
SOL_CLIMATE: 5.003965
TIGER_GREEN_NEWDEAL: 5.003966
SOLAR_THEME: 4.848301 ⬇️

👉 특정 친환경 산업(태양광)에 투자하는 ETF가 반드시 ESG 관점에서 우수한 투자 상품이라고 볼 수 없음을 데이터 기반으로 확인할 수 있다.

---

## 🧠 기술 스택

- Python
- Pandas / NumPy
- 데이터 전처리 및 분석
- (확장) Naver 뉴스 API 기반 ESG 이슈 분석

---

## 📂 프로젝트 구조

```
.
├── data/
│   ├── raw/          # 원본 데이터 (KCGS, ETF CSV)
│   └── processed/    # 전처리 및 결과 데이터
├── src/
│   ├── merge_etf_files.py
│   ├── etf_esg_pipeline.py
│   └── news/         # 뉴스 API 실험 코드
├── README.md
├── requirements.txt
└── .gitignore
```

---

## ⚙️ 실행 방법

### 1️⃣ ETF 데이터 병합

```
python src/merge_etf_files.py
```

### 2️⃣ ESG 점수 계산

```
python src/etf_esg_pipeline.py --etf-id-col ETF명
```

---

## 🔬 확장 기능

- 네이버 뉴스 API를 활용한 ESG 관련 뉴스 수집
- E / S / G 키워드 기반 분류
- 향후 AI 기반 ESG 리스크 분석으로 확장 가능

---

## 📈 향후 계획

- ESG 기반 ETF 추천 시스템
- AI 기반 투자 판단 설명 기능
- ESG 뉴스 기반 리스크 분석 고도화

---

## 💡 프로젝트 의의

본 프로젝트는 단순한 ESG 정보 제공이 아닌

👉 데이터 기반 ESG 점수 산출
👉 ETF 간 객관적 비교
👉 투자 의사결정 지원

을 목표로 하는 ESG 금융 분석 엔진이다.
