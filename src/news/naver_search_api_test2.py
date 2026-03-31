import requests
from collections import defaultdict

CLIENT_ID = ""
CLIENT_SECRET = ""

URL = "https://openapi.naver.com/v1/search/news.json"

HEADERS = {
    "X-Naver-Client-Id": CLIENT_ID,
    "X-Naver-Client-Secret": CLIENT_SECRET
}

ESG_KEYWORDS = {
    "E": ["탄소", "배출", "오염", "환경", "재생에너지", "기후"],
    "S": ["산재", "노동", "안전", "파업", "협력사", "인권"],
    "G": ["횡령", "과징금", "내부거래", "지배구조", "이사회", "불공정"]
}

def search_news(query: str, display: int = 5):
    params = {
        "query": query,
        "display": display,
        "sort": "date"
    }
    response = requests.get(URL, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json().get("items", [])

def build_esg_queries(company_name: str):
    queries = []
    for category, keywords in ESG_KEYWORDS.items():
        for keyword in keywords:
            queries.append((category, f"{company_name} {keyword}", keyword))
    return queries

def is_relevant(item, company_name: str, keyword: str):
    text = f"{item.get('title', '')} {item.get('description', '')}"
    return company_name in text and keyword in text

def deduplicate_news(items):
    seen = set()
    result = []
    for item in items:
        key = item.get("originallink") or item.get("link") or item.get("title")
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result

def collect_company_esg_news(company_name: str):
    categorized_news = defaultdict(list)

    queries = build_esg_queries(company_name)

    for category, query, keyword in queries:
        try:
            items = search_news(query, display=5)
            filtered = [item for item in items if is_relevant(item, company_name, keyword)]
            categorized_news[category].extend(filtered)
        except Exception as e:
            print(f"[ERROR] {query}: {e}")

    for category in categorized_news:
        categorized_news[category] = deduplicate_news(categorized_news[category])

    return categorized_news

def print_news_result(company_name: str, news_data):
    print(f"\n=== {company_name} ESG 뉴스 결과 ===")
    for category in ["E", "S", "G"]:
        print(f"\n[{category}]")
        if not news_data[category]:
            print("관련 뉴스 없음")
            continue
        for idx, item in enumerate(news_data[category][:5], 1):
            print(f"{idx}. {item['title']}")
            print(f"   날짜: {item['pubDate']}")
            print(f"   링크: {item['link']}")

if __name__ == "__main__":
    company = "삼성전자"
    news_data = collect_company_esg_news(company)
    print_news_result(company, news_data)