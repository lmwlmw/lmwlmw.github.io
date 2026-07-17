---
title: "Generalized Stylized Post-Processing Outline Scheme 정리"
excerpt_separator: "<!--more-->"
categories:
  - graphics
  - rendering
tags:
  - NPR
  - outline
  - TAA
  - post-processing
  - deferred-rendering
  - GDC
---

`Generalized Stylized Post-Processing Outline Scheme` 주제를, 현재 확인 가능한 공개 정보 기준으로 최대한 자연스럽게 정리한다.

다만 이 글은 예외가 있다. Zhihu 원문 본문은 공개 웹 환경에서 `403 Forbidden`으로 막혀 있어 전문을 직접 읽지 못했다. 그래서 아래 내용은 `원문 링크`, `검색 스니펫`, `GDC 세션 공개 설명`을 바탕으로 옮긴 정리다.

즉, 이 글은 원문 전문의 완전 번역이 아니라 `공개로 확인 가능한 부분의 번역/정리`다.

<!--more-->

공개 설명 기준으로 이 세션의 핵심은 다음과 같다.

- 실시간 NPR용 post-processing outline 기법
- `deferred rendering` 기반 게임 장면 전반에 적용 가능
- `GBuffer`에 저장된 geometry 정보 활용
- `TAA jitter` 이후 생성되는 low-discrepancy sequence에서 아이디어를 얻음
- post-processing 단계에서 생기는 문제를 `ray tracing denoising`과 유사한 방식으로 해결
- 결과적으로 더 안정적이고 손그림 같은 outline 표현을 목표로 함

## 번역 정리

### 왜 이 주제가 중요한가

stylized rendering에서 post-processing outline은 매우 흔한 선택이다.

- 기존 shading pipeline 위에 비교적 쉽게 붙일 수 있다.
- geometry 확장형 outline보다 범용성이 좋다.
- 화면 전체에 같은 스타일 규칙을 적용하기 쉽다.

하지만 단점도 분명하다.

- TAA와 섞이면 outline이 흔들리거나 번질 수 있다.
- depth와 normal 기반 edge detect는 장면 상황에 따라 noise가 많다.
- 얇은 선, 스타일화된 선, 손그림 느낌은 단순 Sobel filter만으로 만들기 어렵다.

즉, 이 세션은 `post-processing outline은 편하지만 불안정하다`는 오래된 문제를 겨냥한 것으로 보인다.

### GBuffer 기반 geometry 정보 사용

post-processing outline은 보통:

- depth
- normal
- material id 비슷한 분리 정보

를 활용해 경계를 검출한다.

이 세션도 deferred 기반 장면을 전제로 두고 있어, 기본적으로는 GBuffer의 geometry 정보를 활용하는 구조로 보인다.

### TAA jitter를 문제로만 보지 않고 샘플 자산으로 활용

일반적으로 jitter는 outline 안정성에 악영향을 주는 요소로 느껴진다. 그런데 여기서는 오히려 `low-discrepancy sequence` 관점에서 접근한다.

의미를 풀면 대략 이렇다.

- frame마다 서로 조금씩 다른 sample이 생긴다.
- 그 sample을 누적하고 복원하면 더 풍부한 형태 정보를 얻을 수 있다.
- 대신 그대로 두면 noise나 흔들림이 생기므로 후처리 안정화가 필요하다.

즉, jitter를 부작용이 아니라 `시간 축 sampling 자원`으로 보는 쪽에 가깝다.

### Ray tracing denoising과 비슷한 안정화

공개 설명에서 가장 중요한 부분은 다음이다.

- post-processing 단계에서 생기는 문제를 `ray tracing denoising`과 유사한 알고리즘으로 해결

여기서 추정할 수 있는 건:

- frame 간 누적
- neighborhood filtering
- edge-aware reconstruction
- history 기반 안정화

같은 개념이 outline에도 적용됐을 가능성이 크다는 점이다.

즉, 최종 선을 한 frame에서만 결정하지 않고, 여러 frame에 걸쳐 모인 정보를 안정적으로 복원하는 구조로 이해하는 게 자연스럽다.

### 왜 손그림 같은 느낌에 유리한가

손그림 느낌의 선은 완전히 기계적인 silhouette만으로는 부족하다.

필요한 요소는:

- 너무 깨끗하지 않은 선 질감
- frame 간 튀지 않는 안정성
- 장면 전체에 일관된 스타일
- 얇은 부분과 두꺼운 부분의 조형적 제어

단순 edge detect는 첫 단계로는 좋지만, 스타일 표현까지 밀어붙이려면 noise를 통제하면서 선을 재구성하는 단계가 추가로 필요하다.

이 세션이 말하는 `denoising` 유사 접근은 바로 이 지점에서 의미가 있어 보인다.

## 보충 해설

기존 post-processing outline은 대개:

- depth/normal edge detect
- threshold
- blur 또는 dilation

정도로 끝나는 경우가 많다.

그런데 이 세션은 한 단계 더 나가서:

- 시간 축 정보
- 안정화
- 스타일 재구성

을 결합하려는 방향으로 읽힌다.

또한 세션 제목에 `Generalized`가 들어가는 것도 중요하다. 특정 캐릭터 shader 전용이나 특정 camera 구도 전용이 아니라, deferred 장면 전반에 적용 가능한 범용 post-processing outline을 노리는 쪽으로 보인다.

## 참조

- 원문: <https://zhuanlan.zhihu.com/p/1895785690161198348>
- GDC 세션 설명: <https://schedule.gdconf.com/session/generalized-stylized-post-processing-outline-scheme/911861>

## 용어 정리

- NPR: Non-Photorealistic Rendering의 약자로, 현실 재현보다 스타일 표현을 중시하는 렌더링이다.
- outline: 물체 경계나 내부 특징을 선으로 강조하는 표현이다.
- post-processing: 장면을 다 그린 뒤 screen image를 한 번 더 가공하는 단계다.
- deferred rendering: geometry 정보를 GBuffer에 저장한 뒤 조명 계산을 나중에 하는 렌더링 방식이다.
- GBuffer: depth, normal, material 정보 같은 geometry 데이터를 담아 두는 buffer 묶음이다.
- TAA: Temporal Anti-Aliasing의 약자로, 여러 frame의 정보를 활용해 계단 현상을 줄이는 방식이다.
- jitter: 매 frame sample 위치를 아주 조금씩 흔들어 시간 축 샘플을 모으는 기법이다.
- denoising: noisy한 결과를 여러 정보를 이용해 더 안정적으로 복원하는 과정이다.
