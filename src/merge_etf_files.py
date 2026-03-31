from pathlib import Path
import pandas as pd

DATA_DIR = Path("data")

ETF_FILES = [
    "KODEX_200ESG.csv",
    "TIGER_GREEN_NEWDEAL.csv",
    "SOL_CLIMATE.csv",
    "SOLAR_THEME.csv",
    "kodex_semiconductor.csv",
]

def load_csv_with_fallback(path: Path) -> pd.DataFrame:
    encodings = ["utf-8-sig", "cp949", "euc-kr", "utf-8"]
    last_error = None
    for enc in encodings:
        try:
            return pd.read_csv(path, dtype=str, encoding=enc)
        except Exception as e:
            last_error = e
    raise ValueError(f"파일 읽기 실패: {path}") from last_error

def main():
    merged = []

    for file_name in ETF_FILES:
        path = DATA_DIR / file_name
        if not path.exists():
            print(f"[경고] 파일 없음: {path}")
            continue

        df = load_csv_with_fallback(path)

        etf_name = path.stem
        df["ETF명"] = etf_name

        merged.append(df)
        print(f"[로드 완료] {file_name}: {len(df)}행")

    if not merged:
        print("[에러] 병합할 ETF 파일이 없습니다.")
        return

    final_df = pd.concat(merged, ignore_index=True)

    output_path = DATA_DIR / "etf_holdings.csv"
    final_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"\n[저장 완료] {output_path}")
    print(f"총 행 수: {len(final_df)}")
    print("\n[상위 5개 행]")
    print(final_df.head().to_string(index=False))

if __name__ == "__main__":
    main()