# ERP 控件探测工具(项目第 0 步)

目的:在目标机器上测出 ERP 窗口的"控件可观测性"——能从控件树拿到多少控件、
控件有没有可读名称。这直接决定自动化脚本用"控件树定位"(稳)还是"图像匹配"(通用但脆)为主。

## 使用步骤

1. **装 Python**(目标机器或任何装有该 ERP 的机器):
   - 下载 Python 3.8.10 **Windows x86(32位)** 安装包:
     https://www.python.org/downloads/release/python-3810/ → 页面底部 "Windows x86 executable installer"
   - Win7 需已装 SP1(命令 `winver` 可查)。安装时勾选 "Add Python 3.8 to PATH"。

2. **装依赖**(需联网):
   ```
   pip install pywinauto pillow
   ```
   若目标机器不能联网:在能联网的机器上执行
   `pip download pywinauto pillow -d wheels`(同样用 32 位 Python 3.8),
   把 wheels 文件夹拷过去后执行 `pip install --no-index --find-links=wheels pywinauto pillow`。

3. **打开 ERP**,进入想自动化的那个表单界面(例如销售订单新增界面),停住。

4. **运行**(在 cmd 里、probe 目录下):
   ```
   python erp_probe.py                :: 交互模式,列出窗口选编号
   python erp_probe.py "订单"          :: 按窗口标题关键字直接探测
   python erp_probe.py "订单" 4        :: 遍历深度改为 4(默认 8)
   ```

5. **反馈**:把生成的 `probe_report_<时间戳>` 整个目录打包发回。

## 常见问题

- **卡住不动**:复杂界面遍历慢,等 3 分钟;仍不动则 Ctrl+C,用更小深度(如 4)重试。
- **找不到窗口**:不带参数运行,看列出的窗口标题,换更准的关键字。
- **报错**:错误已写入 report.txt,连同目录一起反馈。
