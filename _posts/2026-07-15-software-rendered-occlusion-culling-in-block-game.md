---
title: "Block Game의 Software-Rendered Occlusion Culling 번역 정리"
excerpt_separator: "<!--more-->"
categories:
  - graphics
  - rendering
tags:
  - Occlusion Culling
  - Software Rendering
  - voxel
  - block-game
  - optimization
---

Eniko Fox의 `Software occlusion culling in Block Game` 글을, 가능한 한 원문 흐름을 유지하면서 자연스럽게 옮겨 정리한다.

작성자는 강한 GPU 환경을 전제로 하지 않았고, 목표 하드웨어도 낮은 사양을 상정하고 있었다. 또한 게임이 block 기반이라 지형과 chunk가 축 정렬된 cube로 구성되어 있어, 비교적 단순한 형태의 software occlusion culling이 잘 맞는 상황이었다.

핵심 판단은 이렇다.

- 동굴, 지하 공간처럼 가려진 geometry가 매우 많다.
- block game은 가리는 object와 가려지는 object가 대부분 cube다.
- GPU readback 기반 깊이 재사용은 환경상 부담이 있다.
- 그래서 낮은 해상도의 CPU depth buffer를 직접 만들어 culling하는 쪽이 더 단순하고 실용적이다.

결과적으로 이 방식은 꽤 잘 작동했다.

- 60FPS 기준 반 프레임 정도 안에서 동작
- frustum culling 이후 살아남은 chunk 중 최소 50% 이상 제거
- 실내나 동굴에서는 95% 이상 제거되는 경우도 있음

<!--more-->

아이디어 자체는 단순하다.

1. 먼저 장면의 가림 정보 역할을 하는 depth buffer를 만든다.
2. 각 후보 chunk가 그 depth buffer 뒤에 완전히 숨어 있는지 검사한다.
3. 조금이라도 보이면 렌더링하고, 전부 가려지면 버린다.

일반적으로는 GPU 기반 Hi-Z, previous frame 재사용, async readback 같은 기법을 붙일 수 있지만, 이 글에서는 그런 복잡도를 피하고 CPU에서 직접 구현한다.

작성자는 `256x128` 해상도의 매우 작은 depth buffer를 CPU 메모리 상의 float 배열로 만들었다. 그리고 block game이라는 특성을 이용해 triangle이 아니라 cube 단위로 depth를 채운다.

## 번역 정리

### 1. Chunk를 occluder hierarchy로 만든다

chunk 크기는 `16x16x16`이고, 이를 여러 단계의 subchunk로 다룬다.

- Level 0: chunk 전체
- Level 1: `2x2x2` 분할, 각 셀은 `8x8x8` block
- Level 2: `4x4x4` 분할, 각 셀은 `4x4x4` block
- Level 3: `8x8x8` 분할, 각 셀은 `2x2x2` block
- Level 4: `16x16x16` 분할, 각 셀은 block 1개

Level 4에서 먼저 `완전히 불투명하고 visible face가 있는 block`을 occluder 후보로 표시한다. 그다음 상위 level로 올라가며 `2x2x2` 영역이 전부 불투명하고, 그 안에 실제 visible face를 가진 하위 요소가 있을 때 상위 subchunk를 occluder로 만든다.

즉, 멀리서는 큰 덩어리로 가리고 가까이서는 작은 block 단위로 정밀하게 가리는 구조다.

### 2. 후보 chunk와 occluder를 모은다

카메라가 갱신되면 먼저:

- visible face나 entity가 없는 chunk를 제외
- world space에서 frustum culling
- 남은 chunk를 occlusion culling 후보로 등록

occluder는 거리별로 다른 level을 사용한다.

- 가장 가까운 영역은 block 단위 occluder 사용
- 더 멀어질수록 더 큰 subchunk 사용

이후에는 각 chunk의 실제 데이터에 다시 접근하지 않도록, 위치와 크기, index만 따로 모아 background thread로 넘긴다. 이렇게 해서 thread-safe하게 occlusion culling을 돌린다.

### 3. CPU에서 cube를 depth buffer에 그린다

이 구현에서 흥미로운 부분은 `triangle rasterize` 대신 `cube의 화면 범위를 아주 싸게 계산`한다는 점이다.

occluder에 대해:

- 먼저 subchunk 단위로 다시 frustum culling
- 8개 corner를 screen 좌표와 depth로 변환
- 각 y 행마다 최소 x, 최대 x를 기록
- 그 범위를 depth buffer에 수평 채우기

또 하나의 포인트는 depth를 일반적인 projection space z 대신 `linear view depth`로 다룬다는 점이다. 정밀한 GPU pipeline 재현이 목적이 아니므로, 더 싼 계산으로 충분하다고 본 것이다.

### 4. Occlusion 후보는 반대로 검사한다

occluder는 `가장 먼 depth`를 buffer에 채우고, 후보 chunk는 `가장 가까운 depth` 기준으로 검사한다.

후보 chunk가 차지하는 pixel 중 하나라도 buffer보다 앞에 있으면 보이는 것으로 간주한다. 어느 pixel도 통과하지 못하면 그 chunk는 완전히 가려졌다고 보고 culling한다.

