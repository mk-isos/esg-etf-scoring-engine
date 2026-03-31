import requests

client_id = "JbwrQz7M9eXI6DPpS5sZ"
client_secret = "sW_snfS1LA"

query = "삼성전자 ESG"

url = "https://openapi.naver.com/v1/search/news.json"

headers = {
    "X-Naver-Client-Id": client_id,
    "X-Naver-Client-Secret": client_secret
}

params = {
    "query": query,
    "display": 5,
    "sort": "date"
}

response = requests.get(url, headers=headers, params=params)

print(response.json())