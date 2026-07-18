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

또 부위별 `ramp` texture가 따로 존재한다. 옷, 피부와 얼굴, 머리카락, 털 재질이 각자 다른 ramp를 쓰며, 이 ramp의 `rgb`는 색 매핑, `alpha`는 `NoL` 재매핑에 사용된다고 설명한다. 글에서는 미호요나 소녀전선 계열처럼 여러 ramp를 한 장에 합쳐 `id`로 읽지 않고, 부위별 ramp를 따로 쓰는 구성이라고 적는다. 피부와 얼굴은 같은 ramp를, 머리카락은 별도의 ramp를, 털과 의상도 각자 다른 ramp를 사용한다.

여기에 emissive texture, 환경용 cubemap, preintegrated specular color mapping texture, 피부용 `lut`, 얼굴용 `sdf` texture와 제한 mask, 표정 texture, 눈용 `matcap`, 그리고 모델의 `uv`에 저장된 smooth normal까지 필요하다. 작성자는 특히 `albedo`의 `alpha`가 cutout과 반투명 재질 구현에 연결되고, 얼굴 shader에는 `SDF` 이미지와 영역 제한용 이미지, 눈에는 `matcap`, 머리카락에는 고광 색 보정용 texture가 있다는 점을 하나씩 짚는다.

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

글은 여기서 `ramp`의 `alpha`가 `NoL`을 다시 매핑하는 데 쓰인다고 설명한다. 즉, 단순히 `NoL` 값을 바로 쓰는 것이 아니라, ramp가 밝고 어두운 영역의 분포 자체를 조정한다. 여기에 역광 보정까지 더하면, 실제 물리적 분포 위에 stylized 분포를 얹는 구조가 된다.

또 작성자는 밝음-어두움-더 어두움 세 층을 만들 때 `NoL`, `ao`, `shadow`, `NoF`를 서로 다르게 조합한다고 적는다. 밝은 영역과 어두운 영역처럼 차이가 큰 두 층은 `min` 성격의 조합으로 경계를 분명히 하고, 어두운 영역과 더 어두운 영역은 `ao`, `shadow`, `NoF`를 더 적극적으로 섞어 안쪽 음영을 조인다. 이 때문에 `终末地`의 diffuse는 일반적인 anime toon보다 덜 평면적이고, 그림자 안쪽의 입체감도 더 크게 느껴진다.

### specular는 물리 기반을 유지하되 방향을 과감히 바꾼다

specular 쪽은 더 흥미롭다. `终末地`는 specular BRDF 자체를 완전히 버리지는 않지만, `NoH`를 만드는 light direction 쪽에 큰 stylization을 넣는다.

글에 따르면 고광 계산에서는 일반적인 main light direction 대신, 카메라에서 캐릭터 쪽으로 들어오는 듯한 virtual light direction을 섞는다. 그리고 이 방향 혼합 비율도 `日光直射强度`에 의해 바뀐다.

결과적으로:

- 직사광이 강할 때는 main light 쪽 성향이 좀 더 남고
- 직사광이 약할 때는 camera-forward 성향이 강해져서, top light 상황에서도 더 자연스럽고 anime스럽게 보이는 highlight가 나온다

작성자는 이것이 엄밀한 물리라기보다, 직관적으로 “보기 좋은 specular”를 만드는 trick이라고 설명한다.

원문 후반에는 고광 계산에 `albedo`의 `alpha`를 한 번 더 걸어 `SSS` 성격 재질의 diffuse 에너지를 줄이고, 그 위에 근사식으로 `IBL` specular를 더하는 흐름도 적혀 있다. 작성자는 이 수식 출처를 깊게 연구하지는 않았지만, `NVIDIA NRD` 쪽 근사와 `Kulla-Conty` 계열 보정을 참고한 것으로 보인다고 적는다. 여기서는 완전한 물리 복원보다, 원본 게임의 화면 인상을 재현하는 것이 목표이기 때문에, 식의 해석보다는 결과 재현에 무게를 둔다.

