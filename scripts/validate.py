#!/usr/bin/env python3
"""validate.py — code-video-pipeline 视频制作计划七维校验器

输入: 视频制作计划 JSON（schema 见 tests/sample_good.json）
  {
    "shot": {
      "id": "SHOT-1",
      "type": "info_dense",               // info_dense(信息密集) | realistic(真实感/人物/物理)
      "route": "code",                    // code(代码路线) | video_model(视频模型) | mixed
      "route_reason": "分流理由",
      "has_realistic_elements": false     // 是否含真实感/人物/复杂物理元素
    },
    "meta_directive": {
      "exists": true,                     // 元指令 md 是否存在
      "business_version": "产品功能演示片", // 业务版名称
      "reused": true,                     // 是否复用既有元指令（只改参数）
      "hard_constraints": ["黑边", "盖屏", "时间轴重叠"]  // 硬约束清单
    },
    "pipeline": {
      "stage": "silent",                  // silent(静默版) | audio(音频) | encode(编码成片)
      "shot_screenshots_done": true,      // 静默版逐镜截图是否完成
      "human_review_passed": true,        // 人眼逐镜验收是否通过
      "audio_stage_blocked_until_review": true  // 音频阶段是否被验收门控
    },
    "delivery": {                          // 交付四件套
      "index_html": true,
      "srt": true,
      "shot_screenshots": true,
      "reusable_scripts": true
    },
    "budget": {
      "think_tier": "max",                // low | medium | high | max
      "task_size": "long",                // short(小动效) | long(长片)
      "within_quota_reset_window": true   // 是否排在额度重置窗口后
    }
  }

七维校验（任一 FAIL → exit 1）：
  D1 分流纪律: type=realistic 且 route=code → FAIL（拿短板撞长板）；
     route=code 且 has_realistic_elements=true → FAIL；
     route 须与 type 一致（info_dense→code, realistic→video_model, mixed 允许任一但须说明）
  D2 元指令纪律: 元指令必须存在且硬约束非空；reused=false 且 business_version 存在
     （说明同业务已有元指令却从零重写）→ FAIL
  D3 分阶段纪律: stage=audio 或 encode 时，shot_screenshots_done 且 human_review_passed
     必须为 true（静默版未过验收禁止进音频/编码）；
     stage=encode 时 audio_stage_blocked_until_review 必须 true
  D4 交付四件套: 四项全 true；任一 false → FAIL（只收 MP4 = 资产没收）
  D5 档位匹配: think_tier ∈ 枚举；task_size=short 且 tier ∈ {high,max} → FAIL
     （小动效用高档 = 烧钱）；task_size=long 且 tier ∈ {low} → FAIL（长片低档跑不完）
  D6 额度纪律: task_size=long 且 within_quota_reset_window=false → FAIL
     （重活排额度重置窗口后，1700 万 Token 级消耗撞额度墙）
  D7 理由留痕: route_reason 非空（分流必须写理由，防"顺手选了 code"）；
     同业务第 2 个片子起 reused 必须 true（meta_directive.reused=false 且 exists=true 时 WARN 级提示，
     但若 business_version 非空仍按 FAIL 处理——有业务版却不复用=资产没沉淀）

退出码：0=通过 / 1=有缺陷 / 2=文件/格式错误
"""
import json
import sys

TYPES = {"info_dense", "realistic", "mixed"}
ROUTES = {"code", "video_model", "mixed"}
TIERS = {"low", "medium", "high", "max"}
SIZES = {"short", "long"}
STAGES = {"silent", "audio", "encode"}


def fail(checks, code, msg):
    checks.append(("FAIL", code, msg))


def ok(checks, code, msg):
    checks.append(("OK", code, msg))


