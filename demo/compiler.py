# -*- coding: utf-8 -*-
"""用法: python compiler.py sessions/20260101_120000"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.compiler import compile_session
from common.config import load_config
from common.vlmclient import VLMClient


def main():
    ap = argparse.ArgumentParser(description="把录制会话编译成回放脚本")
    ap.add_argument("session_dir")
    a = ap.parse_args()
    base = os.path.dirname(os.path.abspath(__file__))
    cfg = load_config(base)
    client = VLMClient(cfg["vlm"])
    out = compile_session(a.session_dir, client)
    print("脚本已生成: %s(请人工审阅后再回放)" % out)


if __name__ == "__main__":
    main()