### rim light는 두 종류를 섞는다

rim light는 한 가지가 아니다.

첫 번째는 전형적인 `1 - NoV` 기반의 Fresnel rim이다. 범위는 `smoothstep`으로 제어하고, 필요하면 원래 diffuse color 영향을 섞는다.

두 번째는 광원 방향에 영향을 받는 anime식 rim이다. 여기서는 `mainLight`의 `xz` 성분만 써서, 인물을 원통처럼 바라보는 방식으로 rim 분포를 만든다. 역시 `日光直射强度`가 바뀌면 이 효과도 약해지거나 사라진다.

즉, rim light도 단순 edge glow가 아니라:

- view-driven rim
- light-aware rim

두 계층을 합쳐서 캐릭터가 평면적으로 죽지 않도록 만드는 구조다.

원문은 특히 두 번째 rim에서 `NoL`의 `y` 성분보다 `xz` 평면 분포를 더 중시한다고 설명한다. 인물을 원통처럼 보고 옆 가장자리를 더 강조하는 쪽이다. 다시 말해, 실제 광원이 위에 있든 옆에 있든 상관없이, 캐릭터의 silhouette가 anime 원화처럼 정리되도록 light-aware rim을 의도적으로 설계한다.

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

글에서는 금속 장식 쪽에 `_SPECULARREFINE_ON` 같은 variant를 두고, color mapping texture로 `F0`를 다시 정하고, emissive를 추가해 장난감이나 리본 같은 특정 부위의 미술 느낌을 맞춘다고 설명한다. black stocking은 `1 - NoV` 기반의 간단한 `SSS`를 추가하고, transparent 부위는 별도 ramp와 emissive를 이용해 게임 안의 반투명 재질에 가깝게 만든다.

### skin은 별도 LUT로 dark color를 만든다

skin은 base shader와 비슷하지만, dark tone을 만드는 방식이 다르다. 일반적인 ramp 대신 skin 전용 `lut`를 사용해 dark-side color를 매핑한다. 작성자는 이 덕분에 피부의 음영 변화가 더 정교해지고, 단순 ramp보다 더 유기적인 결과가 나온다고 본다.

여기에 `SSS`까지 더해서, 피부는 옷보다 훨씬 더 따로 다뤄진다. 이 부분만 봐도 `终末地`가 모든 재질을 동일한 toon rule로 처리하지 않고, material-specific treatment를 꽤 강하게 넣는다는 점이 드러난다.

작성자는 피부에서 일반 ramp보다 `LUT`가 더 직접적인 dark-color hash table처럼 작동한다고 설명한다. 즉, ramp처럼 분포를 살짝 틀어 주는 수준이 아니라, 피부의 어두운 쪽 색 자체를 다른 색으로 바꿔 버리는 식이다. 그래서 피부의 그림자색이 옷보다 훨씬 풍부하게 느껴진다.

### face shader는 SDF 기반이다

face shader는 최근 anime face rendering에서 흔히 보이는 `SDF` 기반 설계를 따른다. base shader에서 IBL specular와 일반 rim light는 제거하고, 얼굴 전용 `NoL` 분포를 `SDF` texture에서 만들어 diffuse shading 쪽에 넣는다.

여기서도 단순 SDF 한 장으로 끝나지 않는다.

- 얼굴 `SDF` 자체
- `sss`/rim 범위 제한용 refine texture
- 표정용 4분할 texture

가 함께 쓰인다.

특히 light가 얼굴의 왼쪽에서 오는지 오른쪽에서 오는지에 따라 `SDF` sampling 방향을 바꾸고, `FaceForward`와 `mainLightDir`의 관계를 이용해 부드럽게 밝고 어두운 면을 나눈다. 여기에 backlight compensation, neck blending, 비대칭 rim까지 더해지면서, 얼굴은 몸통과는 완전히 다른 특별 취급을 받는다.

작성자는 이 부분이 구현 난이도도 높고, 최근 anime 얼굴 shader가 왜 대부분 `SDF` 기반으로 가는지 잘 보여 준다고 본다.

