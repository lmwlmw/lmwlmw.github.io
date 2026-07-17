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

`【技术美术】unity 工具记录 - 写个GPU上运行的SDF生成器` 글을, 원문 흐름을 최대한 유지하면서 자연스럽게 번역합니다.

## 使用方式

![원문 이미지](https://pic1.zhimg.com/v2-b2ad7e472c0d2e55e17f9d26168e3f35.jpg?source=25ab7b06)

원문 이미지 링크: <https://pic1.zhimg.com/v2-b2ad7e472c0d2e55e17f9d26168e3f35.jpg?source=25ab7b06>

## 前言

최근 `Compute shader`로 Unity `SDF` 생성기를 하나 만들었다. 여기서는 `SDF`의 생성 알고리즘을 다시 돌아보고, 핵심 코드를 기록해 둔다. 프로젝트는 GitHub에 올려 두었다.

이 도구를 이용해 만든 dissolve 효과:

<!--more-->

## 需求

카툰 렌더링의 얼굴 normal, 그리고 연소, dissolve, growth 같은 효과에서는, Houdini에서 정교하게 다듬은 결과를 게임 엔진으로 가져와 표현하고 싶을 때가 있다. 이때는 `SDF` texture를 써서 표면 변화 과정을 기록해야 할 수 있다.

예를 들어 Houdini에서 `pyrosourcespread` 노드로 burn 효과를 만든 뒤, 각 frame의 흑백 마스크를 내보낸다. 이 글은 Unity 엔진 안에서 그 흑백 마스크를 `SDF` 이미지와 gradient texture로 바꾸는 도구를 기록한다.

`(첫 번째 gif가 보이지 않으면 아래 링크로 볼 수 있다)`

![원문 이미지](https://pic1.zhimg.com/v2-09763168a0822ec2e081aa67b55b6574_b.jpg)

원문 이미지 링크: <https://pic1.zhimg.com/v2-09763168a0822ec2e081aa67b55b6574_b.jpg>

![원문 이미지](https://pic3.zhimg.com/v2-85281feb5e66fa7590ab67a09b94f20e_1440w.jpg)

원문 이미지 링크: <https://pic3.zhimg.com/v2-85281feb5e66fa7590ab67a09b94f20e_1440w.jpg>

![원문 이미지](https://pic3.zhimg.com/v2-f8e5e91f95ab31987d74aa563aeb7e3c_1440w.jpg)

원문 이미지 링크: <https://pic3.zhimg.com/v2-f8e5e91f95ab31987d74aa563aeb7e3c_1440w.jpg>

## 原理

### SDF 是什么

`SDF`는 signed distance field다. 2D 이미지 `SDF`에서는 각 pixel이 가장 가까운 반대 색 pixel까지의 거리를 기록한다. 예를 들어 아래 그림에서는, 검은색 부분의 `SDF`가 가장 가까운 흰 pixel까지의 거리를 기록하므로 양수가 되고, 흰색 부분은 가장 가까운 검은 pixel까지의 거리를 기록하므로 음수가 된다.

![원문 이미지](https://pica.zhimg.com/v2-e1f4ddb2c9431e9203b2ce821f094afe_1440w.jpg)

원문 이미지 링크: <https://pica.zhimg.com/v2-e1f4ddb2c9431e9203b2ce821f094afe_1440w.jpg>

### 如何从遮罩图生成 SDF

어떤 글에서 `SDF` 생성 방법을 세 가지로 설명한 적이 있다. brute force, `Saito`, `8ssedt`다.

여기서는 뒤의 두 방법 원리를 간단히 다시 적는다.

- `Saito`

첫 번째 단계에서는 가로 방향 최소 거리 제곱 맵을 만든다. 예를 들어 빨간 원으로 표시한 점에서 왼쪽의 최소 거리는 2 pixel, 오른쪽 최근접 거리는 4 pixel이므로, 왼쪽 거리의 제곱인 4를 기록한다.

![원문 이미지](https://pic4.zhimg.com/v2-03db23d3ca08d1cb6e3e699bfb1041e5_1440w.jpg)

원문 이미지 링크: <https://pic4.zhimg.com/v2-03db23d3ca08d1cb6e3e699bfb1041e5_1440w.jpg>

두 번째 단계에서는 첫 번째 단계의 결과를 각 열 단위로 꺼낸 뒤, 각 pixel에서 해당 pixel까지의 거리를 더하고, 그 최소값을 취한다. 그림의 9라고 표시된 pixel을 예로 들면, 왼쪽은 그 열의 값들이고 오른쪽은 각 pixel에서 9까지의 거리 제곱이다. 둘을 더한 값 중 최소가 4이므로, 이 점의 `SDF`는 4가 된다.

![원문 이미지](https://pic3.zhimg.com/v2-701bef00d52647e21262f16e75425322_1440w.jpg)

원문 이미지 링크: <https://pic3.zhimg.com/v2-701bef00d52647e21262f16e75425322_1440w.jpg>

- `8ssedt`

이 방법은 먼저 장애물을 0으로, 배경을 무한대로 표시한다.

첫 번째 패스에서는 각 중심 pixel이 좌상단 주변의 네 pixel, 즉 왼쪽, 좌상단, 위, 우상단을 조회한다. 각 pixel의 값에 그 pixel에서 중심 pixel까지의 거리를 더한 뒤, 최소값을 현재 pixel에 기록한다. 즉, 검은색 영역에서 오른쪽 아래로 값이 퍼져 나가게 된다.

두 번째 패스에서는 우하단의 네 pixel을 조회하며, 그림의 오른쪽 아래에서 왼쪽 위로 진행한다. 마지막으로 두 패스 결과를 합치면 된다.

예를 들어 왼쪽 그림이 흑백 이미지이고, 표시되지 않은 값이 무한대라고 하자. 오른쪽 그림은 좌상단 네 점을 조회하는 경우다. 빨간 원 점을 예로 들면, 네 점의 조회값에 현재 점까지의 거리를 더한 값은 각각 `1+1`, `0+sqrt(2)`, `1+1`, `2+sqrt(2)`가 되고, 그 중 최소를 현재 pixel 값으로 기록한다.

![원문 이미지](https://pic1.zhimg.com/v2-03ed9b465daf4e1e46ecceb35fabf4ae_1440w.jpg)

원문 이미지 링크: <https://pic1.zhimg.com/v2-03ed9b465daf4e1e46ecceb35fabf4ae_1440w.jpg>

- 方案选择

두 방법을 비교해 보면, `8ssedt`는 `O(N)` 시간 안에 끝낼 수 있지만, 각 pass가 반드시 순서대로 실행되어야 한다. 즉, 다음 계산은 반드시 이전 계산 결과를 기반으로 해야 하며, 그래야 값이 0인 pixel이 바깥으로 퍼져 나갈 수 있다.

반면 `Saito`는 병렬 계산이 가능하므로 GPU에서 돌리기에 더 적합하다. 그래서 여기서는 이 방법을 선택했다.

### SDF 图到渐变图

먼저 여러 장의 `SDF`가 있고, 각 `SDF`는 하나의 frame 번호에 대응한다고 하자. 예를 들어 첫 번째 frame의 `sdf1`과 다섯 번째 frame의 `sdf5`를 기록해 두었다면, 두 번째 frame의 `sdf2`는 선형 보간으로 만들 수 있다.

```c
float weight2 = (2-1)/(5-1);
sdf2 = sdf1 * weight2 + sdf5 * (1 + weight2);
```

각 frame의 `SDF` texture를 모두 준비한 뒤에는, `SDF`를 `step` 처리해 흑백 마스크로 만들고, 각 이미지의 흰색 부분을 출력 gradient image에 +1 밝기로 누적한다. frame 간격이 충분히 촘촘하면 연속적인 gradient image가 된다.

![원문 이미지](https://pic1.zhimg.com/v2-b926741f2fb8733f57480d71e4e02f22_1440w.jpg)

원문 이미지 링크: <https://pic1.zhimg.com/v2-b926741f2fb8733f57480d71e4e02f22_1440w.jpg>

## 工具开发

### 生成 SDF

이 부분은 `Compute shader`로 알고리즘을 구현한 코드를 기록하려는 것이다.

- 첫 번째 함수는 각 pixel이 한 줄 전체를 순회하며 가장 가까운 장애물까지의 거리를 찾는다.
- 두 번째 함수는 각 pixel이 한 열 전체를 순회하며, 해당 pixel 값에 각 pixel에서 현재 pixel까지의 거리를 더한 뒤 최소값을 취한다.
- 세 번째와 네 번째 함수는 기본적으로 첫 번째와 두 번째와 같지만, 흑백을 뒤집어서 장애물 내부의 `SDF`를 계산한다.
- 마지막으로 장애물 바깥의 `SDF`에서 장애물 내부 `SDF`를 빼면, 내부는 음수, 외부는 양수가 되는 `SDF` texture를 얻는다. 원래 흑백 mask는 `_OriginalTex`에 넣고, 네 개의 pass를 모두 돌리면 `SDF` image가 출력된다.

```hlsl
float _ScaleDown;
float2 _TexSize;
RWTexture2D<float> _TempTex; // 가로 방향 최소 거리를 저장하는 임시 texture
Texture2D<float> _OriginalTex; // 입력 흑백 mask
RWTexture2D<float> _OutputTex; // 출력 SDF

// 0. 원본의 1을 장애물, 0을 배경으로 보고, 배경에서 장애물까지의 가로 방향 최소 거리 찾기
[numthreads(32,32,1)]
void setHorizontalMinDist(uint3 id : SV_DispatchThreadID)
{
    float currentColor = _OriginalTex[id.xy].r;

    if (currentColor > 0.5)
    {
        _TempTex[id.xy] = 0;
        return;
    }

    float minDistance = 999999999;
    for (int i = 0; i < _TexSize.x; i++)
    {
        float distance = (i - id.x) * (i - id.x);
        float color = _OriginalTex[uint2(i, id.y)].r;
        if (color > 0.5)
        {
            minDistance = min(minDistance, distance);
        }
    }
    _TempTex[id.xy] = minDistance;
}

// 1. 각 열을 처리하여 최소 거리를 기록(양의 SDF)
[numthreads(32,32,1)]
void calculateSDF(uint3 id : SV_DispatchThreadID)
{
    float minDistance = 999999999;
    for (int i = 0; i < _TexSize.y; i++)
    {
        float distance = (i - id.y) * (i - id.y);
        float color = _TempTex[uint2(id.x, i)].x;
        minDistance = min(minDistance, sqrt(distance + color));
    }
    _OutputTex[id.xy] = minDistance / _ScaleDown;
}

// 2. 원본의 0을 장애물, 1을 배경으로 보고, 배경에서 장애물까지의 가로 방향 최소 거리 찾기
[numthreads(32,32,1)]
void setHorizontalMinDist2(uint3 id : SV_DispatchThreadID)
{
    float currentColor = _OriginalTex[id.xy].r;
    if (currentColor < 0.5)
    {
        _TempTex[id.xy] = 0;
        return;
    }

    float minDistance = 999999999;
    for (int i = 0; i < _TexSize.x; i++)
    {
        float distance = (i - id.x) * (i - id.x);
        float color = _OriginalTex[uint2(i, id.y)].r;
        if (color < 0.5)
        {
            minDistance = min(minDistance, distance);
        }
    }
    _TempTex[id.xy] = minDistance;
}

// 3. 각 열을 처리하여 최소 거리를 계산(음의 SDF)
//    양의 SDF에서 음의 SDF를 빼고 0-1 범위로 다시 매핑
[numthreads(32,32,1)]
void calculateSDF2(uint3 id : SV_DispatchThreadID)
{
    float oriOutput = _OutputTex[id.xy];

    float minDistance = 999999999;
    for (int i = 0; i < _TexSize.y; i++)
    {
        float distance = (i - id.y) * (i - id.y);
        float color = _TempTex[uint2(id.x, i)].x;
        minDistance = min(minDistance, sqrt(distance + color));
    }
    float dist2 = minDistance / _ScaleDown;
    _OutputTex[id.xy] = (oriOutput - dist2) * 0.5 + 0.5;
}
```

### 合成 SDF 为渐变图

나는 각 texture 이름의 마지막 몇 글자를 frame 번호로 썼다. 예를 들어 `Substance_graph_output_SDF_177`은 177번째 frame의 `SDF` image를 뜻한다.

내게는 `SDF` image가 총 180장 있고, 이것으로 255 단계의 밝기를 보간해 만들고 싶었다. 그러면 각 밝기에 대응하는 보간 위치는 `w = 180/255`가 된다.

매번 보간 위치 주변의 두 texture를 골라 interpolation한다. 예를 들어 `w = 180/255`이면 `sdf0`과 `sdf1` 사이를 보간하고, `2w = 360/255`이면 1보다 크므로 `sdf1`과 `sdf2` 사이를 보간한다. 만약 `SDF`가 5 frame마다 하나씩만 있다면, `1w`와 `2w` 모두 `sdf1`과 `sdf5` 사이를 보간하게 된다.

```csharp
async UniTaskVoid ComposeSDF() {
    await InitTexture();

    // SDF 번호와 texture를 대응시킨다
    Dictionary<int, Texture2D> numRT = _oriTextures.ToDictionary(
        (x) => int.Parse(x.name.Split('_').Last()),
        (x) => x
    );

    var keys = numRT.Keys.ToList();
    int keyIdx = 1;

    // 마지막 SDF 번호가 최대값(180)
    float sdfMax = keys.Last();
    // 각 밝기 단계가 대응하는 SDF 비율
    float ratio = (sdfMax) / 255f;

    for (int i = 0; i < 256; i++) {
        if (ratio * i > keys[keyIdx]) {
            if (keyIdx < keys.Count - 1) {
                keyIdx++;
            }
        }

        // 예: (2w-1)/(2-1)
        float weight = (ratio * i - keys[keyIdx - 1]) /
                       (keys[keyIdx] - keys[keyIdx - 1]);

        ComputeComposeSDF(
            weight,
            numRT[keys[keyIdx - 1]],
            numRT[keys[keyIdx]],
            _sdfTexture
        );
    }

    SaveTexture(_sdfTexture, _oriTextures.FirstOrDefault());
    AssetDatabase.SaveAssets();
    AssetDatabase.Refresh();
}

void ComputeComposeSDF(float weight, Texture2D sdf1, Texture2D sdf2, RenderTexture outTexture) {
    var cmd = new CommandBuffer();
    cmd.SetComputeFloatParam(_computeSDF, "_Weight", weight);
    cmd.SetComputeTextureParam(_computeSDF, 4, "_SDF1", sdf1);
    cmd.SetComputeTextureParam(_computeSDF, 4, "_SDF2", sdf2);
    cmd.SetComputeTextureParam(_computeSDF, 4, "_OutputTex", outTexture);
    cmd.DispatchCompute(_computeSDF, 4, _width / 32, _height / 32, 1);
    Graphics.ExecuteCommandBuffer(cmd);
}
```

`Compute shader` 쪽 코드는 다음과 같다.

```hlsl
Texture2D<float> _SDF1;
Texture2D<float> _SDF2;
float _Weight;

// 4. SDF 합성
[numthreads(32,32,1)]
void combineSDF(uint3 id : SV_DispatchThreadID)
{
    float initColor = _OutputTex[id.xy].r;
    float sdf1 = _SDF1[id.xy];
    float sdf2 = _SDF2[id.xy];
    float col = step(sdf1 * _Weight + sdf2 * (1 - _Weight), 0.5);
    _OutputTex[id.xy] = initColor + col / 255;
}
```

## 踩坑记录

- 처음에는 Houdini 안에서 도구를 쓰려고 했다. 하지만 Houdini `COP`에는 loop node가 없어서, 다음 pixel의 조회 대상을 이전 pixel의 출력 결과로 삼는 구조를 만들 수 없었다. 그래서 `8sset`은 작성할 수 없었다. 게다가 Houdini의 `VEX`는 CPU에서 실행되므로 `Saito`도 매우 느렸다. 결국 엔진 안에서 `Compute shader`로 도구를 작성할 수밖에 없었다. `Houdini`에서 `openCL`을 쓸 수 있는 것 같긴 하지만 자료가 너무 적다.

- `RenderTexture`는 엔진을 종료하면 비워지고, 도구를 사용해 asset으로 내보낸 뒤에도 내용이 사라지는 경우가 있다. 그래서 asset 저장 용도로 쓰면 안 되고, texture 제작이 끝난 뒤에는 `png`로 내보내야 한다.

```csharp
// path는 string path = AssetDatabase.GetAssetPath(oriTex); 로 얻을 수 있다
static void SaveRTToFile(RenderTexture rt, string path) {
    RenderTexture.active = rt;
    Texture2D tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false);
    tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0);
    RenderTexture.active = null;

    byte[] bytes = tex.EncodeToPNG();

    File.WriteAllBytes(path, bytes);
    AssetDatabase.ImportAsset(path);
}
```

- `URP`의 render feature가 아닌 곳에서도 `CommandBuffer`를 쓸 수 있다. `Graphics.ExecuteCommandBuffer`로 호출하면 된다. `CommandBuffer`를 사용하면 여러 `Compute shader`가 순서대로 실행되게 할 수 있고, 여러 command 작업을 비동기로 처리할 수도 있다.

```csharp
var cmd = new CommandBuffer();
cmd.SetComputeFloatParam(_computeSDF, "_Weight", weight);
cmd.SetComputeTextureParam(_computeSDF, 4, "_SDF1", sdf1);
cmd.SetComputeTextureParam(_computeSDF, 4, "_SDF2", sdf2);
cmd.SetComputeTextureParam(_computeSDF, 4, "_OutputTex", outTexture);
cmd.DispatchCompute(_computeSDF, 4, _width / 32, _height / 32, 1);
Graphics.ExecuteCommandBuffer(cmd);
```

마지막으로, 내가 구현한 Unity 효과와 도구는 계속 칼럼에 기록해 둘 예정이니, 관심 있으면 팔로우해 주시면 된다.

## 参考

- 亚像素距离变换 — Acko.net --- Sub-pixel Distance Transform — Acko.net
- 欧几里得距离转换（EDT）算法_distance transforms of sampled functions-CSDN博客

## 참조

- 원문: <https://zhuanlan.zhihu.com/p/702637242>
- 관련 링크: <https://github.com/FengLvv/VATTest/tree/main/Assets/Editor>
- 관련 링크: <https://zhuanlan.zhihu.com/p/703044996>
- 관련 링크: <https://acko.net/blog/subpixel-distance-transform/>
- 관련 링크: <https://blog.csdn.net/tianwaifeimao/article/details/45078661>
- 원문 이미지: <https://pic1.zhimg.com/v2-b2ad7e472c0d2e55e17f9d26168e3f35.jpg?source=25ab7b06>
- 원문 이미지: <https://pic1.zhimg.com/v2-09763168a0822ec2e081aa67b55b6574_b.jpg>
- 원문 이미지: <https://pic3.zhimg.com/v2-85281feb5e66fa7590ab67a09b94f20e_1440w.jpg>
- 원문 이미지: <https://pic3.zhimg.com/v2-f8e5e91f95ab31987d74aa563aeb7e3c_1440w.jpg>
- 원문 이미지: <https://pica.zhimg.com/v2-e1f4ddb2c9431e9203b2ce821f094afe_1440w.jpg>
- 원문 이미지: <https://pic4.zhimg.com/v2-03db23d3ca08d1cb6e3e699bfb1041e5_1440w.jpg>
- 원문 이미지: <https://pic3.zhimg.com/v2-701bef00d52647e21262f16e75425322_1440w.jpg>
- 원문 이미지: <https://pic1.zhimg.com/v2-b926741f2fb8733f57480d71e4e02f22_1440w.jpg>
