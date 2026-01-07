#!/usr/bin/env python3
"""
공통 설정 파일

GitHub/GitLab 커밋 캘린더 생성기의 모든 설정을 관리합니다.
"""

from datetime import datetime
from pathlib import Path

# ============================================================
# 인원별 계정 매핑
# ============================================================
# 각 인원의 표시 이름과 GitHub/GitLab 계정을 매핑합니다.
# GitHub 또는 GitLab 계정이 없으면 None으로 설정하세요.

USERS = [
    {
        "name": "세용",           # 캘린더에 표시될 이름
        "github": "Nieaunder7",         # GitHub 사용자명 (없으면 None)
        "gitlab": "sieging",            # GitLab 사용자명 (없으면 None)
    },
    {
        "name": "보미",
        "github": "bomi94437",
        "gitlab": None,
    },
    {
        "name": "은비",
        "github": "eunbi0322",
        "gitlab": "eunbi0322",
    }, 
    {
        "name": "진환",
        "github": "realight0316",
        "gitlab": "0316kjh",
    },
    {
        "name": "재일",
        "github": "ShinJaeIL01",
        "gitlab": None,
    },
    {
        "name": "재현",
        "github": "jhkim6069",
        "gitlab": None,
    }, 
    {
        "name": "영수",
        "github": "youngsu999",
        "gitlab": "youngsu999",
    }, 
    {
        "name": "지희",
        "github": "SUNJIHEE",
        "gitlab": "jiheesun",
    }, 
    {
        "name": "준무",
        "github": "JunmooByun",
        "gitlab": "junmoo.byun",
    }
    # 추가 인원 예시:
    # {
    #     "name": "홍길동",
    #     "github": "hong-gildong",
    #     "gitlab": None,  # GitLab 계정 없음
    # },
]

# ============================================================
# GitHub 설정
# ============================================================

GITHUB_TOKEN = ""  # 여기에 GitHub 토큰 입력
GITHUB_ORG_NAME = "nextlab-ai"

# ============================================================
# GitLab 설정
# ============================================================

GITLAB_TOKEN = ""  # 여기에 GitLab 토큰 입력
GITLAB_URL = "https://gitlab.com"  # self-hosted인 경우 변경
GITLAB_GROUP_NAME = "nextlab-cowork"

# ============================================================
# 조회 기간
# ============================================================

START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 12, 31, 23, 59, 59)

# ============================================================
# 프로젝트 매핑 (리포지토리명 → 간략화된 이름)
# ============================================================

PROJECT_MAPPING = {
    "topaz-stb-test-system": "topaz",
    "athena-runner-ott": "ott",
    "beyond_xray_services": "xray",
    "netMeterUplusHome": "netmeter",
    "NetAnalyzer": "netmeter",
    "NetAnalyzerLGHV": "netmeter",
    "web-speed-service-dione": "ott",
    "EvoService": "EvoRev2",
    # 나머지는 그대로 사용
}

# ============================================================
# 프로젝트별 색상
# ============================================================

PROJECT_COLORS = {
    "topaz": "#ef4444",     # 빨강
    "EvoRev2": "#3b82f6",   # 파랑
    "vos": "#22c55e",       # 초록
    "ott": "#f59e0b",       # 주황
    "netmeter": "#8b5cf6",  # 보라
    "xray": "#06b6d4",      # 시안
}
DEFAULT_COLOR = "#6b7280"  # 회색

# ============================================================
# 출력 경로
# ============================================================

OUTPUT_DIR = Path(__file__).parent
NEATOCAL_PATH = "./neatocal"
