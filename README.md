# LongChang anonymous project page

独立的英文匿名论文主页。直接用浏览器打开 `index.html`，或在仓库根目录启动：

```bash
python3 project_page/scripts/serve.py --bind 0.0.0.0 --port 8765
```

在服务器本机可访问 <http://127.0.0.1:8765>。从自己的电脑访问时，应使用服务器可达的 IP/域名加 `:8765`，或先建立 SSH 端口转发；浏览器中的 localhost 指的是浏览器所在电脑。预览服务器支持视频字节范围请求，并要求 HTML/JS/CSS 重新核验缓存，便于持续微调。

当前预览服务独立运行在 `longchang-page` tmux 会话，可用 `tmux attach -t longchang-page` 查看。素材导出运行在 `longchang-media`，日志为 `/tmp/longchang-media-build.log`，不会随一条终端命令结束而停止。

整个 `project_page/` 目录可部署到任意静态托管服务，也支持站点子目录。无需 Node、构建步骤、API key 或实时模拟后端。字体、图片、视频和数据均为本地文件。代码按钮提供匿名源码 ZIP，包含框架、场景、依赖与入门说明。

论文中的匿名仓库链接在制作时返回 HTTP 401，因此页面先使用可直接下载的源码包。仓库开放后，可以把 `index.html` 的两个代码入口替换为正式匿名链接。

## 内容

- 浅色学术版式、动态首屏与研究概述；标题、摘要和匿名 PDF 同步当前论文。
- 15 个场景全部提供动态图解、触发说明、参数或对照条件；支持播放、暂停、拖动、重置、键盘切换和自动轮播。每个场景可切换查看论文来源的真实初始布置。
- **场景命名以 ACL 论文为唯一来源**：`scripts/paper_scenes.py` 从当前总览表读取 01–15 的正式名称，从附录读取对应规律与作用范围；网页、案例、演示标题和重新导出的字幕共用这份数据。
- **三种场景视图**：`Physics demo` 为原始 MuJoCo 场景程序的脚本化演示，`Try the law` 为轻量 SVG 交互，`Original scene` 为原始初始布置。全部 15 段实际物理演示带模拟时间、采样轨迹、读数、布置与操作记录；可下载 162 秒合集和视频/记录 ZIP。
- 48 秒四幕概览与全屏演示模式；120 秒全场景 MP4、15 个逐场景 GIF 和合集可直接下载。
- 四个交互式规律示意图：地砖反弹、顺时针偏转、延迟速度复制、受发射抑制的漂移。可改变高度或发射方向、选择对照实验、重置计时。
- 从当前评分 C/S 同时通过的 Astra runs 中精选四个故事，每个有三个真实视频章节，共12段；支持播放、暂停、拖动、最终笔记和报告下载。
- 框架流程图可播放、暂停和逐阶段点击；结果热力图的 Astra 成功格可跳转到相应故事。
- 每个场景的完整规律、适用对象与触发条件可展开阅读。
- 12 个模型的 D/C/S 对比、场景热力图及全部探索行为指标。
- 任务提示、预算与器材权限对比；研究问题形成（Astra/Gemini 真实回放对照）、颜色交换与称重装置案例。
- 场景演化的三个分支与独立评测结果。
- 匿名论文、540 条结果记录、原始 prompt、案例笔记，以及三张结果图的 SVG/PNG 下载。

## 结果口径与来源

`data/paper.js` 从当前论文冻结的 GPT-6.1-Sol 评价导出。主实验包含 12 × 15 × 3 = 540 条记录；每个模型的 D/C/S 以 42 个改变物理规律的场景运行计算，正常对照单独统计。页面的三项发现指标、五项探索指标及对照拒绝数均与源码表格一致。

源文件哈希在 `data/provenance.json`。预算实验使用无上下文压缩的匹配基线，其 100-turn 条件与主实验基线不同。场景演化另有一组原始场景运行，因此其 Scene 14/15 数值与主实验热力图不同。网页已说明这两个区别。

主视频精选 Scene 07 r3、Scene 06 r1、Scene 14 r2、Scene 15 r3。它们全部在论文当前 GPT-6.1-Sol 评分中同时通过 C/S。原始主实验 Astra 共7个成功 runs，分布为Scene 06两次、07一次、14一次、15三次。来源在 `data/discovery-provenance.json`，完整笔记和报告在 `downloads/successful-runs.json`。

SVG 交互和 illustration MP4/GIF 是用于解释规律的简化模型，不作为真实探索证据。普通摩擦、接触或运动在部分场景中被简化或省略，每个场景底部注明范围。

`Physics demo` 直接运行 `scenes/base_15.json` 的原始物理程序，保留物体大小、颜色、质量、摩擦、重力与碰撞规律。为清楚演示触发条件，球的位置会按公开脚本预先布置；重复接触的例子会在两次试验间重置位置但保留事件历史。数据包含准备位置、干预、接触事件、源哈希和 50 Hz 状态采样。视频取最近的采样状态，镜头和轨迹线仅用于显示。这些是专门制作的演示，不是模型自主探索，不计入主实验的 540 条结果。

成功探索视频和研究问题案例来自原始模型实验存档。三种素材的来源分别标识；页面播放秒数与模拟 counts 分开显示。

15 场景交互依次包括：普通地砖的匹配下落、吸引对象配对、等高度/等速度/等冲量、重力相位、制动阈值、发射方向、反弹高度、发射冲量、经过/绕开/越过区域、能量区内外、球与墙碰撞、重复与持续接触、第三次接触、停止红球后的延迟复制，以及零/非零干预。可通过 `?scene=07#worlds` 直接打开指定场景。

`assets/atlas.js` 维护 15 场景的示意模型及交互，`assets/motion.js` 维护四幕概览、共享绘图及导出时钟；布局分别在同名 CSS 中。数据和真实视频独立保留，调整动效无需改实验记录。

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

# 检查全部 15 场景的触发、对照条件、计时、轮播与演示模式
python scripts/verify_motion.py

# 检查原始物理触发、接触历史、延迟及全部 15 个视频的浏览器播放
python scripts/verify_physics.py --url http://127.0.0.1:8765

# 依赖 Playwright/Chromium、ffmpeg 或 imageio-ffmpeg；导出全部动态素材
python scripts/export_motion.py
# 仅更新某类素材：--only atlas / --only overview / --only gifs

# 使用项目的 MuJoCo Python 环境生成脚本化物理演示；不调用模型
python scripts/render_physics_demos.py --ffmpeg /path/to/ffmpeg
python scripts/package_physics_demos.py --ffmpeg /path/to/ffmpeg
```

以上命令在 `project_page/` 中运行，脚本会自行定位仓库根目录。准备数据需要当前 `acl-build/0.pdf`，结果表沿 `ACL/main.tex` 的 `input/include` 关系读取，兼容当前拆分的 `ACL/secs/`。所有生成输出保存在本目录；场景回放使用项目已有的只读加载器。动态素材由固定时间的浏览器画面编码，不发起模型请求。

匿名版本不含作者姓名、机构、邮箱或个人链接。论文下载副本的作者元信息为 Anonymous Authors，数据下载不含本地路径或 API 请求设置。字体授权见 `assets/fonts/*LICENSE.txt`。
