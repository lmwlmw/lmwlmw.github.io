# Pending Posts

검토용 글 초안을 임시로 두는 폴더입니다.

사용 방식:

1. 이 폴더에 마크다운 파일을 둡니다.
2. 발행할 파일명을 지정합니다.
3. `scripts/publish-post.sh <filename> <date-prefix>`를 실행하면 `_posts`로 이동합니다.

예시:

```sh
scripts/publish-post.sh first-test-post.md 2026-07-14
```

그러면 아래 파일로 발행됩니다.

```text
_posts/2026-07-14-first-test-post.md
```
