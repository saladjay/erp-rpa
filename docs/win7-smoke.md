# Win7 32 位冒烟清单(每阶段交付前执行)

**状态:待执行**(首次执行后改为"已执行 + 日期 + 结果")

环境:32 位 Win7(SP1),已装 Python 3.8.10 x86(python.org "Windows x86 executable installer",
安装勾选 Add to PATH 或记住安装路径)。
材料:**拷贝整个开发工作目录**到目标机(必须含 wheels/ 离线轮子——注意 wheels/ 不在 git 里,
git clone 拿不到,需另行同步)。

0. 二进制轮子首检(最高风险项):`py -3.8-32 -c "from PIL import Image"` → 若报 `_imaging` DLL
   加载失败:装 VC++ 运行库 + UCRT(KB2999226)后重试;仍失败则降级 `Pillow==8.4.0`
   (改 requirements + 重新 pip download,并把结论记入 demo-checklist 已知问题 6)
1. `install.bat` → 依赖离线安装成功(--no-index,全程不需要外网)
2. `py -3.8-32 -m pytest demo\tests -v` → 66 项全绿(不需要网络/大模型)
3. 记事本端到端(需外网+API Key):
   a. 配置:`copy demo\config.example.json demo\config.json`,记事本打开 config.json 填入 api_key(Win7 记事本保存的 UTF-8 带 BOM,程序已兼容)
   b. `py -3.8-32 demo\recorder.py` → 3 秒倒数内点进记事本 → 点一下编辑区 → 输入 hello 123(纯英文可避开 IME 差异)→ F10 → 意图输入"在记事本输入文字"
   c. `py -3.8-32 demo\compiler.py demo\sessions\<新目录>` → 检查 script.json
   d. 清空记事本,`py -3.8-32 demo\player.py demo\sessions\<目录>\script.json` → 文字重现
   e. 关闭记事本再回放 → 报警弹窗 + 退出码 2
4. 断网验证(红线):拔网线后仅跑 player(步骤 d 的脚本)→ 回放零网络依赖
5. 记录:winver 版本、DPI、每项通过/失败;失败附 sessions 目录与 run_log

已知注意事项:
- 目标窗口最小化时 player 报"找不到目标窗口"(已知问题,先把窗口还原)
- 剪贴板会被回放覆盖
- F10 结束录制时可能同时触发目标程序菜单栏,无碍