원문은 얼굴 `SSS`도 단순 `1 - NoV`로는 안 되고, refine texture의 특정 채널로 제한해야 얼굴의 특정 부위만 부드럽게 밝아진다고 설명한다. 표정 texture는 4분할 구조로 저장되어 있고, 별도의 sampling 로직으로 현재 표정을 읽어 `albedo`에 합친다. 얼굴 그림자 `SDF`는 얼굴의 좌우 방향을 판단해 uv를 뒤집거나 유지하고, `FaceForward`와 `mainLightDir`의 관계에서 나온 값을 `smoothstep`의 범위로 써서 경계가 부드럽게 움직이게 만든다.

또 목과 얼굴의 접합부는 refine texture의 마스크를 이용해 `SDF` 기반 얼굴 `NoL`과 목 skin shader의 `NoL`을 섞는다. 이 작업을 하지 않으면 얼굴과 목 사이에 눈에 띄는 틈이 생긴다고 적는다. 얼굴 rim도 일반적인 `1 - NoV`만으로는 원하는 모양이 안 나오기 때문에, 특수한 normal과 refine texture의 `w` 채널을 이용해 비대칭적으로 만든다.

### eye shader는 특수 normal과 matcap을 사용한다

원문 후반부에서는 eye shader를 따로 다룬다. 여기서는 base shader를 그대로 복사하는 것이 아니라, 눈알의 uv를 이용해 특수 normal을 만든다. 작성자는 이 normal이 uv를 2D 함수장처럼 보고 gradient를 뽑아낸 결과처럼 동작한다고 설명한다. eye의 uv는 중심이 동공 중앙에 오도록 잡혀 있어서, 이 방식으로 아주 부드러운 눈용 normal을 만들 수 있다.

이 특수 normal은 diffuse에서 쓰이고, highlight는 `matcap`으로 구현한다. view space normal의 `xy`를 이용해 `matcap`을 샘플하고, `matcap`의 `alpha`로 highlight mask를 받아 영역을 제어한다. 여기에 `日光直射强度`, `ao`, `shadow`를 다시 걸어 최종 eye highlight를 만든다.

또 눈의 밝은 중심 영역과 `mainTex`의 특정 채널을 별도 마스크로 써서 색 보정을 넣는다고 적는다. 즉, 눈은 얼굴 전체 셰이더의 일부가 아니라, 다시 별도의 stylized shader 체계로 다룬다.

### hair shader는 별도 smooth normal과 Kajiya-Kay 기반 고광을 쓴다

머리카락은 또 다른 특수 케이스다. 글에서는 머리카락의 고광이 매우 정렬된 anime 하이라이트처럼 보이기 때문에, diffuse용 모델 normal과는 별도로 highlight용 smooth normal이 필요하다고 설명한다.

원래는 hair normal map의 `zw` 채널을 이용해 평활 normal을 만든다고 분석했지만, 작성자는 자신이 완전히 같은 결과를 얻지 못했다고 적는다. 그래서 실제 복각에서는 중심점을 하나 정해 구형 normal에 가까운 결과로 대체했다. 원문은 이것이 완전한 해법이 아니며, 제대로 하려면 hair 전용 smooth normal을 별도로 설계해야 한다고 분명히 말한다.

고광 분포는 `Kajiya-Kay Shading` 계열을 따른다. 머리카락을 원기둥 다발처럼 보고, 발丝 방향 tangent와 `H`의 관계로 highlight를 만든다. 여기서 tangent는 Unity가 주는 tangent를 그대로 쓰지 않고, 평활 normal과 가짜 tangent를 다시 조합해서 만든다. 작성자는 좌우 방향 변화가 너무 커지지 않도록 camera right와의 겹침을 제거하는 추가 trick도 넣었다고 적는다. 이 때문에 완전히 물리적인 hair highlight는 아니지만, 게임처럼 정렬된 2D anime 광택에 더 가까워진다.