단, 후보 chunk의 corner 중 일부가 near plane 뒤에 있으면 보수적으로 `visible` 처리한다. 검사가 불완전할 때 잘못 버리는 false positive를 피하기 위한 선택이다.

## 성능 최적화 흐름

이 글이 특히 좋은 이유는 최종 해법만 보여주는 게 아니라, 어디서 시간이 줄었는지를 단계별로 보여준다는 점이다.

### 더 싼 좌표 변환

처음에는 일반적인 `4x4 projection matrix` 기반 계산을 썼는데, 이를:

- view rotation
- additive translation
- focal length 기반 투영
- linear depth 사용

방식으로 바꿨다.

결과:

- 곱셈 수를 크게 줄임
- 처리 시간이 대략 `150ms -> 99ms`

### World space frustum culling

screen space에서 culling하려고 하면 투영 후 비선형성 때문에 보수적으로 계산해야 해서 오히려 비효율적이었다. 이를 world space의 bounding sphere + frustum plane 검사로 바꾸면서 더 싸고 더 정확해졌다.

결과:

- 대략 `150ms -> 61ms`

### Visible face 없는 것 제거

처음에는 공기만 아니면 후보로 보던 기준이 너무 느슨했다. 실제로 렌더될 수 있으려면 block이 아니라 `visible face`가 있어야 한다.

이 기준을 적용하자:

- 후보 수가 크게 줄고
- 시간도 `34ms` 수준까지 감소

### 가까운 occluder, 먼 후보 검사

원근 때문에:

- 가까운 occluder는 화면에서 크게 보임
- 먼 후보는 pixel 수가 적어 검사 비용이 낮음

그래서 가까운 것 위주로 가리고, 먼 것 위주로 검사하는 전략을 쓰자 약간 더 좋아졌다.

- `37ms -> 29ms`

### Multi-level subchunk

결정타는 여기다.

- 가까운 곳은 작은 occluder
- 먼 곳은 큰 occluder

를 사용하는 사실상의 mipmap 비슷한 구조를 도입했다.

또한 occluder는 subchunk 단위로 세분화하되, occlusion 후보는 굳이 잘게 쪼개지 않고 `chunk 전체`로 검사했다.

이 최적화 후:

- `29ms -> 4ms`

정도로 떨어졌다. 글 전체에서 가장 중요한 아이디어는 사실상 이 부분이다.

## 왜 1-pixel inset을 주는가

낮은 해상도 depth buffer를 쓰면, 실제 화면에서는 보이는 작은 틈이 buffer에서는 막혀 보이는 경우가 생긴다. 그러면 false occlusion이 발생한다.

이를 줄이기 위해 작성자는 occluder를 가로와 세로 1 pixel씩 줄여서 그린다. 정밀도는 약간 잃지만, 잘못 culling하는 문제를 크게 줄일 수 있다.

이 선택은 block game처럼 큰 덩어리의 가림이 많은 장르에서는 꽤 현실적인 tradeoff다.

## 한계점

좋은 방법이지만 만능은 아니다.

- 근처에 좋은 occluder가 없으면 성능이 떨어진다.
- 1~2 block 두께의 얇은 플레이어 구조물에는 약할 수 있다.
- chunk 경계와 1-pixel inset이 겹치면 틈이 남을 수 있다.

다만 작성자는 실제 성능 악화는 크지 않았다고 본다.

## 보충 해설

이 글에서 특히 배울 점은 `문제 구조에 맞는 단순한 해법을 택했다`는 점이다. GPU Hi-Z나 async readback처럼 화려한 방법 대신, block game과 CPU 목표 사양이라는 제약 안에서 가장 실용적인 해법을 골랐다.

또 하나는 `후보와 occluder를 다르게 설계했다`는 점이다. occluder는 세분화하고 후보는 chunk 단위로 유지했기 때문에 비용 폭증을 막을 수 있었다.

## 참조

- 원문: <https://enikofox.com/posts/software-rendered-occlusion-culling-in-block-game/>
- 원문 이미지: <https://enikofox.com/media/posts/21/occlusion-header-2.png>
- 원문 이미지: <https://enikofox.com/media/posts/22/occlusion-levels.png>

![오클루전 컬링 파이프라인 요약](/assets/images/posts/2026-07-15-occlusion/occlusion-pipeline.svg)

![거리 기반 오클루더 계층 요약](/assets/images/posts/2026-07-15-occlusion/occluder-hierarchy.svg)

## 용어 정리

- Occlusion Culling: 다른 물체에 완전히 가려져 화면에 안 보이는 것을 미리 버리는 최적화다.
- depth buffer: 화면의 각 pixel에 어느 물체가 더 앞에 있는지 기록하는 버퍼다.
- frustum culling: 카메라 시야 바깥의 물체를 먼저 제거하는 작업이다.
- GBuffer: deferred rendering에서 geometry 정보를 저장해 두는 버퍼 묶음이다.
- linear view depth: 카메라와의 거리를 선형적으로 표현한 depth 값이다.
- false positive: 실제로는 보이지 않지만 보인다고 판단하는 경우다.
- tradeoff: 한쪽 이득을 위해 다른 쪽 손해를 감수하는 선택이다.
