# Blog Translation Guidelines

This file is stored in the GitHub repository for working reference only.
It must not be rendered on the public blog.

## Current Rules

1. When the source is a blog/article link, prioritize a source-faithful translation over a short summary.
2. Keep the original paragraph order as much as possible.
3. Include code blocks, examples, and detailed steps whenever they exist in the source.
4. Add `번역` to the post title.
5. The first sentence of the post must be:
   `이 글은 원문 저작권자의 요청이나 삭제 요청이 있을 경우 언제든지 삭제될 수 있습니다.`
6. Inline source images may be shown in the body, and the real image URL may be shown right below each image.
7. The `참조` section must contain links only.
8. Do not include `원문 이미지` links inside `참조`.
9. Add `전문 요약` at the end of the post.
10. Add `용어 정리` at the end of the post.
11. If the source article is too long, split it into small sections and continue translating section by section until the whole source is covered.
12. For long articles, do not replace the full translation with a compressed summary. Use repeated translation passes until the full text is represented on the blog.
13. When updating a long article over multiple passes, preserve the existing translated sections and append or expand the remaining untranslated sections.

## Publication Lanes

- Public blog posts:
  - location: `_posts/`
  - rendered on site

- Site-hidden drafts:
  - location: `.private-posts/`
  - excluded from Jekyll build
  - still visible in this public GitHub repository

## Important Privacy Note

Because this repository is public, files inside `.private-posts/` are hidden from the blog site, but not private on GitHub.
For truly private writing, use a separate private repository or another private storage location.
