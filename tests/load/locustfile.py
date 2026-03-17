"""
Locust 부하 테스트 (F9-25)
실행: locust -f tests/load/locustfile.py --host=http://localhost:5001
     locust -f tests/load/locustfile.py --host=http://localhost:5001 --headless -u 50 -r 5 --run-time 60s
"""
import random
from locust import HttpUser, task, between, events

# 테스트용 YouTube URL 샘플
SAMPLE_URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=9bZkp7q19f0",
    "https://www.youtube.com/watch?v=kJQP7kiw5Fk",
]

SAMPLE_STYLES = ['blog_seo', 'summary', 'tutorial', 'qna', 'sns_post']
SAMPLE_MODELS = ['gemini/gemini-2.5-flash-lite-preview-09-2025']


class InsightEngineUser(HttpUser):
    """일반 사용자 시나리오 (콘텐츠 생성 + 조회)"""
    wait_time = between(2, 8)  # 요청 간격 2~8초 (실제 사용 패턴 모사)
    host = "http://localhost:5001"

    def on_start(self):
        """사용자 세션 시작 — 로그인 시뮬레이션"""
        # 실제 환경에서는 인증 토큰 발급
        self.headers = {
            'Content-Type': 'application/json',
            'X-Test-User': f"load-test-user-{random.randint(1, 1000)}",
        }

    @task(5)
    def health_check(self):
        """헬스체크 엔드포인트 (가장 빈번)"""
        with self.client.get("/health", catch_response=True, name="GET /health") as resp:
            if resp.status_code != 200:
                resp.failure(f"헬스체크 실패: {resp.status_code}")

    @task(3)
    def get_providers(self):
        """지원 프로바이더 목록 조회"""
        self.client.get("/api/providers", headers=self.headers, name="GET /api/providers")

    @task(1)
    def generate_content(self):
        """콘텐츠 생성 (가장 무거운 작업)"""
        payload = {
            "url": random.choice(SAMPLE_URLS),
            "style_id": random.choice(SAMPLE_STYLES),
            "model": random.choice(SAMPLE_MODELS),
            "length": random.choice(["short", "medium"]),
            "language": "ko",
        }

        with self.client.post(
            "/generate",
            json=payload,
            headers=self.headers,
            timeout=120,
            catch_response=True,
            name="POST /generate",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if not data.get('content') and not data.get('error'):
                    resp.failure("응답에 content 없음")
            elif resp.status_code in (429, 503):
                resp.success()  # Rate limit/과부하는 정상 처리
            else:
                resp.failure(f"생성 실패: {resp.status_code}")


class AdminUser(HttpUser):
    """관리자 사용자 시나리오 (대시보드 + 통계)"""
    wait_time = between(5, 15)
    weight = 1  # 관리자는 일반 사용자보다 적음

    @task
    def admin_dashboard(self):
        """관리자 대시보드 조회"""
        self.client.get(
            "/api/admin/dashboard",
            headers={'Content-Type': 'application/json'},
            name="GET /api/admin/dashboard",
        )

    @task
    def check_metrics(self):
        """Prometheus 메트릭 조회"""
        self.client.get("/metrics", name="GET /metrics")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("=" * 50)
    print("Insight Engine 부하 테스트 시작")
    print(f"대상 호스트: {environment.host}")
    print("=" * 50)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats
    print("\n" + "=" * 50)
    print("부하 테스트 완료")
    print(f"총 요청 수: {stats.total.num_requests}")
    print(f"실패 수: {stats.total.num_failures}")
    print(f"평균 응답시간: {stats.total.avg_response_time:.0f}ms")
    print(f"최대 응답시간: {stats.total.max_response_time:.0f}ms")
    print("=" * 50)
