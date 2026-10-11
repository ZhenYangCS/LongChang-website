# LongChang anonymous project page

独立的英文匿名论文主页。直接用浏览器打开 `index.html`，或在仓库根目录启动：

```bash
python3 -m http.server 8765 --bind 127.0.0.1 --directory project_page
```

访问 <http://127.0.0.1:8765>。整个 `project_page/` 目录可部署到任意静态托管服务，也支持站点子目录。无需 Node、构建步骤、API key 或后端。字体、图片、视频和数据均为本地文件。代码按钮提供匿名源码 ZIP，包含框架、场景、依赖与入门说明。

论文中的匿名仓库链接在制作时返回 HTTP 401，因此页面先使用可直接下载的源码包。仓库开放后，可以把 `index.html` 的两个代码入口替换为正式匿名链接。

## 内容

- 玻璃房首屏与研究概述。
- 四个交互式规律示意图：地砖反弹、顺时针偏转、延迟速度复制、受发射抑制的漂移。可改变高度或发射方向、选择对照实验、重置计时。
- 从当前评分 C/S 同时通过的 Astra runs 中精选四个故事，每个有三个真实视频章节，共12段；支持播放、暂停、拖动、最终笔记和报告下载。
- 框架流程图可播放、暂停和逐阶段点击；结果热力图的 Astra 成功格可跳转到相应故事。
- 15 个场景的初始状态图及可展开的规律描述。
- 12 个模型的 D/C/S 对比、场景热力图及全部探索行为指标。
- 任务提示、预算与器材权限对比；颜色交换与称重装置案例。
- 场景演化的三个分支与独立评测结果。
- 匿名论文、540 条结果记录、原始 prompt、案例笔记，以及三张结果图的 SVG/PNG 下载。

## 结果口径与来源

`data/paper.js` 从当前论文冻结的 GPT-6.1-Sol 评价导出。主实验包含 12 × 15 × 3 = 540 条记录；每个模型的 D/C/S 以 42 个改变物理规律的场景运行计算，正常对照单独统计。页面的三项发现指标、五项探索指标及对照拒绝数均与源码表格一致。

源文件哈希在 `data/provenance.json`。预算实验使用无上下文压缩的匹配基线，其 100-turn 条件与主实验基线不同。场景演化另有一组原始场景运行，因此其 Scene 14/15 数值与主实验热力图不同。网页已说明这两个区别。

主视频精选 Scene 07 r3、Scene 06 r1、Scene 14 r2、Scene 15 r3。它们全部在论文当前 GPT-6.1-Sol 评分中同时通过 C/S。原始主实验 Astra 共7个成功 runs，分布为Scene 06两次、07一次、14一次、15三次。来源在 `data/discovery-provenance.json`，完整笔记和报告在 `downloads/successful-runs.json`。

交互示意图是用于解释规律的简化模型，画面明确标注 illustration，不作为真实探索证据。高度、发射方向和计时操作仅影响示意图。真实视频与示意图分栏呈现。

回放由 `runs` 中保存的 MuJoCo 模型版本和状态恢复，没有重新运行探索或推进物理。画面进行相机、灯光、房间剖视和 sRGB 显示转换；物体位置、尺寸、原始颜色及规律均保留。视频取最近的记录帧，不插值物体轨迹。每段视频标出原始回合及模拟时间，章节按“观察、区分解释、进一步验证”组织；短片的播放速度经过调整，显示的模拟时间来自记录。

原始笔记与网页解释分别展示。颜色交换和器材案例来自 500-turn 条件，是精选案例，未并入主实验指标。案例解释不代替完整的发现评价。

## 更新素材

页面可直接使用，以下脚本仅用于在论文或源素材变化后重新导出。

```bash
# 依赖 Pillow、pypdf；从当前论文、图件和结果表导出
python scripts/prepare_data.py

# 依赖 Matplotlib、Pillow、NumPy；导出三张独立结果图和分享卡
python scripts/export_figures.py

# 使用安装了项目依赖的 Python，另需 ffmpeg；不产生 API 调用
python scripts/render_replays.py --ffmpeg /path/to/ffmpeg

# 精选并核验成功 runs，生成12段证据视频和公开记录
python scripts/prepare_discoveries.py --ffmpeg /path/to/ffmpeg

# 强制重新渲染现有视频与场景图
python scripts/render_replays.py --ffmpeg /path/to/ffmpeg --force

# 核对本地链接、数据、所有主实验指标与来源哈希
python scripts/verify_site.py

# 可选：使用 Playwright 检查真实浏览器交互及响应式布局
python scripts/verify_browser.py
```

以上命令在 `project_page/` 中运行，脚本会自行定位仓库根目录。准备数据需要当前 `acl-build/0.pdf`。所有生成输出保存在本目录；场景渲染会使用项目已有的只读回放加载器。

匿名版本不含作者姓名、机构、邮箱或个人链接。论文下载副本的作者元信息为 Anonymous Authors，数据下载不含本地路径或 API 请求设置。字体授权见 `assets/fonts/*LICENSE.txt`。
