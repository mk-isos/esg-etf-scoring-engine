#!/usr/bin/env python3
"""
ETF + KCGS ESG 전처리/조인 파이프라인

기본 실행:
    python etf_esg_pipeline.py

옵션 예시:
    python etf_esg_pipeline.py \
        --esg-path data/kcgs_esg.xlsx \
        --etf-path data/etf_holdings.csv \
        --output-dir data \
        --missing-grade-policy zero \
        --etf-id-col ETF코드
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import numpy as np
import pandas as pd


# ----------------------------
# 설정/상수
# ----------------------------
# GRADE_TO_SCORE = {
#     "S": 7,
#     "A+": 6,
#     "A": 5,
#     "B+": 4,
#     "B": 3,
#     "C": 2,
#     "D": 1,
# }

GRADE_TO_SCORE = {
    "S": 10,
    "A+": 9,
    "A": 8,
    "B+": 7,
    "B": 6,
    "C": 4,
    "D": 2,
    "등급없음": 0
}


SCORE_COL_MAP = {
    "ESG등급": "ESG점수",
    "환경": "E점수",
    "사회": "S점수",
    "지배구조": "G점수",
}

ESG_REQUIRED_COLS = ["기업코드", "ESG등급", "환경", "사회", "지배구조"]
ETF_REQUIRED_COLS = ["종목코드", "시가총액 구성비중"]


class DataValidationError(Exception):
    """입력 데이터 스키마/값 검증 오류."""


@dataclass
class PipelineConfig:
    esg_path: str = "data/kcgs_esg.xlsx"
    etf_path: str = "data/etf_holdings.csv"
    output_dir: str = "data"
    missing_grade_policy: str = "zero"  # "zero" or "exclude"
    etf_id_col: Optional[str] = None
    esg_sheet_name: Union[int, str] = 0


# ----------------------------
# 유틸리티
# ----------------------------
def ensure_required_columns(df: pd.DataFrame, required_cols: list[str], dataset_name: str) -> None:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise DataValidationError(f"[{dataset_name}] 필수 컬럼 누락: {missing}")


def normalize_six_digit_code(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0+$", "", regex=True)        # 엑셀 숫자형 잔재 제거 (예: 5930.0)
    s = s.str.replace(r"[^0-9]", "", regex=True)       # 숫자만 남김
    s = s.replace("", pd.NA)
    s = s.str[-6:].str.zfill(6)                        # 6자리 문자열 고정
    return s


def clean_grade_text(value: object) -> Optional[str]:
    if pd.isna(value):
        return None
    text = str(value).strip().upper().replace(" ", "")
    if text in {"", "등급없음", "미평가", "NONE", "N/A", "NA", "-", "NULL"}:
        return None
    return text


def grade_to_score(value: object) -> float:
    g = clean_grade_text(value)
    if g is None:
        return np.nan
    return float(GRADE_TO_SCORE.get(g, np.nan))


def parse_weight_series(series: pd.Series) -> pd.Series:
    """
    시가총액 구성비중 파싱:
    - "3.12%" -> 0.0312
    - "3.12"  -> 값 분포가 1 초과면 %로 간주하여 /100
    - "0.0312" -> 그대로 유지
    """
    raw = series.astype(str).str.strip()
    has_percent = raw.str.contains("%", regex=False, na=False)

    cleaned = raw.str.replace(",", "", regex=False).str.replace("%", "", regex=False)
    values = pd.to_numeric(cleaned, errors="coerce")

    values.loc[has_percent] = values.loc[has_percent] / 100.0

    no_percent_mask = ~has_percent & values.notna()
    max_no_percent = values.loc[no_percent_mask].max(skipna=True)
    if pd.notna(max_no_percent) and max_no_percent > 1:
        values.loc[no_percent_mask] = values.loc[no_percent_mask] / 100.0

    values = values.clip(lower=0)
    return values


def load_esg_excel(path: str, sheet_name: Union[int, str] = 0) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"ESG 파일을 찾을 수 없습니다: {path}")
    try:
        return pd.read_excel(p, sheet_name=sheet_name, dtype=str)
    except ImportError as e:
        raise RuntimeError("엑셀 로딩을 위해 openpyxl 설치가 필요합니다.") from e


def load_etf_csv(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"ETF 파일을 찾을 수 없습니다: {path}")

    encodings = ["utf-8-sig", "cp949", "euc-kr", "utf-8"]
    decode_error = None

    for enc in encodings:
        try:
            return pd.read_csv(p, dtype=str, encoding=enc)
        except UnicodeDecodeError as e:
            decode_error = e

    raise ValueError(f"CSV 인코딩 판별 실패: {path}") from decode_error


# ----------------------------
# 전처리
# ----------------------------
def convert_grade_columns(df: pd.DataFrame, missing_grade_policy: str) -> Tuple[pd.DataFrame, int]:
    if missing_grade_policy not in {"zero", "exclude"}:
        raise ValueError("missing_grade_policy는 'zero' 또는 'exclude' 여야 합니다.")

    out = df.copy()
    score_cols = list(SCORE_COL_MAP.values())

    for src_col, score_col in SCORE_COL_MAP.items():
        out[score_col] = out[src_col].apply(grade_to_score)

    dropped = 0
    if missing_grade_policy == "zero":
        out[score_cols] = out[score_cols].fillna(0).astype(int)
    else:
        before = len(out)
        out = out.dropna(subset=score_cols).copy()
        dropped = before - len(out)
        out[score_cols] = out[score_cols].astype(int)

    return out, dropped


def preprocess_esg(df: pd.DataFrame, missing_grade_policy: str) -> Tuple[pd.DataFrame, int]:
    ensure_required_columns(df, ESG_REQUIRED_COLS, "KCGS ESG 데이터")

    out = df.copy()
    out["기업코드"] = normalize_six_digit_code(out["기업코드"])
    out = out[out["기업코드"].notna()].copy()

    # 동일 기업코드가 여러 평가년도에 걸쳐 존재하면 최신년도 1건만 유지
    if "평가년도" in out.columns:
        out["_평가년도_num"] = pd.to_numeric(out["평가년도"], errors="coerce")
        out = out.sort_values(["기업코드", "_평가년도_num"], ascending=[True, False])
        out = out.drop_duplicates(subset=["기업코드"], keep="first")
        out = out.drop(columns=["_평가년도_num"])
    else:
        out = out.drop_duplicates(subset=["기업코드"], keep="first")

    out, dropped_for_missing_grade = convert_grade_columns(out, missing_grade_policy)
    return out, dropped_for_missing_grade


def resolve_etf_id_col(df: pd.DataFrame, preferred_col: Optional[str]) -> Optional[str]:
    if preferred_col:
        if preferred_col not in df.columns:
            raise DataValidationError(f"지정한 ETF 식별 컬럼을 찾을 수 없습니다: {preferred_col}")
        return preferred_col

    for candidate in ["ETF코드", "ETF명", "ETF_ID", "펀드코드"]:
        if candidate in df.columns:
            return candidate
    return None


def preprocess_etf(df: pd.DataFrame, etf_id_col: Optional[str]) -> pd.DataFrame:
    ensure_required_columns(df, ETF_REQUIRED_COLS, "ETF 구성 데이터")

    out = df.copy()
    out["종목코드"] = normalize_six_digit_code(out["종목코드"])
    out = out[out["종목코드"].notna()].copy()

    out["시가총액 구성비중"] = parse_weight_series(out["시가총액 구성비중"]).fillna(0.0)

    resolved_id_col = resolve_etf_id_col(out, etf_id_col)
    if resolved_id_col:
        out["ETF_ID"] = out[resolved_id_col].astype(str).str.strip()
        out["ETF_ID"] = out["ETF_ID"].replace("", "UNKNOWN_ETF")
    else:
        out["ETF_ID"] = "SINGLE_ETF"

    # ETF별 정규화 비중 (ETF별 합계=1)
    weight_sum = out.groupby("ETF_ID")["시가총액 구성비중"].transform("sum")
    out["시가총액 구성비중_정규화"] = np.where(weight_sum > 0, out["시가총액 구성비중"] / weight_sum, 0.0)

    return out


# ----------------------------
# 조인/집계
# ----------------------------
def merge_etf_and_esg(
    cleaned_etf: pd.DataFrame,
    cleaned_esg: pd.DataFrame,
    missing_grade_policy: str,
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    score_cols = list(SCORE_COL_MAP.values())
    esg_cols = ["기업코드", "기업명", "평가년도", "ESG등급", "환경", "사회", "지배구조"] + score_cols
    esg_cols = [c for c in esg_cols if c in cleaned_esg.columns]

    merged = cleaned_etf.merge(
        cleaned_esg[esg_cols],
        left_on="종목코드",
        right_on="기업코드",
        how="left",
        indicator=True,
    )

    join_success = int((merged["_merge"] == "both").sum())
    join_missing = int((merged["_merge"] == "left_only").sum())

    stats = {
        "join_success": join_success,
        "join_missing": join_missing,
        "dropped_missing_grade_after_join": 0,
    }

    merged["조인성공"] = (merged["_merge"] == "both").astype(int)
    merged["ESG_데이터존재"] = merged["ESG점수"].notna()

    if missing_grade_policy == "zero":
        merged[score_cols] = merged[score_cols].fillna(0).astype(int)
    elif missing_grade_policy == "exclude":
        before = len(merged)
        merged = merged.dropna(subset=score_cols).copy()
        stats["dropped_missing_grade_after_join"] = int(before - len(merged))
        merged[score_cols] = merged[score_cols].astype(int)
    else:
        raise ValueError("missing_grade_policy는 'zero' 또는 'exclude' 여야 합니다.")

    # ETF 구성비중을 반영한 종목별 가중 기여 점수 (중간 데이터프레임 핵심 컬럼)
    merged["ESG_가중점수"] = merged["ESG점수"] * merged["시가총액 구성비중_정규화"]
    merged["E_가중점수"] = merged["E점수"] * merged["시가총액 구성비중_정규화"]
    merged["S_가중점수"] = merged["S점수"] * merged["시가총액 구성비중_정규화"]
    merged["G_가중점수"] = merged["G점수"] * merged["시가총액 구성비중_정규화"]

    merged = merged.drop(columns=["_merge"])
    return merged, stats


def summarize_etf_scores(merged: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for etf_id, g in merged.groupby("ETF_ID", dropna=False):
        covered_weight = float(g.loc[g["ESG_데이터존재"], "시가총액 구성비중_정규화"].sum())
        esg_w = float(g["ESG_가중점수"].sum())
        e_w = float(g["E_가중점수"].sum())
        s_w = float(g["S_가중점수"].sum())
        g_w = float(g["G_가중점수"].sum())

        rows.append(
            {
                "ETF_ID": etf_id,
                "총정규화비중합": float(g["시가총액 구성비중_정규화"].sum()),
                "ESG데이터커버비중합": covered_weight,
                "ETF_ESG점수": esg_w,
                "ETF_E점수": e_w,
                "ETF_S점수": s_w,
                "ETF_G점수": g_w,
                # 커버리지 보정 평균 (ESG 데이터가 있는 종목 비중으로 보정)
                "ETF_ESG점수_커버리지보정": (esg_w / covered_weight) if covered_weight > 0 else np.nan,
                "ETF_E점수_커버리지보정": (e_w / covered_weight) if covered_weight > 0 else np.nan,
                "ETF_S점수_커버리지보정": (s_w / covered_weight) if covered_weight > 0 else np.nan,
                "ETF_G점수_커버리지보정": (g_w / covered_weight) if covered_weight > 0 else np.nan,
            }
        )

    return pd.DataFrame(rows).sort_values("ETF_ID").reset_index(drop=True)


# ----------------------------
# 저장/실행
# ----------------------------
def save_outputs(
    cleaned_esg: pd.DataFrame,
    cleaned_etf: pd.DataFrame,
    merged: pd.DataFrame,
    output_dir: str,
) -> Dict[str, str]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    p1 = out_dir / "cleaned_esg.csv"
    p2 = out_dir / "cleaned_etf.csv"
    p3 = out_dir / "merged_etf_esg.csv"

    cleaned_esg.to_csv(p1, index=False, encoding="utf-8-sig")
    cleaned_etf.to_csv(p2, index=False, encoding="utf-8-sig")
    merged.to_csv(p3, index=False, encoding="utf-8-sig")

    return {
        "cleaned_esg.csv": str(p1),
        "cleaned_etf.csv": str(p2),
        "merged_etf_esg.csv": str(p3),
    }


def print_preview(
    cleaned_esg: pd.DataFrame,
    cleaned_etf: pd.DataFrame,
    merged: pd.DataFrame,
    join_stats: Dict[str, int],
    summary_df: pd.DataFrame,
    dropped_from_esg: int,
) -> None:
    print("\n[cleaned_esg 상위 5개 행]")
    print(cleaned_esg.head(5).to_string(index=False))

    print("\n[cleaned_etf 상위 5개 행]")
    print(cleaned_etf.head(5).to_string(index=False))

    print("\n[merged_etf_esg 상위 5개 행]")
    print(merged.head(5).to_string(index=False))

    print(f"\n조인 성공 종목 수: {join_stats['join_success']}")
    print(f"조인 누락 종목 수: {join_stats['join_missing']}")

    if dropped_from_esg > 0:
        print(f"등급 정책에 의해 ESG 원천 데이터에서 제외된 행 수: {dropped_from_esg}")
    if join_stats.get("dropped_missing_grade_after_join", 0) > 0:
        print(f"등급 정책에 의해 조인 후 제외된 행 수: {join_stats['dropped_missing_grade_after_join']}")

    print("\n[ETF 점수 요약 상위 5개 행]")
    print(summary_df.head(5).to_string(index=False))


def run_pipeline(config: PipelineConfig) -> Dict[str, pd.DataFrame]:
    if config.missing_grade_policy not in {"zero", "exclude"}:
        raise ValueError("missing_grade_policy는 'zero' 또는 'exclude' 여야 합니다.")

    esg_raw = load_esg_excel(config.esg_path, sheet_name=config.esg_sheet_name)
    etf_raw = load_etf_csv(config.etf_path)

    cleaned_esg, dropped_from_esg = preprocess_esg(esg_raw, config.missing_grade_policy)
    cleaned_etf = preprocess_etf(etf_raw, config.etf_id_col)

    merged, join_stats = merge_etf_and_esg(cleaned_etf, cleaned_esg, config.missing_grade_policy)
    summary_df = summarize_etf_scores(merged)

    saved_paths = save_outputs(cleaned_esg, cleaned_etf, merged, config.output_dir)
    print_preview(cleaned_esg, cleaned_etf, merged, join_stats, summary_df, dropped_from_esg)

    print("\n[저장 완료]")
    for name, path in saved_paths.items():
        print(f"- {name}: {path}")

    return {
        "cleaned_esg": cleaned_esg,
        "cleaned_etf": cleaned_etf,
        "merged_etf_esg": merged,
        "etf_score_summary": summary_df,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KCGS ESG + ETF 구성 데이터 전처리/조인 파이프라인")
    parser.add_argument("--esg-path", default="data/kcgs_esg.xlsx", help="KCGS ESG 엑셀 경로")
    parser.add_argument("--etf-path", default="data/etf_holdings.csv", help="ETF 구성 CSV 경로")
    parser.add_argument("--output-dir", default="data", help="출력 디렉터리")
    parser.add_argument(
        "--missing-grade-policy",
        default="zero",
        choices=["zero", "exclude"],
        help="등급없음 처리 방식: zero(0점 처리) | exclude(행 제외)",
    )
    parser.add_argument(
        "--etf-id-col",
        default=None,
        help="ETF 식별 컬럼명(복수 ETF 파일 처리 시 권장, 예: ETF코드/ETF명)",
    )
    parser.add_argument(
        "--esg-sheet-name",
        default="0",
        help="엑셀 시트명 또는 인덱스(기본 0)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sheet_name: Union[int, str] = int(args.esg_sheet_name) if str(args.esg_sheet_name).isdigit() else args.esg_sheet_name

    config = PipelineConfig(
        esg_path=args.esg_path,
        etf_path=args.etf_path,
        output_dir=args.output_dir,
        missing_grade_policy=args.missing_grade_policy,
        etf_id_col=args.etf_id_col,
        esg_sheet_name=sheet_name,
    )

    try:
        run_pipeline(config)
    except (FileNotFoundError, DataValidationError, ValueError, RuntimeError) as e:
        print(f"[ERROR] {e}")
    except Exception as e:
        print(f"[UNEXPECTED ERROR] {e}")
        raise


if __name__ == "__main__":
    main()
