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

`Maya工作流的平滑法线描边小工具` 글을, 원문 흐름을 최대한 유지하면서 자연스럽게 옮겨 정리한다.

작성자는 오랜만에 Zhihu에 글을 올린다고 말하며, 바로 문제를 꺼낸다. 현재 가장 흔한 toon rendering outline 방식은 back-face normal extrusion인데, 전반적으로는 좋지만 hard surface에서 outline이 끊어진다는 점이 단점이라는 것이다. 이유는 간단하다. vertex normal 방향이 면마다 다르기 때문이다.

하지만 모델에는 원래 soft edge와 hard edge가 섞여 있고, 단지 outline 때문에 원래 normal을 통째로 바꾸는 것은 적절하지 않다. 그래서 보통은 모델 vertex의 average normal을 저장해 두고, 원래 normal 대신 그 average normal로 outline extrusion을 수행한다. 스킨된 mesh라면 tangent space 기준으로 저장해야 한다는 점도 함께 짚는다.

![원문 이미지](https://pica.zhimg.com/v2-89821a13bc0c6b37fcd81d11bf4022e4_b.jpg)

원문 이미지 링크: <https://pica.zhimg.com/v2-89821a13bc0c6b37fcd81d11bf4022e4_b.jpg>

<!--more-->

## 번역 정리

### 왜 average normal 기반 outline이 필요한가

글의 출발점은 매우 실무적이다. back-face extrusion은 편하고 널리 쓰이지만, hard surface에서는 끊어진다. 그런데 모델에는 원래 hard edge가 필요할 수 있으니, outline 문제 때문에 원본 normal을 망가뜨릴 수는 없다.

그래서 가장 많이 쓰는 보완책은 이렇다.

1. 모델 vertex의 average normal을 만든다.
2. 그 값을 vertex color에 저장한다.
3. outline을 그릴 때 원래 normal 대신 average normal을 사용한다.

작성자는 대략적인 개념 그림도 함께 보여준다.

![원문 이미지](https://pica.zhimg.com/v2-30ee1995b11b729fc8f659398576551e_1440w.jpg)

원문 이미지 링크: <https://pica.zhimg.com/v2-30ee1995b11b729fc8f659398576551e_1440w.jpg>

### 왜 Maya용 툴을 직접 만들었는가

이 글은 Maya workflow를 쓰는 팀 환경에서 나온 도구 이야기다. 작성자는 처음에 검색으로 찾은 것이 3ds Max 버전이나 Unity FBX SDK 버전뿐이었다고 말한다. Houdini 기반 workflow도 있지만, 이 글은 Maya 사용자를 위한 글이라고 선을 긋는다.

또 작업 환경상 하나의 FBX 안에서 특정 submesh만 average normal 계산이 필요하고, 나머지는 필요하지 않은 경우가 많다고 설명한다. 이럴 때는 Maya 안에서 어느 submesh에 계산을 적용할지 직접 제어하는 편이 훨씬 낫다. 이것이 Maya 툴을 만든 중요한 이유라고 적는다.

### 처음에는 기존 명령으로 처리하려 했지만 너무 느렸다

처음 접근은 Maya 기본 명령을 활용하는 쪽이었다. 필요한 것은 결국 vertex 위치 정보와 normal 방향이니, 관련 API와 명령을 찾았고 `polyAverageNormal` 같은 기능도 금방 발견한다.

문제는 이 명령이 원래 normal을 직접 바꿔 버린다는 점이다. 그래서 흐름이 다음처럼 꼬인다.

1. 원래 normal 저장
2. average normal 계산
3. 그 결과를 vertex color에 저장
4. 원래 normal 복원

이렇게 한 번 갔다가 다시 돌아오는 구조로는 고폴리곤 mesh에서 너무 느렸다. 작성자는 1만 1천 face 정도에서 계산에 50분이 걸렸다고 적는다. 결과는 맞았지만 실사용은 어렵다는 판단이다.

이때부터 방향을 바꾼다. API가 normal을 직접 건드리게 두지 말고, 필요한 average normal 값을 직접 계산해서 바로 vertex color에 넣는 함수로 가야 한다는 것이다. 그렇게 바꾸자 계산 시간이 대략 30초 수준으로 줄었다고 설명한다.

### 스킨된 mesh에서는 tangent space가 문제다

여기서 끝이 아니다. 스킨된 mesh에서 이 데이터를 쓰려면 tangent space 기준으로 변환해야 한다. 그런데 당시 Maya에는 `perVertexTangent` 같은 간단한 API가 없었다고 적는다.

처음에는 UV와 normal만으로 tangent를 계산해 보려 했지만, UV와 vertex 데이터가 예상과 깔끔하게 맞지 않아 포기했다고 한다. 그러다 다른 사용자의 조언으로 `OpenMaya`를 쓰게 되고, Maya의 C++ 기반 low-level API를 Python으로도 호출할 수 있다는 점을 알게 됐다고 설명한다.

이후에는 사실상 전체 계산을 `OpenMaya` 기반으로 옮긴다. 중간에 `normal / tangent / binormal`의 index 순서가 서로 달라 한 번 더 고생했다고도 적어 둔다.

### 최종 구현은 OpenMaya 기반 계산으로 정리됐다

작성자는 최종적으로는 average normal 계산과 tangent space 변환을 전부 `OpenMaya`로 처리했다고 말한다. 그리고 이렇게 정리한다.

- 모델 공간 좌표계 문제는 tangent space로 옮기면 크게 신경 쓰지 않아도 된다.
- 당시 코드는 `ColorSet` 이름과 `uv map` 이름을 하드코딩해 둔 상태였다.
- 지금 다시 보면 `cmds`로 이름을 받아 더 유연하게 만들 수 있었을 것이라고 회고한다.
- vertex color set이 없는 모델은 검사 후 새로 만들어 주는 개선도 가능하다고 적는다.

성능은 확실히 좋아졌다. `OpenMaya`로 옮긴 뒤에는 vertex 수 2만 2천 정도 mesh도 몇 초 안에 계산할 수 있었다고 한다.

![원문 이미지](https://pic2.zhimg.com/v2-b39f3b8e4126158eb1faf9db1541b9df_1440w.jpg)

원문 이미지 링크: <https://pic2.zhimg.com/v2-b39f3b8e4126158eb1faf9db1541b9df_1440w.jpg>

### 테스트와 사용 시 주의점

글 후반에는 간단한 skeletal animation 테스트와 before/after 비교 이미지가 들어 있다. average normal 기반 outline를 적용한 결과가 더 부드럽고, hard surface 경계가 덜 끊기는 방향임을 보여주려는 의도다.

작성자는 몇 가지 실무 메모도 남긴다.

- `Maya 2020`에서는 크래시가 난다.
- 사용 전 모델 history를 지우는 것이 좋다.
- 아주 오래 작업한 모델은 `OBJ`로 내보내 계산한 뒤 color만 다시 가져오는 것도 방법이다.

![원문 이미지](https://pic3.zhimg.com/v2-f460d0c46d3a249b1866091a1b37b7f4_1440w.jpg)

원문 이미지 링크: <https://pic3.zhimg.com/v2-f460d0c46d3a249b1866091a1b37b7f4_1440w.jpg>

![원문 이미지](https://pica.zhimg.com/v2-967bc0da2cc36bfc2a36fcc1c51ec85a_b.jpg)

원문 이미지 링크: <https://pica.zhimg.com/v2-967bc0da2cc36bfc2a36fcc1c51ec85a_b.jpg>

## 보충 해설

이 글에서 흥미로운 지점은 알고리즘 자체보다도 workflow 설계다. average normal 기반 outline라는 아이디어 자체는 업계에서 널리 쓰이지만, 작성자는 그것을 Maya 현업 파이프라인 안에서 어떻게 제어 가능하게 만들 것인가에 더 집중한다.

즉, 핵심은 `원본 shading normal은 건드리지 않고`, outline용 데이터를 별도 vertex color로 굽고, 필요한 submesh에만 선택적으로 적용하는 것이다. runtime shader보다 DCC 단계의 제어성과 속도 개선이 더 중요한 문제였다는 점이 글 전체에 잘 드러난다.

## 참조

- 원문: <https://zhuanlan.zhihu.com/p/538660626>
- 관련 링크: <https://github.com/SelfishKrus/MayaPython_AverageNormalsToUVs>
- 관련 링크: <https://github.com/SelfishKrus/K_URP_ToonShading>
- 원문 이미지: <https://pica.zhimg.com/v2-89821a13bc0c6b37fcd81d11bf4022e4_b.jpg>
- 원문 이미지: <https://pica.zhimg.com/v2-30ee1995b11b729fc8f659398576551e_1440w.jpg>
- 원문 이미지: <https://pic2.zhimg.com/v2-b39f3b8e4126158eb1faf9db1541b9df_1440w.jpg>
- 원문 이미지: <https://pic3.zhimg.com/v2-f460d0c46d3a249b1866091a1b37b7f4_1440w.jpg>
- 원문 이미지: <https://pica.zhimg.com/v2-967bc0da2cc36bfc2a36fcc1c51ec85a_b.jpg>

## 용어 정리

- back-face extrusion: 뒷면 mesh를 normal 방향으로 바깥쪽으로 밀어서 외곽선을 만드는 기법이다.
- hard surface: 기계, 갑옷, 건물처럼 면이 딱딱하게 꺾이는 형태의 모델을 말한다.
- vertex normal: vertex에서 표면이 어느 방향을 향하는지 나타내는 벡터다.
- average normal: 주변 면들의 방향을 평균 내 더 부드럽게 만든 normal이다.
- vertex color: vertex마다 색 정보를 저장하는 채널로, 색 외의 보조 데이터 저장에도 자주 활용된다.
- tangent space: 표면 기준 local 좌표계다. 스킨된 mesh나 normal map 처리에서 자주 사용한다.
- OpenMaya: Maya의 low-level API 집합으로, Python에서 호출해 더 세밀하고 빠른 처리를 할 수 있다.
- ShaderFX: Maya에서 shader를 그래프 기반으로 구성할 수 있게 해 주는 도구다.
