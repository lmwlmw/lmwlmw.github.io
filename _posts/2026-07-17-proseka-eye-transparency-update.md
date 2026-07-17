---
title: "프로세카 3주년 눈 투과 표현 번역"
excerpt_separator: "<!--more-->"
categories:
  - graphics
  - rendering
tags:
  - Unity
  - URP
  - stencil
  - transparency
  - anime-rendering
  - Project Sekai
---

이 글은 원문 저작권자의 요청이나 삭제 요청이 있을 경우 언제든지 삭제될 수 있습니다.

Colorful Palette의 글 `プロジェクトセカイ 3周年グラフィックスアップデート解説 (目の透過表現)`을, 가능한 한 원문 흐름을 유지하면서 자연스럽게 번역한다.

프로세카 3주년 업데이트에서는 머리카락 너머로 눈이 은근히 비치는 표현이 추가됐다. 이런 표현은 캐릭터의 감정선을 더 섬세하게 보여줄 수 있지만, 구현은 생각보다 까다롭다.

- 눈은 얼굴 안쪽에 있는 얇은 파츠다.
- 머리카락, 눈꺼풀, 속눈썹, 홍채가 서로 매우 가깝게 겹친다.
- 반투명 표현을 넣는 순간 depth test, draw order, 캐릭터 간 겹침 문제가 함께 발생한다.

이 글의 핵심은 `반투명 눈을 어떻게 자연스럽게 보이게 할 것인가`보다 `그 반투명을 다른 얼굴 파츠나 다른 캐릭터와 충돌 없이 어떻게 제어할 것인가`에 가깝다.

<!--more-->

개발 환경은 `Unity + Universal RP`다.

눈 표현은 기본적으로 두 개의 pass로 구성된다.

1. 일반 눈 렌더링용 opaque pass
2. 눈 투과 표현용 transparent pass

투과용 pass는 별도의 `RendererFeature`로 실행되며, 기본 설정은 대략 다음과 같다.

- `Cull Back`
- `ZWrite Off`
- `Blend SrcAlpha OneMinusSrcAlpha`
- 상황에 따라 `ZTest Always`

즉, 일반적인 opaque 렌더링 위에 transparent overlay pass를 하나 더 얹는 구조다.

## 번역

### 방법 1. 눈 pass를 `ZTest Always`로 두고 그냥 그리기

가장 단순한 접근이다.

- 기본 눈은 정상적으로 렌더링
- 투과 눈 pass는 depth test를 무시하고 항상 그림

속눈썹만 살짝 투과시키는 정도라면 얼핏 괜찮아 보인다. 하지만 눈 전체를 투과시키면 바로 문제가 난다.

- 원래 눈꺼풀 뒤에 가려져 있어야 하는 홍채도 같이 비쳐버린다.
- 즉, `가려진 상태여야 하는 눈 내부 파츠`까지 모두 앞으로 튀어나온다.

이 방식은 너무 단순해서 얼굴 내부의 가림 관계를 보존하지 못한다.

### 방법 2. 눈을 stencil에 기록하고, 머리카락이 지나갈 때 값을 1 증가시키기

두 번째 접근은 stencil을 써서 머리카락에 가려진 위치만 투과를 허용하는 방식이다.

개념은 이렇다.

1. 눈을 렌더링할 때 stencil에 특정 값을 기록
2. 머리카락을 렌더링할 때 그 값을 증가
3. 눈 투과 pass는 증가된 값이 있는 영역에서만 렌더링

아이디어 자체는 그럴듯하지만, 캐릭터가 여러 명 겹치면 바로 무너진다.

- 다른 캐릭터의 머리카락이 앞에 있어도 stencil 값이 섞인다.
- 머리카락이 여러 번 겹치면 증가 횟수도 꼬인다.
- 그 결과 눈이 엉뚱한 캐릭터 머리카락 앞에 보이거나 일부가 잘려 나간다.

즉, `증가형 stencil`은 단일 캐릭터 안에서는 버틸 수 있어도 다중 캐릭터 중첩 상황에는 안정적이지 않다.

### 방법 3. 눈 투과용 vertex를 카메라 쪽으로 당기기

