---
title: "Unity URP로 구현한 종말지 캐릭터 Toon Rendering 번역"
excerpt_separator: "<!--more-->"
categories:
  - graphics
  - rendering
tags:
  - Unity
  - URP
  - toon-rendering
  - NPR
  - character-shading
---

이 글은 원문 저작권자의 요청이나 삭제 요청이 있을 경우 언제든지 삭제될 수 있습니다.

`【unity urp】从零模仿复刻实现自己的终末地人物卡通渲染` 글을, 원문 흐름을 최대한 유지하면서 자연스럽게 번역한다.

작성자는 이전 카드렌더링 글 이후 한동안 다른 연구 때문에 글을 쉬었다가, 이번에는 `终末地` 스타일의 캐릭터 rendering을 `Unity URP`에서 직접 복각한 과정을 설명한다. 목표는 단순 아이디어 소개가 아니라, 처음부터 따라가면 비슷한 결과를 직접 만들 수 있을 정도로 전체 구현을 설명하는 것이다.

이 글의 방향은 분명하다. 미호요식 강한 cel 스타일에서 조금 더 `PBR`과 결합된 toon rendering으로 넘어가며, `终末地`가 어떤 식으로 사실적인 광 분포와 stylized trick을 섞는지 분석한다. 작성자는 완전한 원본 재현은 아니라고 선을 그으면서도, 실제 게임 shader를 역으로 추적해 최대한 가깝게 복각한 흐름을 단계별로 설명한다.

