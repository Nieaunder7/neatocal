#!/usr/bin/env python3
"""
여러 커밋 캘린더 HTML 파일들을 탭 인터페이스로 합치는 스크립트

사용법:
    python merge_calendars.py

출력:
    commit_calendar_all.html

참고:
    github_calendar.py가 자동으로 탭 통합 HTML을 생성하므로,
    이 스크립트는 기존 개별 HTML 파일들을 수동으로 합칠 때만 사용합니다.
"""

import re
import json
from pathlib import Path

# 설정 import
from config import PROJECT_COLORS, OUTPUT_DIR, NEATOCAL_PATH

# ============================================================
# 설정
# ============================================================

# 입력 디렉토리
INPUT_DIR = OUTPUT_DIR

# 출력 파일
OUTPUT_FILE = INPUT_DIR / "commit_calendar_all.html"


# ============================================================
# HTML 파일에서 CALENDAR_DATA 추출
# ============================================================

def extract_calendar_data(html_content):
    """HTML 파일에서 CALENDAR_DATA JSON을 추출"""
    # var CALENDAR_DATA = {...}; 패턴 매칭
    pattern = r'var\s+CALENDAR_DATA\s*=\s*(\{.*?\});'
    match = re.search(pattern, html_content, re.DOTALL)

    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"  JSON 파싱 오류: {e}")
            return None
    return None


def find_calendar_files(directory):
    """commit_calendar - *.html 패턴의 파일들을 찾음"""
    files = []
    for f in directory.glob("commit_calendar - *.html"):
        # 파일명에서 이름 추출 (commit_calendar - xxx.html -> xxx)
        name = f.stem.replace("commit_calendar - ", "")
        files.append({
            'path': f,
            'name': name,
        })

    # 이름순 정렬
    files.sort(key=lambda x: x['name'].lower())
    return files


# ============================================================
# 탭 인터페이스 HTML 생성
# ============================================================

def generate_tabbed_html(calendars, year=2025):
    """탭 인터페이스가 있는 통합 HTML 생성"""

    # 각 캘린더 데이터를 JavaScript 객체로 변환
    calendar_data_js = {}
    for cal in calendars:
        calendar_data_js[cal['name']] = cal['data']

    # 범례 HTML
    legend_html = ""
    for project, color in PROJECT_COLORS.items():
        legend_html += f'''      <div class="legend-row">
        <div class="legend-item" style="background-color: {color};"></div>
        <span class="legend-label">{project}</span>
      </div>
'''

    # 탭 버튼 HTML
    tab_buttons = ""
    for i, cal in enumerate(calendars):
        active = "active" if i == 0 else ""
        tab_buttons += f'      <button class="tab-btn {active}" data-name="{cal["name"]}">{cal["name"]}</button>\n'

    # JavaScript 데이터
    all_data_json = json.dumps(calendar_data_js, ensure_ascii=False)

    html_content = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>Commit Heatmap Calendar {year} - All Members</title>

<link rel='stylesheet' href='{NEATOCAL_PATH}/css/Oswald.css'>
<link rel='stylesheet' href='{NEATOCAL_PATH}/css/neatocal.css'>
<script type='text/javascript' src='{NEATOCAL_PATH}/neatocal.js'></script>

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

</head>
<body>

  <!-- 탭 버튼 -->
  <div class="tab-container">
{tab_buttons}  </div>

  <div class="calendar-container">
    <!-- 현재 선택된 이름 -->
    <div class="current-name" id="currentName">{calendars[0]['name'] if calendars else ''}</div>

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
  var currentCalendar = '{calendars[0]["name"] if calendars else ""}';

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

      // 캘린더 다시 초기화
      neatocal_init();
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
      neatocal_init();
    }}
  }})();
</script>
</html>
'''
    return html_content


# ============================================================
# 메인 실행
# ============================================================

def main():
    print("=" * 60)
    print("Commit Calendar Merger")
    print("=" * 60 + "\n")

    # 1단계: 파일 찾기
    print("[1/3] 캘린더 파일 검색...")
    files = find_calendar_files(INPUT_DIR)

    if not files:
        print("  오류: commit_calendar - *.html 파일을 찾을 수 없습니다.")
        return

    print(f"  {len(files)}개 파일 발견:")
    for f in files:
        print(f"    - {f['name']}")

    # 2단계: 데이터 추출
    print(f"\n[2/3] 캘린더 데이터 추출...")
    calendars = []

    for f in files:
        print(f"  {f['name']}...", end=" ")
        try:
            html_content = f['path'].read_text(encoding='utf-8')
            data = extract_calendar_data(html_content)

            if data:
                calendars.append({
                    'name': f['name'],
                    'data': data,
                })
                # 날짜 수 계산
                date_count = len([k for k in data.keys() if k.startswith('202')])
                print(f"OK ({date_count}일)")
            else:
                print("데이터 없음")
        except Exception as e:
            print(f"오류: {e}")

    if not calendars:
        print("\n오류: 추출된 캘린더 데이터가 없습니다.")
        return

    # 3단계: HTML 생성
    print(f"\n[3/3] 통합 HTML 생성...")
    html_content = generate_tabbed_html(calendars)

    OUTPUT_FILE.write_text(html_content, encoding='utf-8')
    print(f"  저장: {OUTPUT_FILE}")

    # 완료
    print("\n" + "=" * 60)
    print("완료!")
    print(f"브라우저에서 {OUTPUT_FILE} 을 열어 확인하세요.")
    print("=" * 60)


if __name__ == "__main__":
    main()
