---
title: "Unity에서 GPU로 돌리는 SDF 생성기 번역"
excerpt_separator: "<!--more-->"
categories:
  - graphics
  - rendering
tags:
  - Unity
  - SDF
  - compute-shader
  - Houdini
  - technical-art
---

이 글은 원문 저작권자의 요청이나 삭제 요청이 있을 경우 언제든지 삭제될 수 있습니다.

`【技术美术】unity 工具记录 - 写个GPU上运行的SDF生成器` 글을, 원문 흐름을 최대한 유지하면서 자연스럽게 번역한다.

작성자는 최근 `Compute shader`로 Unity용 `SDF` 생성기를 만들었고, 이 글에서 `SDF` 생성 알고리즘을 간단히 되짚은 뒤 핵심 코드를 기록한다고 설명한다. 글의 출발점은 실무 활용 예시다. Houdini에서 만든 연소, 용해, 성장 같은 surface 변화 효과를 게임 엔진으로 가져오고 싶을 때, 흑백 mask만으로는 부족하고 그 변화를 더 부드럽게 제어할 수 있는 `SDF` texture가 필요해진다는 것이다.

예시로는 Houdini의 `pyrosourcespread` 노드로 만든 burn 효과를 든다. 각 frame의 흑백 mask를 뽑아 두고, 그것을 Unity 툴로 `SDF`와 gradient texture로 변환해 엔진 쪽 dissolve 표현에 활용하는 흐름이다.

