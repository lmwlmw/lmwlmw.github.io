# 댓글 / 방명록 / 통계 설정 메모

## 현재 적용된 구조

- 댓글 시스템: `utterances`
- 방명록: `/guestbook/`
- 통계 수집: `GoatCounter`
- 통계 페이지: `/stats/`
- 총 방문 수: footer
- 페이지별 방문 수: 글 상단 메타

## 1. 댓글 켜기

1. GitHub에서 `utterances` 앱을 `lmwlmw/lmwlmw.github.io` 저장소에 설치한다.
   - 앱: https://github.com/apps/utterances
2. 설치만 끝나면 현재 코드 기준으로 게시글 댓글과 방명록이 동작한다.

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

- utterances: https://utteranc.es/
- GoatCounter getting started: https://www.goatcounter.com/help/start
- GoatCounter visitor counter: https://www.goatcounter.com/help/visitor-counter
- GoatCounter embed in frame: https://www.goatcounter.com/help/frame
