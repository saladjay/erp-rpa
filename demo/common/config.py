# -*- coding: utf-8 -*-
"""配置加载:首次运行从 config.example.json 复制并提示填 key。"""
import json
import os
import shutil


def load_config(base_dir):
    path = os.path.join(base_dir, "config.json")
    example = os.path.join(base_dir, "config.example.json")
    if not os.path.exists(path):
        if os.path.exists(example):
            shutil.copyfile(example, path)
            raise RuntimeError(
                "已生成 %s,请填入 api_key 后重试" % path)
        raise RuntimeError("缺少配置文件: %s" % path)
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)
