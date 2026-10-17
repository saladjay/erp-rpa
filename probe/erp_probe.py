# -*- coding: utf-8 -*-
"""
erp_probe.py — ERP 控件可观测性摸底工具(项目第 0 步)

在装有目标 ERP 的机器上运行,导出指定窗口的:
  1) UIA 控件树   -> uia_tree.txt     (能拿到多少控件、有没有名字/AutomationId)
  2) Win32 窗口树 -> win32_tree.txt   (MSAA/句柄层能看到什么)
  3) 整屏截图     -> screenshot.png   (探测时 ERP 停在什么界面)
  4) 摘要         -> report.txt

用法:
  python erp_probe.py                     交互模式:列出顶层窗口,输入编号选择
  python erp_probe.py "窗口标题关键字"     按标题关键字直接探测
  python erp_probe.py "关键字" 4           第三个参数=遍历深度(默认 8,卡死就调小)

结果输出到脚本旁的 probe_report_<时间戳>/ 目录,整个目录打包即可。

依赖:pip install pywinauto pillow
注意:先打开 ERP 并停在想自动化的那个表单界面,再运行本脚本。
"""
import datetime
import os
import sys
import traceback

OUT = None  # 报告目录,main() 里初始化


def log(msg=""):
    line = str(msg)
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("gbk", "replace").decode("gbk"))
    with open(os.path.join(OUT, "report.txt"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def log_env():
    import platform
    log("== 系统: %s %s  机器: %s  python: %s(%d位)" % (
        platform.system(), platform.release(), platform.machine(),
        platform.python_version(), 64 if sys.maxsize > 2 ** 32 else 32))


def pick_window(keyword):
    from pywinauto import Desktop
    wins = [w for w in Desktop(backend="uia").windows() if w.window_text().strip()]
    if keyword:
        kw = keyword.lower()
        matched = [w for w in wins if kw in w.window_text().lower()]
        if not matched:
            log("没有标题含 '%s' 的窗口。现有窗口:" % keyword)
            for w in wins:
                log("  - %s" % w.window_text()[:70])
            return None, None
        if len(matched) > 1:
            log("关键字 '%s' 匹配到 %d 个窗口,取第一个:" % (keyword, len(matched)))
            for w in matched:
                log("  - %s" % w.window_text()[:70])
        target = matched[0]
    else:
        log("顶层窗口列表(标题 | class | pid):")
        for i, w in enumerate(wins):
            log("%2d. %s | %s | %s" % (
                i, w.window_text()[:55], w.element_info.className,
                w.element_info.process_id))
        n = input("输入要探测的窗口编号: ").strip()
        target = wins[int(n)]
    handle = target.element_info.handle
    log("")
    log("== 选定窗口: %s" % target.window_text())
    log("== 句柄=%s class=%s pid=%s" % (
        handle, target.element_info.className, target.element_info.process_id))
    log("提示:进程名可在任务管理器按 pid 查,或 cmd 执行 tasklist /fi \"pid eq %s\""
        % target.element_info.process_id)
    return handle, target.window_text()


def dump_tree(backend, handle, depth):
    """导出某个后端的控件树;返回 (文件名, 行数) 或 (None, 0)"""
    from pywinauto import Desktop
    win = Desktop(backend=backend).window(handle=handle).wrapper()
    fn = os.path.join(OUT, "%s_tree.txt" % backend)
    log("导出 %s 树(深度 %d)… 复杂界面可能要 1-3 分钟,卡死就 Ctrl+C 后调小深度" % (backend, depth))
    win.print_control_identifiers(depth=depth, filename=fn)
    n = 0
    if os.path.exists(fn):
        with open(fn, "r", encoding="utf-8", errors="replace") as f:
            n = sum(1 for _ in f)
    log("  -> %s (%d 行)" % (fn, n))
    return fn, n


def grab_screen():
    from PIL import ImageGrab
    img = ImageGrab.grab()
    fn = os.path.join(OUT, "screenshot.png")
    img.save(fn)
    log("截图: %s (%dx%d)" % (fn, img.width, img.height))


def main():
    global OUT
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "probe_report_" + stamp)
    os.makedirs(OUT, exist_ok=True)

    keyword = sys.argv[1] if len(sys.argv) > 1 else None
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else 8

    log("# ERP 探测报告 %s  (深度=%d)" % (stamp, depth))
    log_env()
    log("")
    handle, title = pick_window(keyword)
    if not handle:
        log("未选定窗口,退出。")
        return

    grab_screen()
    uia_fn, uia_lines = dump_tree("uia", handle, depth)
    win32_fn, win32_lines = dump_tree("win32", handle, depth)

    log("")
    log("== 完成。快速判读:")
    log("   uia_tree 行数=%d,win32_tree 行数=%d" % (uia_lines, win32_lines))
    log("   行数多且控件带可读名称 -> 控件树定位为主,架构乐观")
    log("   行数很少/大段空名 -> 自绘控件多,图像匹配兜底占比高")
    log("请把整个 %s 目录打包反馈。" % OUT)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n已中断(未完成的部分不会写入)。可调小深度重试。")
    except Exception:
        with open(os.path.join(OUT, "report.txt"), "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        print(traceback.format_exc())
        print("出错详情已写入 report.txt,请一并打包反馈。")
