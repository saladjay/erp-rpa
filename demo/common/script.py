# -*- coding: utf-8 -*-
"""回放脚本契约与校验。脚本是人可读可手改的 JSON(共识:小改手改脚本)。"""
ALLOWED_ACTIONS = ("click", "input", "hotkey", "wait")
ALLOWED_STRATEGIES = ("offset",)  # demo 仅 offset;后续加 uia / image


def validate(script):
    errors = []
    if not isinstance(script, dict):
        return ["脚本必须是 JSON 对象"]
    if not isinstance(script.get("name"), str) or not script.get("name"):
        errors.append("缺少非空 name")
    target = script.get("target")
    if not isinstance(target, dict) or not target.get("title_re"):
        errors.append("缺少 target.title_re")
    steps = script.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("steps 必须是非空数组")
        return errors
    for i, step in enumerate(steps):
        p = "steps[%d]" % i
        if not isinstance(step, dict):
            errors.append(p + " 必须是对象")
            continue
        action = step.get("action")
        if action not in ALLOWED_ACTIONS:
            errors.append("%s action=%r 不合法(允许 %s)" % (p, action, ALLOWED_ACTIONS))
            continue
        if action == "click":
            loc = step.get("locator")
            if not isinstance(loc, dict):
                errors.append(p + " click 需要 locator")
                continue
            if loc.get("strategy") not in ALLOWED_STRATEGIES:
                errors.append(p + " locator.strategy 只支持 " + str(ALLOWED_STRATEGIES))
            for f in ("x", "y"):
                if not isinstance(loc.get(f), int):
                    errors.append("%s locator.%s 必须是整数" % (p, f))
        elif action == "input":
            if not isinstance(step.get("text"), str):
                errors.append(p + " input 需要 text 字符串")
        elif action == "hotkey":
            keys = step.get("keys")
            if (not isinstance(keys, list) or not keys
                    or not all(isinstance(k, str) for k in keys)):
                errors.append(p + " hotkey 需要 keys 非空字符串数组")
        elif action == "wait":
            if not isinstance(step.get("seconds"), (int, float)) or step["seconds"] <= 0:
                errors.append(p + " wait 需要 seconds 正数")
    return errors
