---
title: "GDC2025 : Generalized Stylized Post Processing Outline 번역 정리"
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

`GDC2025 : Generalized Stylized Post Processing Outline` 글을, 원문 흐름을 최대한 유지하면서 자연스럽게 옮겨 정리한다.

작성자는 이 글이 지난달 GDC에서 발표한 `《通用风格化后处理描边方案》`의 후속 정리라고 설명한다. 원문은 전체 발표 중에서도 미술 파트보다 알고리즘 파트, 그중에서도 `遮挡检测`과 `TAA`를 결합한 중간 `denoising` 단계를 자세히 다룬다. 원고는 원래 영어였고, 글에는 영어 문장과 중국어 번역이 함께 섞여 있다.

가장 먼저 보여주는 핵심 메시지는 단순하다. post-processing outline에서 `denoising`은 단순한 anti-flicker가 아니라, 많은 경우 outline shape 자체를 유지하는 데 필수적이라는 점이다.

![원문 이미지](https://pic3.zhimg.com/v2-345a019bde0ea9f813d161ca5e32c0de_b.jpg)

원문 이미지 링크: <https://pic3.zhimg.com/v2-345a019bde0ea9f813d161ca5e32c0de_b.jpg>

<!--more-->

작성자는 이번 outline 알고리즘이 완전히 post-processing 기반이며, 크게 세 부분으로 이루어진다고 설명한다. 이 글은 그중 가운데 단계인 `denoising`에 집중한다.

## 번역 정리

### 왜 flickering과 aliasing이 생기는가

글은 `Nyquist–Shannon sampling theorem`부터 출발한다. aliasing을 피하려면 sample rate가 신호 대역폭의 두 배 이상이어야 한다. 실시간 렌더링에서는 보통 temporal accumulation으로 sample rate를 높이지만, 이 누적이 실패하는 상황에서는 flickering과 aliasing이 나타난다.

원문은 대표적인 두 상황을 든다.

첫 번째는 geometry가 너무 얇을 때다.

- object width가 1 pixel보다 작아진다.
- subpixel 일부만 덮게 된다.
- outline된 cylinder 같은 예시에서 화면 오른쪽에 flickering이 생긴다.

두 번째는 stroke가 너무 촘촘할 때다.

- stroke spacing이 1 pixel보다 작아진다.
- outlined prism 같은 예시에서 선 간격이 subpixel 수준까지 줄어든다.
- 결과적으로 매우 심한 flickering이 발생한다.

즉, 문제의 본질은 outline가 너무 높은 주파수 정보를 가진다는 데 있다.

![원문 이미지](https://pic2.zhimg.com/v2-8657b012ec587deed190ce1487bc63c1_1440w.jpg)

원문 이미지 링크: <https://pic2.zhimg.com/v2-8657b012ec587deed190ce1487bc63c1_1440w.jpg>

### 왜 temporal denoiser가 이 문제를 잘 못 푸는가

이어서 글은 기본적인 `TAA` 흐름을 설명한다.

1. 이전 frame reprojection
2. validation
3. 현재 frame과 blend

여기서 품질을 결정하는 핵심은 `validation`이다. 오래된 history에서 오류를 얼마나 정확하게 제거하느냐가 중요하다. `DLSS`, `XeSS`, `FSR`, `TSR` 같은 고급 기법도 결국 validation에 더 많은 비중을 두지만, 작성자는 이들이 outline denoising에 그대로 적용되기는 어렵다고 본다.

가장 흔한 validation은 `Clamp-History` 계열인데, outline처럼 edge detection 빈도가 지나치게 높은 경우에는 두 가지 문제가 생긴다.

- flickering
- non-convergence

고밀도 outline 상황에서는 전통적인 TAA가 안정성을 보장하지 못한다. 또 object width가 너무 작으면 `Clamp-History`가 주기적으로 색을 배경 쪽으로 잘라 버려, 아예 올바른 값으로 수렴하지 못한다.

작성자는 이 지점에서 `TSR`이 상대적으로 잘 버틴다고 말한다. 이유는:

- history color resolution이 더 높고
- per-pixel accumulated weight를 기록해 clamp의 부작용을 줄이기 때문

다만 비용이 크고, 여전히 충분히 만족스럽지는 않다고 본다.

### ray tracing denoising과의 연결

글에서 가장 흥미로운 부분은 `TAA jitter`와 `ray tracing denoising`을 같은 샘플링 문제로 바라본다는 점이다.

- ray traced hit result도 고주파 정보의 한 sample이고
- jitter된 subpixel도 고주파 정보의 한 sample이다

그래서 ray tracing denoiser에서 흔히 쓰는 다음 개념들이 outline denoising에도 시사점을 준다고 설명한다.

- 큰 clamp range
- 여러 번의 spatial blur pass
- clamp에만 의존하지 않는 history validation

또 실시간 렌더링 데이터를 두 종류로 나눈다.

- geometry 정보만 필요로 하는 데이터
- lighting이나 world space 정보가 필요한 데이터

outline는 전자에 속한다. depth, normal, BaseColor처럼 `GBuffer` 수준의 geometry 정보만 필요하다면, 굳이 까다로운 clamp를 쓸 필요가 없다는 것이 글의 핵심 주장 중 하나다.

### 핵심 해법 1: Disocclusion Detection

작성자는 여기서 `Clamp-History`를 버리고 `Disocclusion Detection` 중심의 history validation으로 넘어간다.

기본 아이디어는 다음과 같다.

- 현재 frame에서 새로 드러난 pixel은 history를 쓰지 않는다.
- 이를 위해 foreground disocclusion과 background disocclusion을 모두 검출한다.

기본 절차는:

1. 이전 frame depth를 가져온다.
2. 현재 frame 공간으로 reprojection한다.
3. 현재 depth와 비교해 disocclusion 영역을 찾는다.

그런데 이 기본 알고리즘만으로는 세 가지 문제가 남는다.

- foreground depth difference가 너무 작아 ghosting이 생긴다
- background ghosting이 피할 수 없이 생긴다
- tangent edge에서 jitter 때문에 edge flickering이 생긴다

이를 해결하기 위해 글은 몇 가지 장치를 추가한다.

#### depth dilation

먼저 depth buffer를 1 pixel 확장하고, 확장된 pixel을 따로 표시한다. 이 표시는 나중에 회전 물체 edge를 다시 갱신할 때도 사용된다.

#### current depth를 history space로 reprojection

현재 depth를 다시 history 공간으로 reprojection해서 비교 양쪽이 같은 jitter offset을 갖도록 맞춘다.

#### Use-Count Texture

`TSR`에서 영감을 받은 `Use-Count Texture`도 쓴다. 다만 사용법은 조금 다르다.

- reprojection 동안 각 pixel이 몇 번 쓰였는지 기록
- 정적인 장면에서는 한 번만 쓰인 pixel은 disocclusion이 없다고 볼 수 있음

이걸 통해 moving edge처럼 계속 갱신이 필요한 위치를 더 정확하게 분리한다.

작성자는 이 구성이 세 가지 문제를 해결한다고 정리한다.

- foreground ghosting 완화
- background ghosting 완화
- edge flickering 완화

그리고 전통적인 single-pass 방식과 비교한 결과, camera rotation, foreground motion, camera translation 세 경우 모두에서 더 정확한 mask를 만든다고 설명한다.

![원문 이미지](https://pic4.zhimg.com/v2-288afc26e8c2eb059bcf227fa222e305_1440w.jpg)

원문 이미지 링크: <https://pic4.zhimg.com/v2-288afc26e8c2eb059bcf227fa222e305_1440w.jpg>

### 핵심 해법 2: Rotation Detection

하지만 여기서 새 문제가 생긴다. edge flickering을 잡기 위해 현재 frame depth reprojection을 history depth처럼 쓰면, object가 빠르게 회전할 때 reprojection error가 커진다.

즉:

- object가 camera 기준으로 빠르게 회전한다
- reprojection으로 얻은 과거 frame 정보와 실제 과거 frame 정보가 크게 달라진다
- ghosting이 다시 심해진다

작성자는 이 차이를 오히려 이용한다. reprojection으로 얻은 history depth와 실제 history depth 사이의 큰 차이를 `rotation detection` 신호로 사용한다.

핵심은:

- 전통적인 disocclusion detection이 실패하는 영역을
- 두 종류의 historical depth 비교로 보완하는 것

이렇게 하면 회전 때문에 생기는 history 오염을 더 많이 제거할 수 있다.

다만 rotation detection의 우선순위를 높이면 다시 edge flickering 문제가 돌아온다. 글은 이를 `depth dilation marks`로 edge를 찾아 매 frame 갱신하는 식으로 해결했다고 설명한다.

즉, 회전 object의 edge는 항상 refresh해야 한다는 것이다. 그래야 outline가 선명하게 유지된다.

### 마지막 단계: Final Blend

마지막 단계는 final blend다. 작성자는 이것이 denoising의 마지막 pass라고 말한다.

여기서는 blend 전에 현재 frame 결과를 interpolation해서, aliasing이 심한 각도에서도 선의 시각적 두께가 비교적 일정하게 보이도록 만든다. 일종의 outline 전용 anti-aliasing에 가깝다.

또 `Moments Texture`를 써서 convergence speed를 높인다.

- 기본 TAA보다 수렴 속도가 더 빠르다
- 이 알고리즘은 clamp를 아예 쓰지 않기 때문에 결국 기대값으로 수렴한다

마지막으로 사람 눈은 pixel-level flickering보다 brightness 변화에 더 민감하다는 점을 이용해, temporal blending weight도 따로 조정한다. 이를 통해 convergence speed를 높이면서도 밝기 변화가 덜 거슬리게 만든다.

최종 비교에서 작성자는 이렇게 요약한다.

- `DLSS`는 outline 품질에서 `TSR`에 매우 가까움
- `FSR`은 가장 많이 흔들림
- 일반 `TAA`는 가장 흐릿함

![원문 이미지](https://pic1.zhimg.com/v2-a5f2d642c47d0a053cb5ca1b87be4d56_1440w.jpg)

원문 이미지 링크: <https://pic1.zhimg.com/v2-a5f2d642c47d0a053cb5ca1b87be4d56_1440w.jpg>

## 보충 해설

이 글에서 가장 중요한 포인트는 outline 문제를 단순 edge detect나 single-frame filter로 보지 않는다는 점이다. 작성자는 outline 자체를 고주파 신호로 보고, `sampling`, `history validation`, `denoising`, `convergence` 문제로 재해석한다.

또 `Clamp-History`를 버리고 geometry 정보만으로 더 직접적인 validation을 구성한 점이 인상적이다. lighting 정보가 필요 없는 outline라면, 오히려 ray tracing denoiser 쪽의 사고방식이 더 잘 맞는다는 주장도 꽤 설득력 있다.

정리하면 이 글은 `GBuffer 기반 post-processing outline`에 `Disocclusion Detection`, `Use-Count Texture`, `Rotation Detection`, `Moments Texture`를 결합해서 flickering, ghosting, non-convergence를 동시에 줄이는 방향을 제안한 글이다.

## 참조

- 원문: <https://zhuanlan.zhihu.com/p/1895785690161198348>
- 관련 링크: <https://schedule.gdconf.com/session/generalized-stylized-post-processing-outline-scheme/911861>
- 원문 이미지: <https://pic3.zhimg.com/v2-345a019bde0ea9f813d161ca5e32c0de_b.jpg>
- 원문 이미지: <https://pic2.zhimg.com/v2-8657b012ec587deed190ce1487bc63c1_1440w.jpg>
- 원문 이미지: <https://pic4.zhimg.com/v2-288afc26e8c2eb059bcf227fa222e305_1440w.jpg>
- 원문 이미지: <https://pic1.zhimg.com/v2-a5f2d642c47d0a053cb5ca1b87be4d56_1440w.jpg>

## 용어 정리

- Nyquist–Shannon sampling theorem: 신호를 깨지지 않게 복원하려면 충분한 샘플 수가 필요하다는 이론이다.
- aliasing: 샘플 수가 부족해서 계단 현상이나 깜빡임처럼 잘못 보이는 현상이다.
- temporal accumulation: 여러 frame 정보를 쌓아서 더 많은 sample을 얻는 방식이다.
- Clamp-History: history 색을 이웃한 현재 frame 범위 안으로 강제로 제한하는 TAA 계열 검증 방식이다.
- disocclusion: 이전 frame에서는 가려졌지만 현재 frame에서는 새로 드러난 영역이다.
- ghosting: 과거 frame 정보가 잘못 남아 잔상처럼 보이는 현상이다.
- depth dilation: depth buffer를 주변 pixel로 확장해 경계 정보를 더 두껍게 잡는 처리다.
- Use-Count Texture: 어떤 pixel이 reprojection 과정에서 몇 번 쓰였는지 기록하는 버퍼다.
- Moments Texture: 누적 통계량을 저장해 temporal convergence를 더 빠르고 안정적으로 만드는 버퍼다.
