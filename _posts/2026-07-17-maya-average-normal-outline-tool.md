---
title: "Maya 워크플로우의 Smooth Normal Outline 툴 정리"
excerpt_separator: "<!--more-->"
categories:
  - graphics
  - rendering
tags:
  - Maya
  - outline
  - normal
  - toon-rendering
  - ShaderFX
  - HLSL
---

`Maya工作流的平滑法线描边小工具` 글을, 현재 확인 가능한 공개 정보 기준으로 최대한 자연스럽게 정리한다.

2026-07-17 기준으로 Zhihu 원문 페이지의 제목과 본문 첫 문단까지 직접 확인했다. 다만 이 글은 여전히 원문 전체를 문단별 직역한 번역본이 아니라, 원문에서 확인한 핵심 문제의식과 원문을 참조한 GitHub 구현 정보를 함께 묶어 재구성한 정리다.

검색 스니펫 기준으로 이 글의 문제의식은 비교적 분명하다.

- 현재 가장 흔한 toon outline 방식은 back-face normal extrusion이다.
- 이 방식은 전반적으로 좋지만, hard surface에서는 outline이 끊어진다.
- 이유는 vertex normal 방향이 면마다 크게 갈라지기 때문이다.

즉, 이 글은 `하드 서피스에서 끊기지 않는 더 매끈한 outline normal을 어떻게 만들 것인가`를 다루는 글로 읽힌다.

<!--more-->

또 원문을 직접 참조한 GitHub 구현 설명을 보면, 핵심 아이디어가 더 구체적으로 드러난다.

- mesh의 average normals를 계산한다.
- 그 average normals를 `uv2`에 기록한다.
- 기록할 때 `Octahedron compression`을 사용한다.
- vertex shader에서 다시 decode해서 outline 방향으로 사용한다.

즉, 단순히 모델의 원래 normal로 외곽선을 밀어내는 대신, `더 부드러운 average normal`을 별도 채널에 저장해 outline 전용 방향으로 활용하는 접근이다.

## 번역 정리

### 왜 기본 back-face outline은 hard surface에서 깨지는가

toon rendering에서 가장 흔한 outline 방식은 back-face extrusion이다.

대략 이런 구조다.

1. mesh를 back-face로 한 번 더 그린다.
2. vertex를 normal 방향으로 바깥쪽으로 밀어낸다.
3. 앞면 geometry 뒤에서 보이는 두꺼운 외곽선을 만든다.

이 방식은 간단하고 빠르며 실시간 캐릭터 렌더링에 잘 맞는다.

하지만 hard surface에서는 문제가 생긴다.

- 면이 sharply split된 곳에서는 vertex normal이 갑자기 꺾인다.
- extrusion 방향이 면마다 달라진다.
- 그 결과 outline이 부드럽게 이어지지 않고 찢기거나 끊어진다.

즉, shading용 normal과 outline용 normal이 항상 같은 목적에 맞는 것은 아니다.

### 해결 아이디어는 outline 전용 smooth normal을 따로 쓰는 것

이 글의 핵심은 원래 mesh normal 대신 `outline 전용 smooth normal`을 따로 준비하는 데 있는 것으로 보인다.

검색 결과와 연결된 구현 설명을 종합하면 흐름은 대략 이렇다.

1. 원래 vertex normal은 유지한다.
2. outline 계산용 average normal을 별도로 만든다.
3. 이 값을 mesh의 `uv2` 같은 추가 채널에 저장한다.
4. shader에서 다시 decode해서 outline extrusion 방향으로 사용한다.

이렇게 하면:

- 원래 shading normal은 유지
- outline 방향만 더 매끄럽게 제어

가 가능해진다.

즉, 외곽선이 끊기는 문제를 `모델링 수정`이 아니라 `데이터 분리`로 해결하는 쪽이다.

### 왜 uv에 normal을 저장하나

GitHub 구현 설명에서 특히 중요한 부분은 `average normal을 uv2에 encode한다`는 점이다.

이 선택의 의미는 비교적 명확하다.

- Maya 안에서 추가 attribute나 특수 버퍼보다 UV 채널이 다루기 쉬울 수 있다.
- FBX 같은 일반 asset pipeline을 타고 넘기기 쉽다.
- shader 쪽에서는 TEXCOORD semantic으로 쉽게 읽을 수 있다.

다만 normal은 3차원 벡터고 UV는 보통 2채널이기 때문에, 그대로는 넣을 수 없다. 그래서 `Octahedron compression` 같은 normal encoding 기법을 사용해 3D 방향을 2D 값으로 압축한다.

### 예상 워크플로우

참조된 구현 설명을 보면 절차는 다음과 비슷하다.

1. 선택된 object의 원래 vertex normal을 백업
2. mesh의 average normal 계산
3. average normal을 face-vertex 단위로 가져옴
4. 그것을 `AverageNormalWS` 또는 `AverageNormalTS` 형태로 정리
5. `Octahedron compression`으로 `uv2`에 encode
6. 원래 normal 복구
7. vertex shader에서 decode 후 outline 방향으로 사용

이 방식은 모델링 데이터는 원상 복구하고, outline에 필요한 smooth 정보만 별도 채널에 저장하는 구조다.

### 이 접근의 장점

- hard surface에서도 더 매끈한 outline을 만들 수 있다.
- shading normal은 그대로 유지하므로 toon shading 본체를 크게 건드리지 않는다.
- Maya 작업 흐름 안에서 툴로 자동화하기 좋다.
- shader에서는 decode 후 바로 extrusion 방향으로 쓸 수 있다.

즉, 아티스트 워크플로우와 runtime shader를 깔끔하게 연결하는 접근이다.

## 보충 해설

이 아이디어가 재미있는 이유는 `normal 하나로 모든 문제를 해결하려 하지 않는다`는 점이다.

실제로 렌더링에서는 같은 mesh라도 목적마다 원하는 normal이 다를 수 있다.

- lighting용 normal
- outline용 normal
- special effect용 direction

이 각각 다를 수 있는데, 이 글은 outline를 위해 그 방향 데이터를 분리해 두자는 접근이다.

또 하나 중요한 점은 이 방법이 Maya workflow 중심이라는 것이다. 즉, runtime에서 무거운 계산을 하지 않고, DCC 단계에서 필요한 데이터를 baking 비슷하게 만들어 asset에 실어 보내는 구조로 이해할 수 있다.

## 참조

- 원문: <https://zhuanlan.zhihu.com/p/538660626>
- 관련 링크: <https://github.com/SelfishKrus/MayaPython_AverageNormalsToUVs>
- 관련 링크: <https://github.com/SelfishKrus/K_URP_ToonShading>

## 용어 정리

- back-face extrusion: 뒷면 mesh를 normal 방향으로 바깥쪽으로 밀어서 외곽선을 만드는 기법이다.
- hard surface: 기계, 갑옷, 건물처럼 면이 딱딱하게 꺾이는 형태의 모델을 말한다.
- vertex normal: vertex에서 표면이 어느 방향을 향하는지 나타내는 벡터다.
- average normal: 주변 면들의 방향을 평균 내 더 부드럽게 만든 normal이다.
- UV channel: mesh에 추가 데이터를 담을 때도 자주 쓰이는 2차원 좌표 채널이다.
- Octahedron compression: 3차원 normal 벡터를 2차원 값으로 압축해서 저장하는 방법이다.
- encode/decode: 데이터를 저장하기 좋은 형식으로 바꾸는 과정과, 다시 원래 의미로 복원하는 과정을 말한다.
- ShaderFX: Maya에서 shader를 그래프 기반으로 구성할 수 있게 해 주는 도구다.