def validate(plan):
    checks = []

    shot = plan.get("shot") or {}
    where = f"shot({shot.get('id', '?')})"

    # D1 分流纪律
    stype = shot.get("type")
    route = shot.get("route")
    if stype not in TYPES:
        fail(checks, "D1", f"{where}: type 非法: {stype!r}")
    elif route not in ROUTES:
        fail(checks, "D1", f"{where}: route 非法: {route!r}")
    else:
        if stype == "realistic" and route == "code":
            fail(checks, "D1", f"{where}: 真实感/人物/物理需求走代码路线——拿短板撞长板，走视频模型")
        elif stype == "info_dense" and route == "video_model":
            fail(checks, "D1", f"{where}: 信息密集要精确控制却走视频模型——抽卡碰运气，走代码路线")
        elif stype == "info_dense" and route == "code" and shot.get("has_realistic_elements") is True:
            fail(checks, "D1", f"{where}: 信息密集片含真实感元素却整体走 code——该镜头改走视频模型(mixed)")
        elif stype == "mixed":
            ok(checks, "D1", f"{where}: mixed 分流（理由留痕见 D7）")
        else:
            ok(checks, "D1", f"{where}: 分流一致（{stype} → {route}）")

    # D7 理由留痕（与 D1 同节，先查非空）
    if not (shot.get("route_reason") or "").strip():
        fail(checks, "D7", f"{where}: route_reason 缺失——分流必须写理由")
    else:
        ok(checks, "D7", f"{where}: 分流理由已留痕")

    # D2 元指令纪律
    md = plan.get("meta_directive") or {}
    if md.get("exists") is not True:
        fail(checks, "D2", "元指令 md 不存在——别每次从零写提示词")
    else:
        hc = md.get("hard_constraints") or []
        if not hc or not all(str(x).strip() for x in hc):
            fail(checks, "D2", "元指令硬约束为空——黑边/盖屏/时间轴重叠等坑无规避")
        else:
            ok(checks, "D2", f"元指令硬约束 {len(hc)} 条")
        bv = (md.get("business_version") or "").strip()
        if bv and md.get("reused") is not True:
            fail(checks, "D2", f"业务版「{bv}」已存在却 reused=false——同业务第 2 个片子起必须复用元指令，只改参数")
        elif not bv:
            fail(checks, "D2", "business_version 缺失——元指令未固化为业务版，无法长期复用")
        else:
            ok(checks, "D2", f"元指令复用「{bv}」")

    # D3 分阶段纪律
    pl = plan.get("pipeline") or {}
    stage = pl.get("stage")
    if stage not in STAGES:
        fail(checks, "D3", f"pipeline.stage 非法: {stage!r}")
    else:
        ss = pl.get("shot_screenshots_done") is True
        hr = pl.get("human_review_passed") is True
        if stage in ("audio", "encode") and not (ss and hr):
            fail(checks, "D3", f"stage={stage} 但静默版逐镜验收未过（screenshots={ss}, review={hr}）——分阶段不可跳")
        elif stage == "encode" and pl.get("audio_stage_blocked_until_review") is not True:
            fail(checks, "D3", "encode 阶段但音频门控未启用——一次梭哈，返工成本翻倍")
        elif stage == "silent":
            ok(checks, "D3", "静默版阶段，验收进行中")
        else:
            ok(checks, "D3", f"stage={stage}，分阶段纪律通过")

    # D4 交付四件套
    dv = plan.get("delivery") or {}
    missing = [k for k in ("index_html", "srt", "shot_screenshots", "reusable_scripts") if dv.get(k) is not True]
    if missing:
        fail(checks, "D4", f"交付四件套缺: {missing}——只收 MP4 = 资产没收，退回补交")
    else:
        ok(checks, "D4", "交付四件套齐全（index.html/SRT/分镜截图/可复用脚本）")

    # D5 档位匹配
    bd = plan.get("budget") or {}
    tier = bd.get("think_tier")
    size = bd.get("task_size")
    if tier not in TIERS:
        fail(checks, "D5", f"think_tier 非法: {tier!r}")
    elif size not in SIZES:
        fail(checks, "D5", f"task_size 非法: {size!r}")
    else:
        if size == "short" and tier in ("high", "max"):
            fail(checks, "D5", f"小动效开 {tier} 档——日常小动效用 low/medium 快速出")
        elif size == "long" and tier == "low":
            fail(checks, "D5", "长片开 low 档——长程任务开 high/max")
        else:
            ok(checks, "D5", f"档位匹配（{size} → {tier}）")

    # D6 额度纪律
    if size == "long" and bd.get("within_quota_reset_window") is not True:
        fail(checks, "D6", "长片未排在额度重置窗口后——1700 万 Token 级消耗撞额度墙")
    elif size == "long":
        ok(checks, "D6", "重活已排额度重置窗口后")
    else:
        ok(checks, "D6", "小动效，额度纪律豁免")

    return checks


def main():
    if len(sys.argv) != 2:
        print("usage: python validate.py plan.json", file=sys.stderr)
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            plan = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: 无法读取/解析: {e}", file=sys.stderr)
        return 2
    if not isinstance(plan, dict):
        print("ERROR: 顶层必须是 JSON 对象", file=sys.stderr)
        return 2

    checks = validate(plan)
    fails = [c for c in checks if c[0] == "FAIL"]
    for status, code, msg in checks:
        if status == "FAIL":
            print(f"[{code}] FAIL {msg}")
    print(f"== {len(checks) - len(fails)} OK / {len(fails)} FAIL ==")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