![원문 이미지](https://pic1.zhimg.com/v2-09763168a0822ec2e081aa67b55b6574_b.jpg)

원문 이미지 링크: <https://pic1.zhimg.com/v2-09763168a0822ec2e081aa67b55b6574_b.jpg>

<!--more-->

## 번역

### SDF가 여기서 어떤 역할을 하는가

글은 먼저 2D 이미지의 `SDF`를 짧게 설명한다. 각 pixel은 가장 가까운 반대 색 pixel까지의 거리를 기록한다. 예를 들어 검은 영역에서는 가장 가까운 흰 pixel까지의 거리를 양수로 저장하고, 흰 영역에서는 가장 가까운 검은 pixel까지의 거리를 음수로 저장하는 식이다.

이렇게 만들어진 `SDF`는 단순 mask보다 훨씬 다루기 좋다. dissolve나 burn처럼 경계가 시간이 지나며 움직이는 효과를 만들 때, threshold를 움직이는 것만으로도 더 부드럽고 연속적인 변형을 만들 수 있기 때문이다.

![원문 이미지](https://pic3.zhimg.com/v2-85281feb5e66fa7590ab67a09b94f20e_1440w.jpg)

원문 이미지 링크: <https://pic3.zhimg.com/v2-85281feb5e66fa7590ab67a09b94f20e_1440w.jpg>

### 어떤 알고리즘을 검토했고 왜 Saito를 골랐는가

작성자는 `SDF` 생성 방법으로 세 가지를 언급한다.

- brute force
- `Saito`
- `8ssedt`

이 글에서는 뒤의 두 방법 원리를 간단히 복기한다.

`Saito` 방식은 먼저 가로 방향 최소 거리 제곱 맵을 만든 뒤, 각 column을 다시 평가해 최종 최소 거리를 구하는 식으로 설명된다. 원문에서는 특정 pixel을 예로 들며, 왼쪽과 오른쪽 중 더 가까운 반대 색 pixel까지의 거리 제곱을 먼저 기록하고, 이후 세로 방향으로 다시 최소값을 고르는 흐름을 보여 준다.

`8ssedt`는 장애물을 0, 배경을 무한대로 두고, 첫 pass에서 좌상단 이웃 네 점을, 두 번째 pass에서 우하단 이웃 네 점을 참조하며 값을 전파시키는 방식이다. 이쪽은 `O(N)`으로 끝나지만 pass 간 순차 의존성이 강해서, 이전 pass 결과가 다음 pass의 기반이 된다.

결론은 분명하다. `8ssedt`는 CPU식 순차 전파에는 강하지만, GPU 병렬 계산에는 `Saito`가 더 잘 맞는다. 그래서 작성자는 `Compute shader`로 돌리기 위해 `Saito`를 선택했다고 적는다.

![원문 이미지](https://pic3.zhimg.com/v2-f8e5e91f95ab31987d74aa563aeb7e3c_1440w.jpg)

원문 이미지 링크: <https://pic3.zhimg.com/v2-f8e5e91f95ab31987d74aa563aeb7e3c_1440w.jpg>

![원문 이미지](https://pica.zhimg.com/v2-e1f4ddb2c9431e9203b2ce821f094afe_1440w.jpg)

원문 이미지 링크: <https://pica.zhimg.com/v2-e1f4ddb2c9431e9203b2ce821f094afe_1440w.jpg>

### 여러 frame의 SDF를 gradient texture로 바꾸는 방법

이 글의 실무 포인트는 단일 `SDF` 생성보다도, 여러 frame에서 얻은 `SDF`를 하나의 gradient texture로 합치는 부분이다.

작성자는 먼저 frame별 `SDF`를 여러 장 가지고 있다고 가정한다. 예를 들어 1 frame의 `sdf1`, 5 frame의 `sdf5`가 있으면, 그 사이의 중간 frame은 두 `SDF`를 선형 보간해서 만든다. 이렇게 충분히 촘촘한 간격으로 `SDF`를 준비한 뒤, 각 `SDF`를 `step` 처리해 흑백 mask로 바꾸고, mask의 흰 영역이 출력 gradient texture에서 밝기 1단계를 차지하도록 누적해 나간다.

즉, 시간에 따라 퍼져 나가는 mask를 frame별 `SDF`로 다시 표현하고, 그 사이를 보간해 연속적인 grayscale progression을 만든다는 뜻이다.

![원문 이미지](https://pic4.zhimg.com/v2-03db23d3ca08d1cb6e3e699bfb1041e5_1440w.jpg)

원문 이미지 링크: <https://pic4.zhimg.com/v2-03db23d3ca08d1cb6e3e699bfb1041e5_1440w.jpg>

### Compute shader 구현에서 실제로 한 일

후반부는 `Compute shader` 쪽 구현 기록이다. 작성자는 각 이미지 파일 이름 끝부분에 frame 번호를 두는 규칙부터 정한다. 예를 들어 `Substance_graph_output_SDF_177`이면 177번째 frame의 `SDF`라는 식이다.

그 뒤 목표 밝기 단계 수와 보유한 `SDF` 장수 사이를 매핑한다. 원문 예시에서는 `SDF`가 180장 있고, 이를 255단계 밝기로 보간하고 싶다고 설명한다. 그러면 각 단계가 참조해야 하는 interpolation 위치는 `w = 180 / 255`가 된다.

이제 각 단계는 가장 가까운 두 장의 `SDF`를 골라 보간한다.

- `w`는 `sdf0`과 `sdf1` 사이
- `2w`는 `sdf1`과 `sdf2` 사이
- 만약 5 frame 간격으로만 `SDF`가 있다면, 같은 방식으로 `sdf1`과 `sdf5` 사이를 보간

즉, 전체 핵심은 frame index를 texture sequence 위의 연속 좌표로 바꾸고, 매 출력 단계가 그 주변 두 `SDF`를 선형 보간하도록 만드는 것이다.

### 이 글에서 배울 수 있는 점

이 글은 거대한 이론 정리보다는, 실무에서 `Houdini -> mask sequence -> SDF sequence -> Unity gradient texture`로 이어지는 파이프라인을 어떻게 묶는지 보여 주는 기록에 가깝다.

핵심은 세 가지다.

- `SDF`를 써서 단순 mask보다 더 부드러운 시간 변화 데이터를 만든다.
- GPU 병렬화에 맞춰 `Saito` 기반 거리 변환을 선택한다.
- 여러 frame의 `SDF`를 선형 보간해 더 촘촘한 gradient progression texture를 만든다.

![원문 이미지](https://pic3.zhimg.com/v2-701bef00d52647e21262f16e75425322_1440w.jpg)

원문 이미지 링크: <https://pic3.zhimg.com/v2-701bef00d52647e21262f16e75425322_1440w.jpg>

## 참조

- 원문: <https://zhuanlan.zhihu.com/p/702637242>
- 관련 링크: <https://github.com/FengLvv/VATTest/tree/main/Assets/Editor>
- 관련 링크: <https://zhuanlan.zhihu.com/p/703044996>
- 관련 링크: <https://acko.net/blog/subpixel-distance-transform/>
- 관련 링크: <https://blog.csdn.net/tianwaifeimao/article/details/45078661>
- 원문 이미지: <https://pic1.zhimg.com/v2-09763168a0822ec2e081aa67b55b6574_b.jpg>
- 원문 이미지: <https://pic3.zhimg.com/v2-85281feb5e66fa7590ab67a09b94f20e_1440w.jpg>
- 원문 이미지: <https://pic3.zhimg.com/v2-f8e5e91f95ab31987d74aa563aeb7e3c_1440w.jpg>
- 원문 이미지: <https://pica.zhimg.com/v2-e1f4ddb2c9431e9203b2ce821f094afe_1440w.jpg>
- 원문 이미지: <https://pic4.zhimg.com/v2-03db23d3ca08d1cb6e3e699bfb1041e5_1440w.jpg>
- 원문 이미지: <https://pic3.zhimg.com/v2-701bef00d52647e21262f16e75425322_1440w.jpg>

## 용어 정리

- SDF: Signed Distance Field의 약자로, 어떤 점이 경계에서 얼마나 떨어져 있는지를 부호와 함께 저장하는 데이터다.
- mask: 흑백으로 영역을 구분하는 이미지다. 효과가 적용될 범위를 표현할 때 자주 쓴다.
- gradient texture: 밝기 변화가 연속적으로 담긴 texture다. dissolve 진행률 같은 값을 저장하는 데 쓰기 좋다.
- brute force: 가능한 모든 후보를 전부 검사해 답을 찾는 단순한 방식이다.
- Saito: 거리 변환을 가로와 세로 단계로 나눠 계산하는 방식으로, GPU 병렬화에 더 잘 맞는 편이다.
- 8ssedt: 주변 이웃 값을 순차적으로 전파시키는 EDT 계열 알고리즘이다.
- Compute shader: 그래픽스 파이프라인 밖에서 GPU 병렬 연산을 수행하는 shader다.
- interpolation: 두 값 사이의 중간 값을 계산하는 과정이다.