![원문 이미지](https://pic3.zhimg.com/v2-3ed80f466107a1779e592c76780a5d04_b.jpg)

원문 이미지 링크: <https://pic3.zhimg.com/v2-3ed80f466107a1779e592c76780a5d04_b.jpg>

<!--more-->

## 번역

### 먼저 준비해야 하는 texture와 모델 데이터

글은 구현 전에 반드시 확보해야 하는 리소스부터 설명한다. `toon base shader`에는 기본적으로 `albedo`, `normal`, material property texture가 필요하다. 이 property map에는 `metallic`, `reflectivity`, `ao`, `smoothness` 같은 값이 들어 있고, `albedo`의 alpha 채널은 cutout이나 semi-transparent material 구현에 연결된다.

또 부위별 `ramp` texture가 따로 존재한다. 옷, 피부, 얼굴, 머리카락, 털 재질이 각자 다른 ramp를 쓰며, 이 ramp의 `rgb`는 색 매핑, `alpha`는 `NoL` 재매핑에 사용된다고 설명한다. 여기에 emissive texture, 환경용 cubemap, preintegrated specular color mapping texture, 피부용 `lut`, 얼굴용 `sdf` texture와 제한 mask, 눈용 `matcap`, 그리고 모델의 `uv`에 저장된 smooth normal까지 필요하다.

즉, 이 셰이더는 단순히 한 장의 albedo와 normal로 끝나는 구조가 아니라, 부위별 보조 texture를 많이 활용하는 asset-driven 파이프라인이라는 뜻이다.

![원문 이미지](https://pic1.zhimg.com/v2-665f21080045352c347dfb2c3b3f3336_1440w.jpg)

원문 이미지 링크: <https://pic1.zhimg.com/v2-665f21080045352c347dfb2c3b3f3336_1440w.jpg>

### 가장 중요한 전제: `직사광 강도`

작성자가 가장 먼저 강조하는 핵심은 단순히 main directional light intensity만 올리고 내리는 것으로는 게임 안의 조명 변화를 설명하기 어렵다는 점이다. 캐릭터가 벽 근처나 복잡한 환경광 아래에 있을 때는, 단순히 태양광이 약해진 것보다 더 큰 차이가 생긴다.

그래서 글은 `日光直射强度`라는 상태값을 따로 둔다. 이 값은 “지금 캐릭터가 태양 직사광의 직접 영향을 얼마나 받는가”를 나타내며, 이후 거의 모든 shading 로직이 이 값을 기준으로 두 상태를 오간다.

- 값이 1에 가까우면 직사광 중심 상태
- 값이 0에 가까우면 태양 영향이 거의 사라진 상태

이 상태 전환 덕분에 단순 intensity fade가 아니라, rim light, diffuse layering, highlight direction까지 함께 바뀌게 만들 수 있다.

### 광원 설계: mainLight 외에 top light를 하나 더 둔다

이 구현에서 흥미로운 부분은 캐릭터 머리 위에 별도의 top light를 둔다는 점이다. 글에서는 태양광을 `mainLight`, 캐릭터를 위에서 보정해 주는 주관적 보조광을 `otherLight`로 구분한다.

이 `otherLight`는 물리적으로 자연스러운 광원이라기보다, 캐릭터를 더 입체적이고 보기 좋게 만들기 위한 artist-friendly light에 가깝다. `NoL`도 그대로 쓰지 않고, 좀 더 부드러운 분포가 되도록 수동으로 remap한다.

그리고 `日光直射强度`가 낮아질수록:

- `mainLight` 영향은 약해지거나 사라지고
- `otherLight`는 상대적으로 커져서 캐릭터가 완전히 죽지 않게 유지된다

즉, 이 캐릭터 셰이더는 “현실의 조명 재현”보다 “상황별로 캐릭터가 예쁘게 보이는 조명 상태 전이”를 더 중요하게 둔다.

![원문 이미지](https://pic3.zhimg.com/v2-d2d22f3b8ecf5c21febaf8f6fa9127e8_1440w.jpg)

원문 이미지 링크: <https://pic3.zhimg.com/v2-d2d22f3b8ecf5c21febaf8f6fa9127e8_1440w.jpg>

### diffuse는 세 단계 색 분리 + ramp 보정으로 만든다

글에 따르면 `终末地`의 diffuse는 전형적인 단일 ramp toon이 아니라, 물리적인 빛 분포 위에 stylized 색 분리를 얹는 방식이다.

먼저 세 가지 색을 만든다.

- 밝은 영역
- 어두운 영역
- 더 어두운 영역

밝은 영역은 기본 `albedo`에 가깝고, 어두운 영역은 강도와 saturation을 줄인 색, 더 어두운 영역은 그보다 한 번 더 눌린 색으로 만든다. 그런 다음 `NoL`, `ao`, `shadow`, `NoF` 같은 항을 조합해서 이 세 층의 경계를 만든다.

여기서 중요한 점은, ramp가 주인공이 아니라는 것이다. 주된 명암 구조는 물리적인 광 분포에서 오고, ramp는 그 결과 위에 subtle한 색 변화를 더하는 보조 역할에 가깝다. 작성자는 이것이 다른 anime 스타일 toon보다 더 사실적이고 범용적인 방향이라고 해석한다.

또 이 ramp에는 backlight compensation도 들어간다. 캐릭터가 완전히 역광일 때 얼굴과 몸이 너무 쉽게 죽지 않도록, 카메라 방향과 광원 방향을 비교해서 stylized backlight 보정을 넣는다.

### specular는 물리 기반을 유지하되 방향을 과감히 바꾼다

specular 쪽은 더 흥미롭다. `终末地`는 specular BRDF 자체를 완전히 버리지는 않지만, `NoH`를 만드는 light direction 쪽에 큰 stylization을 넣는다.

글에 따르면 고광 계산에서는 일반적인 main light direction 대신, 카메라에서 캐릭터 쪽으로 들어오는 듯한 virtual light direction을 섞는다. 그리고 이 방향 혼합 비율도 `日光直射强度`에 의해 바뀐다.

결과적으로:

- 직사광이 강할 때는 main light 쪽 성향이 좀 더 남고
- 직사광이 약할 때는 camera-forward 성향이 강해져서, top light 상황에서도 더 자연스럽고 anime스럽게 보이는 highlight가 나온다

작성자는 이것이 엄밀한 물리라기보다, 직관적으로 “보기 좋은 specular”를 만드는 trick이라고 설명한다.

### rim light는 두 종류를 섞는다

rim light는 한 가지가 아니다.

첫 번째는 전형적인 `1 - NoV` 기반의 Fresnel rim이다. 범위는 `smoothstep`으로 제어하고, 필요하면 원래 diffuse color 영향을 섞는다.

두 번째는 광원 방향에 영향을 받는 anime식 rim이다. 여기서는 `mainLight`의 `xz` 성분만 써서, 인물을 원통처럼 바라보는 방식으로 rim 분포를 만든다. 역시 `日光直射强度`가 바뀌면 이 효과도 약해지거나 사라진다.

즉, rim light도 단순 edge glow가 아니라:

- view-driven rim
- light-aware rim

두 계층을 합쳐서 캐릭터가 평면적으로 죽지 않도록 만드는 구조다.

![원문 이미지](https://pic2.zhimg.com/v2-a4ad733eb2e7363a02d796cbf7dd1425_1440w.jpg)

원문 이미지 링크: <https://pic2.zhimg.com/v2-a4ad733eb2e7363a02d796cbf7dd1425_1440w.jpg>

### 특수 재질은 base shader 위에 variant로 얹는다

base shader를 만든 뒤에는 옷의 금속 장식, semi-transparent 소매, black stocking, skin 같은 특수 부위를 variant로 풀어 간다.

예를 들어 금속 장식은 preintegrated specular color map으로 `F0`를 수정하고, 일부 부위에는 emissive를 더해 미술 원화에 가까운 느낌을 만든다. black stocking은 간단한 `SSS`를 추가하고, transparent 부위는 별도 ramp와 emissive를 조합한다.

즉, base를 잘 만든 뒤에 각 재질은:

- `F0` 보정
- emissive
- `SSS`
- transparency

같은 요소를 필요한 만큼만 덧붙이는 구조다.

### skin은 별도 LUT로 dark color를 만든다

skin은 base shader와 비슷하지만, dark tone을 만드는 방식이 다르다. 일반적인 ramp 대신 skin 전용 `lut`를 사용해 dark-side color를 매핑한다. 작성자는 이 덕분에 피부의 음영 변화가 더 정교해지고, 단순 ramp보다 더 유기적인 결과가 나온다고 본다.

여기에 `SSS`까지 더해서, 피부는 옷보다 훨씬 더 따로 다뤄진다. 이 부분만 봐도 `终末地`가 모든 재질을 동일한 toon rule로 처리하지 않고, material-specific treatment를 꽤 강하게 넣는다는 점이 드러난다.

### face shader는 SDF 기반이다

face shader는 최근 anime face rendering에서 흔히 보이는 `SDF` 기반 설계를 따른다. base shader에서 IBL specular와 일반 rim light는 제거하고, 얼굴 전용 `NoL` 분포를 `SDF` texture에서 만들어 diffuse shading 쪽에 넣는다.

여기서도 단순 SDF 한 장으로 끝나지 않는다.

- 얼굴 `SDF` 자체
- `sss`/rim 범위 제한용 refine texture
- 표정용 4분할 texture

가 함께 쓰인다.

특히 light가 얼굴의 왼쪽에서 오는지 오른쪽에서 오는지에 따라 `SDF` sampling 방향을 바꾸고, `FaceForward`와 `mainLightDir`의 관계를 이용해 부드럽게 밝고 어두운 면을 나눈다. 여기에 backlight compensation, neck blending, 비대칭 rim까지 더해지면서, 얼굴은 몸통과는 완전히 다른 특별 취급을 받는다.

작성자는 이 부분이 구현 난이도도 높고, 최근 anime 얼굴 shader가 왜 대부분 `SDF` 기반으로 가는지 잘 보여 준다고 본다.

![원문 이미지](https://pic1.zhimg.com/v2-9429d1e01da20f78ec1e474a626cdc38_1440w.jpg)

원문 이미지 링크: <https://pic1.zhimg.com/v2-9429d1e01da20f78ec1e474a626cdc38_1440w.jpg>

## 참조

- 원문: <https://zhuanlan.zhihu.com/p/2028819446546932894>
- 관련 링크: <https://github.com/qiudashu233/MyZmdShaders>
- 관련 링크: <https://zhuanlan.zhihu.com/p/31522286649>
- 원문 이미지: <https://pic3.zhimg.com/v2-3ed80f466107a1779e592c76780a5d04_b.jpg>
- 원문 이미지: <https://pic1.zhimg.com/v2-665f21080045352c347dfb2c3b3f3336_1440w.jpg>
- 원문 이미지: <https://pic3.zhimg.com/v2-d2d22f3b8ecf5c21febaf8f6fa9127e8_1440w.jpg>
- 원문 이미지: <https://pic2.zhimg.com/v2-a4ad733eb2e7363a02d796cbf7dd1425_1440w.jpg>
- 원문 이미지: <https://pic1.zhimg.com/v2-9429d1e01da20f78ec1e474a626cdc38_1440w.jpg>

## 용어 정리

- PBR: physically based rendering의 약자다. 물리적으로 그럴듯한 빛 반응을 목표로 하는 shading 방식이다.
- ramp texture: `NoL` 같은 값에 따라 색을 다시 매핑하는 texture다. toon rendering에서 명암과 색감을 stylize할 때 많이 쓴다.
- NoL: normal과 light direction의 내적이다. 표면이 빛을 얼마나 정면으로 받는지 나타낸다.
- NoV: normal과 view direction의 내적이다. 표면이 카메라를 얼마나 정면으로 보는지 나타낸다.
- NoH: normal과 half vector의 내적이다. specular 분포 계산에 자주 쓰인다.
- Fresnel rim: 시선 각도가 얕아질수록 가장자리 밝기가 강해지는 효과다.
- F0: 재질이 정면에서 보일 때의 기본 반사율이다.
- SSS: subsurface scattering의 약자다. 피부나 얇은 재질 안으로 빛이 조금 스며드는 것처럼 보이게 하는 효과다.
- LUT: 미리 계산된 색 변환 표다. 여기서는 피부의 dark color mapping에 사용된다.
- SDF: signed distance field의 약자다. 경계까지의 거리를 저장한 데이터로, 얼굴 명암이나 toon 마스크 제어에 자주 쓰인다.