세 번째 접근은 눈 투과 pass를 실제로 약간 앞으로 끌어오는 방식이다.

- vertex shader에서 depth를 조정
- linear depth로 변환한 뒤 카메라 쪽으로 살짝 이동
- 다시 clip space depth로 돌려놓음

이 방식은 `Metal`, `Vulkan` 계열에서는 꽤 잘 보였다고 한다. 하지만 `OpenGLES`, 특히 Android에서 문제가 생겼다.

- 카메라에 가까운 구간의 depth precision이 낮은 환경에서는
- 뒤에 있는 캐릭터 눈이 앞 캐릭터보다 앞으로 튀어나와 보이는 현상이 생긴다.

즉, 구현 자체는 성립하지만 플랫폼 간 depth precision 차이 때문에 결과가 일관되지 않았다.

### 최종 채택 방식: 캐릭터별 stencil bit 사용

최종 해법은 `캐릭터마다 stencil buffer의 다른 bit 자리를 할당`하는 방식이다.

- 다른 캐릭터와 stencil 정보가 섞이지 않는다.
- 증감 연산 대신 bit 단위 masking이라 제어가 명확하다.
- 겹치는 캐릭터 수가 늘어나도 논리가 비교적 안정적이다.

글에서는 이 방식을 두 단계 문제 해결로 설명한다.

## 캐릭터 겹침 문제 해결

### Step 1. 눈 기본 렌더링 시 자기 캐릭터 bit를 1로 기록

예를 들어 캐릭터 2가 stencil의 특정 bit를 담당한다고 하면, 눈이 그려지는 위치에 그 bit만 1이 되게 쓴다.

여기서 중요한 건 `WriteMask`를 이용해 자기 bit만 건드린다는 점이다.

### Step 2. 머리카락 렌더링 시 자기 bit를 제외한 나머지 bit를 0으로 지움

이 단계가 핵심이다.

- 내 머리카락은 내 눈 정보는 유지
- 다른 캐릭터 눈과 관련된 bit는 제거

이렇게 하면 앞에 있는 캐릭터 머리카락이 뒤 캐릭터 눈 투과를 잘못 통과시키는 문제가 크게 줄어든다.

### Step 3. 눈 투과 pass는 자기 bit가 살아 있는 곳에서만 그림

투과 pass는 `ZTest Always`로 그리더라도, stencil에서 자기 bit가 남아 있는 pixel만 통과시키므로 표시 위치가 통제된다.

즉, depth test를 희생하는 대신 stencil mask로 `어디에 그릴지`를 다시 엄격하게 제한한 구조다.

## 속눈썹과 홍채의 순서 제어

캐릭터 간 겹침만 해결해도 아직 문제가 남는다.

- 속눈썹
- 홍채

둘 다 `ZTest Always`로 그리면 서로 겹쳐 보이는 깨짐이 생긴다.

이 문제는 속눈썹을 먼저 그리고, 그 영역의 stencil을 바로 0으로 지우는 방식으로 해결한다.

1. stencil 조건을 만족하는 위치에 속눈썹을 그림
2. 속눈썹이 그려진 영역의 stencil bit를 0으로 reset
3. 이후 홍채는 남아 있는 영역에만 그림

이렇게 하면 홍채가 속눈썹 위로 침범하지 못한다. 결과적으로 눈 내부 layer 순서까지 stencil로 제어하는 셈이다.

## 참조

- 원문: <https://media.colorfulpalette.co.jp/n/n927a776b6b35>

## 용어 정리

- stencil buffer: pixel마다 작은 정수 값을 저장해 특정 영역만 통과시키거나 막는 버퍼다.
- ZTest Always: depth 값과 상관없이 항상 통과시키는 depth test 설정이다.
- ZWrite Off: 현재 그리는 물체의 depth를 depth buffer에 기록하지 않는 설정이다.
- WriteMask: stencil의 특정 bit만 수정하도록 제한하는 설정이다.
- clip space: projection 변환 직후 GPU가 depth와 screen 위치 계산에 쓰는 공간이다.
- depth precision: depth 값이 얼마나 세밀하게 구분되는지 나타내는 정도다.
- pass: 하나의 material이나 effect가 GPU에서 한 번 그려지는 단위다.