그리고 이미 준비된 color map으로 highlight 위치를 샘플해 `F0`를 다시 꾸미고, 거기에 또 한 번 `Kajiya-Kay` 계열 halo를 계산해 `backF0`처럼 겹친 뒤 최종 결과를 만든다.

### outline, fur, 앞머리 그림자, 눈 그림자, 후처리도 별도로 다룬다

글 후반부는 세부 shader들이다.

- outline은 smooth uv 기반 normal을 써서 외곽으로 밀고, 카메라 거리와 screen space를 고려해 두께를 보정한다.
- fur shader는 toon base의 diffuse, specular, `IBL`, rim을 모두 가져오되, shape texture와 여러 layer pass를 더한다.
- 앞머리 그림자는 별도 mesh를 준비해 template/stencil처럼 쓰는 방식으로 구현한다.
- 눈 그림자는 대부분의 게임과 비슷하게 별도 polygon과 transparency로 처리한다.
- 후처리는 `LUT` color grading, `bloom`, anti-aliasing 세 가지를 공통으로 사용한다.

작성자는 이 세부들까지 들어가면 미술 디테일은 사실상 끝이 없다고 말한다. 특히 fur와 flame 효과는 완벽히 따라가지 못했고, 자신이 적은 구현도 원본과 차이가 크니 더 좋은 방법을 직접 연구해 보라고 적는다.

![원문 이미지](https://pic1.zhimg.com/v2-9429d1e01da20f78ec1e474a626cdc38_1440w.jpg)

원문 이미지 링크: <https://pic1.zhimg.com/v2-9429d1e01da20f78ec1e474a626cdc38_1440w.jpg>

### 글 말미

글 마지막에서 작성자는 이 복각이 완전무결하다고 주장하지 않는다. 오히려 이것은 자신의 분석과 경험, 그리고 AI 보조를 섞어 만든 reverse-engineering 결과라고 반복해서 밝힌다. 하지만 그만큼 학습용 자료로는 가치가 있다고 본다. 긴 글이지만 차근차근 따라가거나, 전체 코드를 코드 분석 도구에 넣어 함께 읽으면 훨씬 이해가 빠를 것이라고 권한다.

## 전문 요약

이 글은 `Unity URP`에서 `终末地`식 캐릭터 toon rendering을 복각한 과정을 처음부터 끝까지 정리한 글이다. 핵심은 하나의 shader로 모든 재질을 해결하는 것이 아니라, `toon base shader`를 중심으로 `직사광 강도`, top light, three-tone diffuse, stylized specular, 두 종류의 rim light 같은 공통 규칙을 세운 뒤, skin, face, eye, hair, transparent, metal, fur 같은 재질별 변형을 각각 얹는 데 있다. 얼굴은 `SDF` 기반으로, 눈은 특수 normal과 `matcap` 기반으로, 머리카락은 별도 smooth normal과 `Kajiya-Kay` 계열 highlight로 풀고, 마지막에는 outline, 앞머리 그림자, 눈 그림자, `LUT` color grading, `bloom`, anti-aliasing까지 더해 전체 화면 인상을 맞춘다. 완전한 원본 재현은 아니지만, `PBR`과 stylized trick을 어떻게 계층적으로 묶는지 보여 주는 아주 긴 복각 기록이다.

## 참조

- 원문: <https://zhuanlan.zhihu.com/p/2028819446546932894>
- 관련 링크: <https://github.com/qiudashu233/MyZmdShaders>
- 관련 링크: <https://zhuanlan.zhihu.com/p/31522286649>

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
- matcap: 모델의 법선 방향만으로 고광이나 재질 느낌을 입히는 texture 기반 shading 방식이다.
- Kajiya-Kay Shading: 머리카락처럼 가느다란 가닥의 방향성을 이용해 고광을 만드는 전통적인 hair shading 모델이다.
- top light: 실제 환경광과 별도로 캐릭터를 보기 좋게 만들기 위해 위쪽에서 비추는 보조광 설계다.
