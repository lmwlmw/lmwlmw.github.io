# 댓글 / 방명록 / 통계 설정 메모

## 현재 적용된 구조

- 댓글 시스템: `giscus`
- 방명록: `/guestbook/`
- 통계 수집: `GoatCounter`
- 통계 페이지: `/stats/`
- 총 방문 수: footer
- 페이지별 방문 수: 글 상단 메타

## 1. 댓글 켜기

1. GitHub 저장소 `lmwlmw/lmwlmw.github.io` 에서 `Discussions`를 활성화한다.
2. Discussions 카테고리 하나를 만든다.
   - 추천 이름: `General`
3. GitHub에서 `giscus` 앱을 `lmwlmw/lmwlmw.github.io` 저장소에 설치한다.
   - 앱: https://github.com/apps/giscus
4. `https://giscus.app/` 에 들어가서 아래 값을 만든다.
   - `repo_id`
   - `category_id`
5. `_config.yml`에 아래 값을 채운다.

```yml
comments:
  provider: "giscus"
  giscus:
    repo_id: "..."
    category_name: "General"
    category_id: "..."
    discussion_term: "pathname"
    reactions_enabled: '1'
    theme: "light"
```

6. 여기까지 끝나면 게시글 댓글과 방명록이 동작한다.

## 2. GoatCounter 켜기

1. GoatCounter 사이트를 만든다.
   - https://goatcounter.com/
2. `_config.yml`의 아래 값을 채운다.

```yml
goatcounter:
  code: your-site-code
  public_dashboard_url: https://your-site-code.goatcounter.com
```

3. GoatCounter 설정에서 아래를 켠다.
   - Allow adding visitor counts on your website
   - Sites that can embed GoatCounter
     - `lmwlmw.github.io`

## 3. 결과

- footer에 사이트 총 방문 수 표시
- 게시글 메타에 페이지 방문 수 표시
- `/stats/`에 통계 대시보드 iframe 표시

## 4. 참고

- giscus: https://giscus.app/
- giscus repo: https://github.com/giscus/giscus
- GoatCounter getting started: https://www.goatcounter.com/help/start
- GoatCounter visitor counter: https://www.goatcounter.com/help/visitor-counter
- GoatCounter embed in frame: https://www.goatcounter.com/help/frame

## 5. 선택 이유

- `giscus`는 2026-07-22 기준 GitHub에서 약 `12k stars` 규모이고, GitHub Discussions 기반이라 댓글과 방명록 운영이 자연스럽다.
- `utterances`도 좋지만 2026-07-22 기준 약 `9.7k stars`이고, GitHub Issues 기반이라 방명록/커뮤니티형 운영은 `giscus`보다 덜 자연스럽다.
- `GoatCounter`는 2026-07-22 기준 약 `5.8k stars`이고, 정적 블로그에서 방문자 수와 통계를 함께 붙이기 쉽다.
- `Umami`는 약 `37k stars`대로 더 크지만 별도 서버와 데이터베이스가 필요해서 `github.io` 단독 운영에는 무겁다.
