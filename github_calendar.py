#!/usr/bin/env python3
"""
GitHub + GitLab 커밋 데이터를 수집하여 NeatoCal 히트맵 캘린더 HTML을 생성하는 통합 스크립트

워크플로우:
1. GitHub/GitLab API로 커밋 수집
2. 일별/프로젝트별 집계
3. 사용자별 NeatoCal HTML 생성
4. 탭 인터페이스로 통합 HTML 생성
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from github import Github
from github import Auth

# GitLab import (설치 필요: pip install python-gitlab)
try:
    import gitlab
    GITLAB_AVAILABLE = True
except ImportError:
    GITLAB_AVAILABLE = False
    print("경고: python-gitlab이 설치되지 않았습니다. GitLab 수집을 건너뜁니다.")
    print("      설치: pip install python-gitlab\n")

# 설정 import
from config import (
    USERS,
    GITHUB_TOKEN, GITHUB_ORG_NAME,
    GITLAB_TOKEN, GITLAB_URL, GITLAB_GROUP_NAME,
    START_DATE, END_DATE,
    PROJECT_MAPPING, PROJECT_COLORS, DEFAULT_COLOR,
    OUTPUT_DIR, NEATOCAL_PATH
)


# ============================================================
# 1단계: GitHub 커밋 수집 (병렬 처리)
# ============================================================

def collect_github_commits(token, org_name, username, start_date, end_date):
    """GitHub Organization에서 커밋 수집 (병렬 처리)"""
    auth = Auth.Token(token)
    g = Github(auth=auth)
    org = g.get_organization(org_name)

    daily_commits = defaultdict(list)

    print(f"[GitHub] 커밋 수집 (병렬 처리)")
    print(f"      Organization: {org_name}")
    print(f"      사용자: {username}")
    print(f"      기간: {start_date.date()} ~ {end_date.date()}")

    repos = list(org.get_repos(type='all'))
    total_repos = len(repos)
    print(f"      리포지토리: {total_repos}개")
    print(f"      조회 중...", end=" ", flush=True)

    def fetch_repo_commits(repo):
        """단일 리포지토리의 커밋 조회"""
        repo_commits = []
        try:
            commits = repo.get_commits(
                author=username,
                since=start_date,
                until=end_date
            )
            for commit in commits:
                commit_date = commit.commit.author.date.date()
                repo_commits.append({
                    'repo': repo.name,
                    'date': commit_date,
                    'source': 'github',
                })
        except Exception:
            pass
        return repo.name, repo_commits

    # 병렬 처리 (최대 10개 동시 요청)
    total_commits = 0
    repos_with_commits = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_repo_commits, repo): repo for repo in repos}

        for future in as_completed(futures):
            repo_name, commits = future.result()
            if commits:
                repos_with_commits.append((repo_name, len(commits)))
                for commit in commits:
                    daily_commits[commit['date']].append(commit)
                    total_commits += 1

    print(f"완료!")
    print(f"      총 {total_commits}개 커밋 수집")

    # 커밋이 있는 리포지토리 출력
    if repos_with_commits:
        print(f"      커밋 있는 리포지토리:")
        for repo_name, count in sorted(repos_with_commits, key=lambda x: -x[1]):
            print(f"        - {repo_name}: {count}개")

    return daily_commits


# ============================================================
# 1단계: GitLab 커밋 수집 (Events API 사용 - 빠른 버전)
# ============================================================

def collect_gitlab_commits(token, gitlab_url, group_name, username, start_date, end_date):
    """GitLab Group에서 커밋 수집 (Events API 사용)"""
    if not GITLAB_AVAILABLE:
        return defaultdict(list)

    gl = gitlab.Gitlab(gitlab_url, private_token=token)

    daily_commits = defaultdict(list)

    print(f"[GitLab] 커밋 수집 (Events API)")
    print(f"      URL: {gitlab_url}")
    print(f"      Group: {group_name}")
    print(f"      사용자: {username}")
    print(f"      기간: {start_date.date()} ~ {end_date.date()}")

    try:
        # 그룹 정보 조회
        group = gl.groups.get(group_name)
        print(f"      그룹: {group.name}")

        # 그룹의 모든 프로젝트 ID 수집 (필터링용)
        projects = group.projects.list(all=True)
        project_ids = {p.id for p in projects}
        project_names = {p.id: p.name for p in projects}
        print(f"      프로젝트: {len(projects)}개")

        # 사용자 찾기
        users = gl.users.list(username=username)
        if not users:
            # username으로 검색 안되면 search로 시도
            users = gl.users.list(search=username)

        if not users:
            print(f"      경고: 사용자 '{username}'를 찾을 수 없습니다.")
            return daily_commits

        user = users[0]
        print(f"      사용자 ID: {user.id} ({user.name})")

        # 사용자의 push 이벤트 조회
        print(f"      이벤트 조회 중...")
        events = user.events.list(
            action='pushed',
            after=start_date.strftime('%Y-%m-%d'),
            before=(end_date + timedelta(days=1)).strftime('%Y-%m-%d'),
            all=True
        )

        commit_count = 0
        for event in events:
            # 그룹 내 프로젝트인지 확인
            if event.project_id not in project_ids:
                continue

            # 날짜 파싱
            created_at = event.created_at
            if isinstance(created_at, str):
                event_date = datetime.fromisoformat(
                    created_at.replace('Z', '+00:00')
                ).date()
            else:
                event_date = created_at.date()

            # 기간 필터링
            if not (start_date.date() <= event_date <= end_date.date()):
                continue

            # push 이벤트의 커밋 수 (push_data에 commit_count가 있음)
            push_data = getattr(event, 'push_data', {}) or {}
            num_commits = push_data.get('commit_count', 1)

            project_name = project_names.get(event.project_id, f"project_{event.project_id}")

            # 커밋 수만큼 추가
            for _ in range(num_commits):
                daily_commits[event_date].append({
                    'repo': project_name,
                    'date': event_date,
                    'source': 'gitlab',
                })
                commit_count += 1

        print(f"      총 {commit_count}개 커밋 수집 완료")

    except Exception as e:
        print(f"GitLab 오류: {e}")
        # 폴백: 기존 방식으로 시도
        print("      폴백: 프로젝트별 조회 시도...")
        return collect_gitlab_commits_legacy(token, gitlab_url, group_name, username, start_date, end_date)

    return daily_commits


def collect_gitlab_commits_legacy(token, gitlab_url, group_name, username, start_date, end_date):
    """GitLab Group에서 커밋 수집 (레거시 - 프로젝트별 조회)"""
    gl = gitlab.Gitlab(gitlab_url, private_token=token)
    daily_commits = defaultdict(list)

    try:
        group = gl.groups.get(group_name)
        projects = group.projects.list(all=True)
        total_projects = len(projects)

        for idx, project_info in enumerate(projects, 1):
            print(f"      [{idx}/{total_projects}] {project_info.name}...", end=" ", flush=True)

            try:
                project = gl.projects.get(project_info.id)
                commits = project.commits.list(
                    since=start_date.isoformat(),
                    until=end_date.isoformat(),
                    per_page=100
                )

                commit_count = 0
                for commit in commits:
                    author_match = (
                        commit.author_name == username or
                        username.lower() in commit.author_name.lower() or
                        username.lower() in commit.author_email.lower()
                    )

                    if author_match:
                        created_at = commit.created_at
                        if isinstance(created_at, str):
                            commit_date = datetime.fromisoformat(
                                created_at.replace('Z', '+00:00')
                            ).date()
                        else:
                            commit_date = created_at.date()

                        daily_commits[commit_date].append({
                            'repo': project_info.name,
                            'date': commit_date,
                            'source': 'gitlab',
                        })
                        commit_count += 1

                if commit_count > 0:
                    print(f"{commit_count}개")
                else:
                    print("없음")

            except Exception as e:
                print(f"오류")
                continue

    except Exception as e:
        print(f"GitLab 연결 오류: {e}")

    return daily_commits


# ============================================================
# 2단계: 히트맵 데이터 변환
# ============================================================

def normalize_project_name(repo_name):
    """리포지토리명을 간략화된 프로젝트명으로 변환"""
    return PROJECT_MAPPING.get(repo_name, repo_name)


def calculate_level(count, max_count):
    """커밋 수에 따른 활동 레벨 계산 (0~4)"""
    if count == 0:
        return 0
    ratio = count / max_count
    if ratio <= 0.25:
        return 1
    elif ratio <= 0.5:
        return 2
    elif ratio <= 0.75:
        return 3
    else:
        return 4


def convert_to_heatmap(daily_commits):
    """일별 커밋 데이터를 히트맵 형식으로 변환"""
    if not daily_commits:
        return []

    # 일별로 주요 프로젝트와 커밋 수 집계
    date_summary = {}

    for date, commits in daily_commits.items():
        # 프로젝트별 커밋 수 집계
        project_counts = defaultdict(int)
        for commit in commits:
            project = normalize_project_name(commit['repo'])
            project_counts[project] += 1

        # 가장 커밋이 많은 프로젝트 선택
        main_project = max(project_counts, key=project_counts.get)
        total_count = sum(project_counts.values())

        date_summary[date] = {
            'project': main_project,
            'count': total_count,
        }

    # 최대 커밋 수 계산 (level 계산용)
    max_count = max(d['count'] for d in date_summary.values()) if date_summary else 1

    # 히트맵 데이터 생성
    heatmap_data = []
    for date, info in sorted(date_summary.items()):
        heatmap_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': info['count'],
            'project': info['project'],
            'level': calculate_level(info['count'], max_count),
        })

    return heatmap_data


# ============================================================
# 3단계: NeatoCal HTML 생성 (개별 사용자)
# ============================================================

def generate_neatocal_data(heatmap_data, year):
    """히트맵 데이터를 NeatoCal JSON 형식으로 변환"""
    neatocal_data = {
        "param": {
            "year": year,
            "layout": "aligned-weekdays",
            "cell_height": "1.5em",
            "start_day": 0,
            "highlight_color": "#fef9c3",
            "color_cell": []
        }
    }

    for entry in heatmap_data:
        date = entry["date"]
        project = entry["project"]

        # 날짜별 텍스트
        neatocal_data[date] = project

        # 색상 셀
        color = PROJECT_COLORS.get(project, DEFAULT_COLOR)
        neatocal_data["param"]["color_cell"].append({
            "date": date,
            "color": color
        })

    return neatocal_data


def generate_legend_html():
    """범례 HTML 생성"""
    legend_html = ""
    for project, color in PROJECT_COLORS.items():
        legend_html += f'''      <div class="legend-row">
        <div class="legend-item" style="background-color: {color};"></div>
        <span class="legend-label">{project}</span>
      </div>
'''
    return legend_html


def load_neatocal_assets():
    """NeatoCal CSS/JS 파일을 읽어서 인라인으로 사용"""
    neatocal_dir = OUTPUT_DIR / "neatocal"

    # CSS 파일 읽기
    css_content = ""
    css_file = neatocal_dir / "css" / "neatocal.css"
    if css_file.exists():
        css_content = css_file.read_text(encoding='utf-8')

    # JS 파일 읽기
    js_content = ""
    js_file = neatocal_dir / "neatocal.js"
    if js_file.exists():
        js_content = js_file.read_text(encoding='utf-8')

    return css_content, js_content


# ============================================================
# 4단계: 탭 인터페이스 HTML 생성 (통합, Standalone)
# ============================================================

def generate_tabbed_html(user_calendars, year):
    """탭 인터페이스가 있는 통합 HTML 생성 (Standalone)"""

    # NeatoCal CSS/JS 로드
    neatocal_css, neatocal_js = load_neatocal_assets()

    # 각 캘린더 데이터를 JavaScript 객체로 변환
    calendar_data_js = {}
    for username, neatocal_data in user_calendars.items():
        calendar_data_js[username] = neatocal_data

    # 범례 HTML
    legend_html = generate_legend_html()

    # 탭 버튼 HTML
    usernames = list(user_calendars.keys())
    tab_buttons = ""
    for i, username in enumerate(usernames):
        active = "active" if i == 0 else ""
        tab_buttons += f'      <button class="tab-btn {active}" data-name="{username}">{username}</button>\n'

    # JavaScript 데이터
    all_data_json = json.dumps(calendar_data_js, ensure_ascii=False)
    first_user = usernames[0] if usernames else ""

    html_content = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>Commit Heatmap Calendar {year} - All Members</title>

<!-- Google Fonts -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@300;400&display=swap" rel="stylesheet">

<!-- NeatoCal CSS (Inline) -->
<style>
{neatocal_css}
</style>

<style>
  body {{
    font-family: 'Oswald', sans-serif;
    margin: 0;
    padding: 20px;
  }}

  /* 탭 스타일 */
  .tab-container {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    margin-bottom: 20px;
    padding: 10px;
    background: #f5f5f5;
    border-radius: 8px;
  }}

  .tab-btn {{
    padding: 8px 16px;
    border: none;
    background: #fff;
    border-radius: 6px;
    cursor: pointer;
    font-family: 'Oswald', sans-serif;
    font-size: 14px;
    transition: all 0.2s;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }}

  .tab-btn:hover {{
    background: #e0e0e0;
  }}

  .tab-btn.active {{
    background: #3b82f6;
    color: white;
    box-shadow: 0 2px 6px rgba(59,130,246,0.4);
  }}

  /* 캘린더 컨테이너 */
  .calendar-container {{
    max-width: 1200px;
    margin: 0 auto;
  }}

  #ui_table td div {{
    display: inline;
    margin-left: 4px;
    font-size: 0.8em;
  }}

  .legend {{
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 12px 24px;
    margin-top: 20px;
    font-size: 11px;
    padding: 10px;
  }}

  .legend-row {{
    display: flex;
    align-items: center;
    gap: 4px;
  }}

  .legend-label {{
    color: #666;
  }}

  .legend-item {{
    width: 12px;
    height: 12px;
    border-radius: 2px;
  }}

  /* 현재 선택된 이름 표시 */
  .current-name {{
    text-align: center;
    font-size: 1.5em;
    margin-bottom: 10px;
    color: #333;
  }}
</style>

<!-- NeatoCal JS (Inline) -->
<script>
{neatocal_js}
</script>

</head>
<body>

  <!-- 탭 버튼 -->
  <div class="tab-container">
{tab_buttons}  </div>

  <div class="calendar-container">
    <!-- 현재 선택된 이름 -->
    <div class="current-name" id="currentName">{first_user}</div>

    <!-- 연도 표시 -->
    <div id="ui_year" style='width:100%;'>
      <span style='display:inline-block; width:100%; justify-content:center; text-align:center; margin: 0 0 .5em 0;'>{year}</span>
    </div>

    <!-- 캘린더 테이블 -->
    <table id='ui_table'>
      <thead id='ui_thead'>
        <tr id='ui_tr_month_name'>
          <th>Jan</th>
          <th>Feb</th>
          <th>Mar</th>
          <th>Apr</th>
          <th>May</th>
          <th>Jun</th>
          <th>Jul</th>
          <th>Aug</th>
          <th>Sep</th>
          <th>Oct</th>
          <th>Nov</th>
          <th>Dec</th>
        </tr>
      </thead>
      <tbody id='ui_tbody'>
      </tbody>
    </table>

    <!-- 범례 -->
    <div class="legend">
{legend_html}    </div>
  </div>

</body>

<script>
  // 모든 캘린더 데이터
  var ALL_CALENDAR_DATA = {all_data_json};

  // 현재 선택된 캘린더
  var currentCalendar = '{first_user}';

  // 캘린더 전환 함수
  function switchCalendar(name) {{
    currentCalendar = name;

    // 탭 버튼 활성화 상태 변경
    document.querySelectorAll('.tab-btn').forEach(function(btn) {{
      btn.classList.remove('active');
      if (btn.dataset.name === name) {{
        btn.classList.add('active');
      }}
    }});

    // 현재 이름 표시 업데이트
    document.getElementById('currentName').textContent = name;

    // 캘린더 다시 그리기
    var data = ALL_CALENDAR_DATA[name];
    if (data) {{
      // tbody 초기화
      document.getElementById('ui_tbody').innerHTML = '';

      // NEATOCAL_PARAM 설정
      NEATOCAL_PARAM.data = data;
      if (data.param) {{
        for (var key in data.param) {{
          NEATOCAL_PARAM[key] = data.param[key];
        }}
      }}

      // 캘린더 다시 렌더링
      neatocal_render();
    }}
  }}

  // 탭 버튼 이벤트 바인딩
  document.querySelectorAll('.tab-btn').forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      switchCalendar(this.dataset.name);
    }});
  }});

  // 초기 캘린더 로드
  (function() {{
    var initialData = ALL_CALENDAR_DATA[currentCalendar];
    if (initialData) {{
      NEATOCAL_PARAM.data = initialData;
      if (initialData.param) {{
        for (var key in initialData.param) {{
          NEATOCAL_PARAM[key] = initialData.param[key];
        }}
      }}
      neatocal_render();
    }}
  }})();
</script>
</html>
'''
    return html_content


def generate_single_html(neatocal_data, year):
    """단일 사용자 HTML 생성 (Standalone)"""
    # NeatoCal CSS/JS 로드
    neatocal_css, neatocal_js = load_neatocal_assets()

    data_json = json.dumps(neatocal_data, ensure_ascii=False)
    legend_html = generate_legend_html()

    html_content = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>Commit Heatmap Calendar {year}</title>

<!-- Google Fonts -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@300;400&display=swap" rel="stylesheet">

<!-- NeatoCal CSS (Inline) -->
<style>
{neatocal_css}
</style>

<style>
  body {{
    font-family: 'Oswald', sans-serif;
  }}
  #ui_table td div {{
    display: inline;
    margin-left: 4px;
    font-size: 0.8em;
  }}
  .legend {{
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 12px 24px;
    margin-top: 20px;
    font-size: 11px;
    padding: 10px;
  }}
  .legend-row {{
    display: flex;
    align-items: center;
    gap: 4px;
  }}
  .legend-label {{
    color: #666;
  }}
  .legend-item {{
    width: 12px;
    height: 12px;
    border-radius: 2px;
  }}
</style>

<!-- NeatoCal JS (Inline) -->
<script>
{neatocal_js}
</script>

</head>
<body>

  <div id="ui_year" style='width:100%;'>
    <span style='display:inline-block; width:100%; justify-content:center; text-align:center; margin: 0 0 .5em 0;'>{year}</span>
  </div>

  <table id='ui_table'>
    <thead id='ui_thead'>
      <tr id='ui_tr_month_name'>
        <th>Jan</th>
        <th>Feb</th>
        <th>Mar</th>
        <th>Apr</th>
        <th>May</th>
        <th>Jun</th>
        <th>Jul</th>
        <th>Aug</th>
        <th>Sep</th>
        <th>Oct</th>
        <th>Nov</th>
        <th>Dec</th>
      </tr>
    </thead>
    <tbody id='ui_tbody'>
    </tbody>
  </table>

  <div class="legend">
{legend_html}  </div>

</body>

<script>
  var CALENDAR_DATA = {data_json};

  NEATOCAL_PARAM.data = CALENDAR_DATA;
  if (CALENDAR_DATA.param) {{
    for (var key in CALENDAR_DATA.param) {{
      NEATOCAL_PARAM[key] = CALENDAR_DATA.param[key];
    }}
  }}

  neatocal_render();
</script>
</html>
'''
    return html_content


# ============================================================
# 메인 실행
# ============================================================

def main():
    print("=" * 60)
    print("GitHub + GitLab Commit Calendar Generator")
    print("=" * 60 + "\n")

    year = START_DATE.year

    # 사용자별 캘린더 데이터 저장
    user_calendars = {}

    for user in USERS:
        display_name = user["name"]
        github_username = user.get("github")
        gitlab_username = user.get("gitlab")

        print(f"\n{'='*60}")
        print(f"사용자: {display_name}")
        if github_username:
            print(f"  GitHub: {github_username}")
        if gitlab_username:
            print(f"  GitLab: {gitlab_username}")
        print(f"{'='*60}\n")

        all_commits = defaultdict(list)

        # GitHub 커밋 수집
        if github_username:
            github_commits = collect_github_commits(
                token=GITHUB_TOKEN,
                org_name=GITHUB_ORG_NAME,
                username=github_username,
                start_date=START_DATE,
                end_date=END_DATE
            )
            # 병합
            for date, commits in github_commits.items():
                all_commits[date].extend(commits)

        # GitLab 커밋 수집
        if gitlab_username and GITLAB_AVAILABLE:
            print()  # 줄바꿈
            gitlab_commits = collect_gitlab_commits(
                token=GITLAB_TOKEN,
                gitlab_url=GITLAB_URL,
                group_name=GITLAB_GROUP_NAME,
                username=gitlab_username,
                start_date=START_DATE,
                end_date=END_DATE
            )
            # 병합
            for date, commits in gitlab_commits.items():
                all_commits[date].extend(commits)

        if not all_commits:
            print(f"\n{display_name}: 커밋 데이터가 없습니다.")
            continue

        # 히트맵 변환
        print(f"\n[변환] 히트맵 데이터 생성...")
        heatmap_data = convert_to_heatmap(all_commits)
        print(f"      총 {len(heatmap_data)}일 데이터")

        # 프로젝트별 통계
        project_stats = defaultdict(lambda: {'days': 0, 'commits': 0})
        for item in heatmap_data:
            project_stats[item['project']]['days'] += 1
            project_stats[item['project']]['commits'] += item['count']

        print(f"      프로젝트별 통계:")
        for project, stats in sorted(project_stats.items(), key=lambda x: -x[1]['commits']):
            print(f"        - {project}: {stats['commits']}커밋 / {stats['days']}일")

        # NeatoCal 데이터 생성
        neatocal_data = generate_neatocal_data(heatmap_data, year)
        user_calendars[display_name] = neatocal_data

        # 개별 HTML 저장
        single_html = generate_single_html(neatocal_data, year)
        html_file = OUTPUT_DIR / f"commit_calendar - {display_name}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(single_html)
        print(f"\n[저장] {html_file}")

        # 개별 JSON 저장
        json_file = OUTPUT_DIR / f"commit_calendar_data - {display_name}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(neatocal_data, f, ensure_ascii=False, indent=2)
        print(f"[저장] {json_file}")

    # 탭 통합 HTML 생성 (사용자가 1명 이상인 경우)
    if len(user_calendars) >= 1:
        print(f"\n{'='*60}")
        print("탭 통합 HTML 생성")
        print(f"{'='*60}\n")

        tabbed_html = generate_tabbed_html(user_calendars, year)
        tabbed_file = OUTPUT_DIR / "commit_calendar_all.html"
        with open(tabbed_file, 'w', encoding='utf-8') as f:
            f.write(tabbed_html)
        print(f"[저장] {tabbed_file}")

    # 완료
    print("\n" + "=" * 60)
    print("완료!")
    print(f"개별 캘린더: commit_calendar - {{name}}.html")
    if len(user_calendars) >= 1:
        print(f"탭 통합: {OUTPUT_DIR / 'commit_calendar_all.html'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
