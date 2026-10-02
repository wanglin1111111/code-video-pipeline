# code-video-pipeline

用代码模型做视频的生产管线技能：AI 不生成视频而是写出视频——LLM 写 Three.js 单文件 HTML 网页动画，无头浏览器逐帧录屏，FFmpeg 压成 MP4，全程 Agent 内完成，不开一次剪辑软件。

一句话：**视频 = 可编程的网页 + 录屏 + 编码。** 核心动作从"剪"变成"写规格 + 验收"。

## 实操底座（一手教程数据）

- 链路：LLM 写 JS/Three.js 单文件 HTML → 无头浏览器逐帧捕获 → FFmpeg 编码 MP4
- 确定性：每一秒由代码写死，可复现、可精确改（vs 视频模型抽卡碰运气）
- 成本：2 分钟 2K 片约 1700 万 Token，额度重置期内成本为 0，1080p-2K 不加价
- 模型：MiniMax Code + M3.1-Flash-Preview（多模态/1M 上下文/思考深度可调），长片开 max 约 2 小时
- 音频：MiniMax speech-2.8-hd 配音 + Node DSP 合成音效 BGM（噪声水火风雨、Karplus-Strong 古琴）+ 侧链闪避

## 解决什么

| 痛点 | 本技能的做法 |
|---|---|
| 不知道该走代码还是视频模型 | 分流判断前置：信息密集精确控制→代码；真实感人物物理→视频模型 |
| 每次从零写提示词 | 元指令 md 沉淀业务版，只改参数不改结构，坑写进硬约束节 |
| 一次要全套，返工成本翻倍 | 分阶段：静默版逐镜人眼验收过，再上音频 |
| 只收 MP4，改文案从头再来 | 交付四件套：index.html/SRT/分镜截图/可复用脚本 |
| 小动效也开高档位烧钱 | 档位匹配任务 + 重活排额度重置窗口后 |
| 代码路线硬啃写实镜头 | 拿短板撞长板，分流拦截 |

## 安装

复制本目录到 `~/.agents/skills/`（或你的 Skill 加载路径）即可。

## 自检

```bash
python scripts/validate.py tests/sample_good.json   # 必须 exit 0
python scripts/validate.py tests/sample_bad.json    # 必须 exit 1
```

## 结构

```
SKILL.md                              工作流入口（底层链路 + 6 步流程 + 7 条硬规则）
references/routing.md                 代码路线 vs 视频模型分流判据 + 判例表 + 成本直觉
references/meta-directive.md          元指令 md 完整模板（角色/参数/输出流程/交付/硬约束）
references/pipeline-tech.md           逐帧捕获验收清单 + 程序化音频 + FFmpeg + 成本档位数据
references/gotchas.md                 黑边/盖屏/时间轴重叠/TTS余额/ffmpeg兼容等脏活清单
scripts/validate.py                   视频制作计划七维校验器（exit 0/1/2）
tests/sample_good.json                通过基准
tests/sample_bad.json                 拦截基准(真实感走code/跳验收/缺四件套/档位错配…)
docs/methodology.md                   方法论全文（奥卡姆剃刀提炼 + 9 条核心 + 5 步行动指南）
```
