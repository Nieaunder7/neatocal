#!/usr/bin/env python3
"""
기존 commit_calendar HTML 파일을 Standalone HTML로 변환하는 스크립트

사용법:
    python convert_to_standalone.py commit_calendar_all.html
    python convert_to_standalone.py commit_calendar_all.html -o output.html
"""

import re
import sys
from pathlib import Path

def convert_to_standalone(input_file, output_file=None):
    """HTML 파일을 standalone으로 변환"""

    input_path = Path(input_file)
    if not input_path.exists():
        print(f"오류: 파일을 찾을 수 없습니다: {input_file}")
        return False

    # 출력 파일명 설정
    if output_file is None:
        output_path = input_path.parent / f"{input_path.stem}_standalone{input_path.suffix}"
    else:
        output_path = Path(output_file)

    # neatocal 경로
    neatocal_dir = input_path.parent / "neatocal"

    # CSS 파일 읽기
    css_file = neatocal_dir / "css" / "neatocal.css"
    if css_file.exists():
        css_content = css_file.read_text(encoding='utf-8')
    else:
        print(f"경고: CSS 파일을 찾을 수 없습니다: {css_file}")
        css_content = ""

    # JS 파일 읽기
    js_file = neatocal_dir / "neatocal.js"
    if js_file.exists():
        js_content = js_file.read_text(encoding='utf-8')
    else:
        print(f"경고: JS 파일을 찾을 수 없습니다: {js_file}")
        js_content = ""

    # HTML 파일 읽기
    html_content = input_path.read_text(encoding='utf-8')

    # Google Fonts 링크 추가
    google_fonts = '''<!-- Google Fonts -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@300;400&display=swap" rel="stylesheet">
'''

    # 외부 CSS 링크 제거하고 인라인 CSS로 대체
    css_inline = f"<!-- NeatoCal CSS (Inline) -->\n<style>\n{css_content}\n</style>"
    js_inline = f"<!-- NeatoCal JS (Inline) -->\n<script>\n{js_content}\n</script>"

    # ./neatocal/css/Oswald.css 링크 제거
    def replace_oswald(m):
        return ""

    def replace_css(m):
        return css_inline

    def replace_js(m):
        return js_inline

    html_content = re.sub(
        r"<link[^>]*href=['\"]\.?/?neatocal/css/Oswald\.css['\"][^>]*>",
        replace_oswald,
        html_content
    )

    # ./neatocal/css/neatocal.css 링크를 인라인 CSS로 대체
    html_content = re.sub(
        r"<link[^>]*href=['\"]\.?/?neatocal/css/neatocal\.css['\"][^>]*>",
        replace_css,
        html_content
    )

    # 외부 JS 스크립트를 인라인 JS로 대체
    html_content = re.sub(
        r"<script[^>]*src=['\"]\.?/?neatocal/neatocal\.js['\"][^>]*></script>",
        replace_js,
        html_content
    )

    # <head> 태그 다음에 Google Fonts 추가 (아직 없는 경우)
    if "fonts.googleapis.com" not in html_content:
        html_content = re.sub(
            r"(<head[^>]*>)",
            rf"\1\n{google_fonts}",
            html_content,
            count=1
        )

    # 결과 저장
    output_path.write_text(html_content, encoding='utf-8')
    print(f"변환 완료: {output_path}")
    print(f"파일 크기: {output_path.stat().st_size / 1024:.1f} KB")

    return True


def main():
    if len(sys.argv) < 2:
        print("사용법: python convert_to_standalone.py <input.html> [-o output.html]")
        print("\n예시:")
        print("  python convert_to_standalone.py commit_calendar_all.html")
        print("  python convert_to_standalone.py commit_calendar_all.html -o shared.html")
        return

    input_file = sys.argv[1]
    output_file = None

    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]

    convert_to_standalone(input_file, output_file)


if __name__ == "__main__":
    main()
