# 네이버 지도 GraphQL 쿼리 모음
import asyncio

try:
    from playwright.async_api import async_playwright
    from fake_useragent import UserAgent
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    print("Warning: Playwright or fake-useragent not installed. Using default headers.")
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    UserAgent = None

# GraphQL API URL
GRAPHQL_URL = "https://pcmap-api.place.naver.com/graphql"

# UserAgent 인스턴스 생성
ua = UserAgent() if PLAYWRIGHT_AVAILABLE else None

# 기본 헤더 (fallback용)
DEFAULT_HEADERS = {
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

# 동적으로 생성된 헤더와 쿠키를 저장할 변수
_current_headers = None
_current_cookies = None

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

async def get_real_browser_headers():
    """Playwright를 사용하여 실제 브라우저 헤더와 쿠키를 가져옵니다."""
    if not PLAYWRIGHT_AVAILABLE:
        print("Playwright not available, using default headers")
        return DEFAULT_HEADERS, {}
    
    print("Initializing headers/cookies...")
    
    while True:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )
                
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=ua.random
                )
                
                page = await context.new_page()
                await page.goto('https://map.naver.com/', timeout=5000)
                
                headers = await page.evaluate("""
                    () => ({
                        'accept': '*/*',
                        'accept-language': 'ko-KR,ko;q=0.9,en;q=0.8',
                        'content-type': 'application/json',
                        'user-agent': navigator.userAgent,
                        'referer': 'https://map.naver.com/',
                        'origin': 'https://map.naver.com'
                    })
                """)
                
                cookies = {cookie['name']: cookie['value'] for cookie in await context.cookies()}
                await browser.close()
                
                return headers, cookies
                
        except Exception as e:
            print(f"Browser header generation failed: {e} - Retrying...")
            continue

def get_headers_and_cookies():
    """현재 헤더와 쿠키를 반환합니다. 없으면 새로 생성합니다."""
    global _current_headers, _current_cookies
    
    if _current_headers is None or _current_cookies is None:
        if PLAYWRIGHT_AVAILABLE:
            print("Generating new headers and cookies...")
            _current_headers, _current_cookies = asyncio.run(get_real_browser_headers())
        else:
            print("Using default headers (Playwright not available)")
            _current_headers, _current_cookies = DEFAULT_HEADERS, {}
    
    return _current_headers, _current_cookies

def refresh_headers_and_cookies():
    """헤더와 쿠키를 새로 생성합니다."""
    global _current_headers, _current_cookies
    if PLAYWRIGHT_AVAILABLE:
        print("Refreshing headers and cookies...")
        _current_headers, _current_cookies = asyncio.run(get_real_browser_headers())
    else:
        print("Using default headers (Playwright not available)")
        _current_headers, _current_cookies = DEFAULT_HEADERS, {}
    return _current_headers, _current_cookies

def get_graphql_headers():
    """GraphQL 요청에 사용할 헤더를 반환합니다."""
    headers, cookies = get_headers_and_cookies()
    
    # 기본 헤더에 동적 헤더 정보 추가
    graphql_headers = DEFAULT_HEADERS.copy()
    graphql_headers.update(headers)
    
    return graphql_headers, cookies

def create_graphql_body(variables):
    """GraphQL 요청 body를 생성합니다."""
    return {
        "operationName": "getRestaurants",
        "variables": variables,
        "query": build_complete_query()
    }
