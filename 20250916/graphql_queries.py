# 네이버 지도 GraphQL 쿼리 모음

# GraphQL API URL
GRAPHQL_URL = "https://pcmap-api.place.naver.com/graphql"

# GraphQL 요청 헤더
GRAPHQL_HEADERS = {
    "accept": "*/*",
    "accept-language": "ko",
    "content-type": "application/json",
    "priority": "u=1, i",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "x-ncaptcha-violation": "false",
    "x-wtm-graphql": "eyJhcmciOiLsnYzsi53soJAiLCJ0eXBlIjoicmVzdGF1cmFudCIsInNvdXJjZSI6InBsYWNlIn0",
}

# 음식점 목록 조회 쿼리
GET_RESTAURANTS_QUERY = """query getRestaurants($restaurantListInput: RestaurantListInput, $restaurantListFilterInput: RestaurantListFilterInput, $isNmap: Boolean = false) {
  restaurants: restaurantList(input: $restaurantListInput) {
    items {
      ...CommonBusinessItems
      ...RestaurantBusinessItems
      __typename
    }
    total
    __typename
  }
  filters: restaurantListFilter(input: $restaurantListFilterInput) {
    __typename
  }
}
"""

# Fragment 정의들
FRAGMENTS = {
    "CommonBusinessItems": """fragment CommonBusinessItems on BusinessSummary {
  id
  name
  businessCategory
  category
  x
  y
  phone
  blogCafeReviewCount
  totalReviewCount
  detailCid {
    c0
    c1
    c2
    c3
    __typename
  }
  markerId @include(if: $isNmap)
  __typename
}""",

    "RestaurantBusinessItems": """fragment RestaurantBusinessItems on RestaurantListSummary {
  fullAddress
  categoryCodeList
  visitorReviewCount
  visitorReviewScore
  __typename
}"""
}

def build_complete_query():
    """완전한 GraphQL 쿼리를 구성합니다."""
    # 모든 fragment를 하나로 합치기
    all_fragments = "\n\n".join(FRAGMENTS.values())
    
    # 메인 쿼리와 fragment 합치기
    complete_query = f"{GET_RESTAURANTS_QUERY}\n\n{all_fragments}"
    
    return complete_query

def create_graphql_body(variables):
    """GraphQL 요청 body를 생성합니다."""
    return {
        "operationName": "getRestaurants",
        "variables": variables,
        "query": build_complete_query()
    }
