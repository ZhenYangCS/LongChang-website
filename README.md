# LongChang anonymous project page

独立的英文匿名论文主页。在仓库根目录启动以下服务；首屏 MuJoCo 交互需要通过 HTTP 打开：

```bash
python3 project_page/scripts/serve.py --bind 0.0.0.0 --port 8765
```

在服务器本机可访问 <http://127.0.0.1:8765>。从自己的电脑访问时，应使用服务器可达的 IP/域名加 `:8765`，或先建立 SSH 端口转发；浏览器中的 localhost 指的是浏览器所在电脑。预览服务器支持视频字节范围请求，并要求 HTML/JS/CSS 重新核验缓存，便于持续微调。

当前预览服务独立运行在 `longchang-page` tmux 会话，可用 `tmux attach -t longchang-page` 查看。同一房间的 15 段动画在 `longchang-shared` 中导出，日志为 `/tmp/longchang-shared-build.log`，不会随终端命令结束而停止。

整个 `project_page/` 目录可部署到任意静态托管服务，也支持站点子目录。无需 Node、构建步骤、API key 或实时模拟后端。字体、图片、视频和数据均为本地文件。代码按钮提供匿名源码 ZIP，包含框架、场景、依赖与入门说明。

论文中的匿名仓库链接在制作时返回 HTTP 401，因此页面先使用可直接下载的源码包。仓库开放后，可以把 `index.html` 的两个代码入口替换为正式匿名链接。

## 内容

- 首屏先显示 Figure 1 原图。点击 Push / Drag / Rotate 后加载本地 MuJoCo WASM，用原始 `workspace.xml` 实时计算推动、拖放、碰撞、摆锤和天平运动；Three.js 绘制玻璃、金属、珐琅与阴影。支持转视角、缩放、键盘推动和重置。
- 首图按材质合并静态几何，减少重复绘制；较慢设备使用缓存光照和自适应分辨率。物理保持固定步长，物体仍在运动时不会被固定时限强制停住；离开屏幕时暂停计算。
- 左侧为五行三列的 Table 1 场景目录，保留原编号、原名和论文 TikZ 机制图；右侧只展示场景名、一句通俗说明和演示。选择卡片为五行三列，左栏最多 300 px，列间距 8 px，整体与右侧视频面板等高，五行自适应均分高度，卡片内文字与图标保持紧凑，并适配笔记本屏幕，方向键可在网格中移动。手机使用下拉目录。移除重复的 WORLD / TABLE 1 标题及自动轮播入口；MP4/GIF 总集下载集中放在右上方；完整规则与测量数据放入默认折叠的 Rule & data；Watch 与 Try it 默认 4×，均可切换 0.5×、1×、2×、4×。
- **场景命名以 ACL 论文为唯一来源**：`scripts/paper_scenes.py` 从当前总览表读取 01–15 的正式名称，从附录读取对应规律与作用范围；网页、案例、演示标题和重新导出的字幕共用这份数据。
- **两种场景视图**：`Watch` 播放准备好的原生物理演示；`Try it` 使用与首图相同的 MuJoCo / Three.js 引擎，支持直接 Push、Drag、Rotate、滚轮缩放、暂停和重置，移除了 Original scene 入口。15 段 1440×960 视频与 Try it 共用 12×12×12 的封闭玻璃房尺寸和初始相机；墙厚、底座、地砖、相机和灯光均固定，仅替换内部物体与规律。物体轨迹和大小保持原始记录。Watch 默认放大关键过程，Try it 默认显示完整房间；Watch 保留 1–6 倍自由缩放，滚轮放大光标所在位置，拖动可查看房间任意区域，手机支持双指缩放。小地图实时标出查看范围，双击、0 键或 Room 恢复全景。高清局部视频按精确裁切坐标叠放在静态完整房间背景上；所有运动物体都在该区域内，缩放和平移不切换片源、不重新加载，保留时间、倍速和暂停状态；全屏也可使用播放和缩放控件。画面使用 1600×800 高清动态视频；全景与局部仍可自由切换。加速区速度值位于画面外，下载视频也在标题区显示速度，不遮挡物体。两种视图使用统一的名称、简述、画面和底部控件区。可下载 186 秒合集、GIF 和视频/记录 ZIP。
- 视频为 60 fps，直接取自 500 Hz 的 MuJoCo 状态；恒定播放映射，不插入人为定格。场景 12、13 是连续碰撞过程，从当前位置继续推动；场景 09 的独立试验用短过渡明确区分。场景 10 同时发射两个初速度相同的球：红球进入黄色区，蓝球始终在区外；速度标签与轨迹显示差异，全程不重置位置。封面使用第一帧，避免开始播放时跳位置。下载 GIF 为 30 fps。
- 页面先展示静图，未播放的视频不下载。首屏物理引擎只在操作时加载；场景索引只含播放元数据和低清预览，完整测量数据不随首屏下载，测量数组单独按需读取。高清图解码前先显示内嵌预览，避免空白。预览服务压缩 JS / JSON / WASM，保留视频 Range 请求；视频和引擎下载超时会提供重试。
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

`Watch` 直接运行 `scenes/base_15.json` 的原始物理程序，保留物体大小、颜色、质量、摩擦、重力与碰撞规律。初始位置按公开脚本布置；连续碰撞示例不再摆回起点，记录每次推动前的实际位置。当前数据包含准备位置、干预、原始规则回调事件、源哈希、500 Hz 状态采样及关闭异常规则的普通物理对照。视频取最近的原生状态，不使用光流补帧；玻璃外壳和展示底座仅用于呈现。这些是专门制作的演示，不是模型自主探索，不计入主实验的 540 条结果。

成功探索视频和研究问题案例来自原始模型实验存档。三种素材的来源分别标识；页面播放秒数与模拟 counts 分开显示。

原有图解导出依次包括：普通地砖的匹配下落、吸引对象配对、等高度/等速度/等冲量、重力相位、制动阈值、发射方向、反弹高度、发射冲量、经过/绕开/越过区域、能量区内外、球与墙碰撞、重复与持续接触、第三次接触、停止红球后的延迟复制，以及零/非零干预。可通过 `?scene=07#worlds` 直接打开指定场景。

`assets/scene-physics.js` 实现 15 个场景的浏览器规则，`assets/scene-live.js` 管理实时交互与模型释放；`assets/atlas.js` 保留静态图解导出所用的示意模型，`assets/motion.js` 维护四幕概览、共享绘图及导出时钟；布局分别在同名 CSS 中。数据和真实视频独立保留，调整动效无需改实验记录。

回放由 `runs` 中保存的 MuJoCo 模型版本和状态恢复，没有重新运行探索或推进物理。画面进行相机、灯光、房间剖视和 sRGB 显示转换；物体位置、尺寸、原始颜色及规律均保留。视频取最近的记录帧，不插值物体轨迹。每段视频标出原始回合及模拟时间，章节按“观察、区分解释、进一步验证”组织；短片的播放速度经过调整，显示的模拟时间来自记录。

原始笔记与网页解释分别展示。颜色交换和器材案例来自 500-turn 条件，是精选案例，未并入主实验指标。案例解释不代替完整的发现评价。

## 更新素材

页面可直接使用，以下脚本仅用于在论文或源素材变化后重新导出。

本轮首屏和场景展示的检查与更新（已完成的渲染无需重跑）：

```bash
python scripts/verify_front.py --url http://127.0.0.1:8765 --require-hd
python scripts/verify_oracle_records.py
python scripts/verify_shared_room.py
python scripts/verify_smooth_motion.py
python scripts/verify_playback.py
python scripts/verify_zoom.py
python scripts/verify_live_rules.py --prepare --audit
python scripts/verify_live_rules.py --audit
python scripts/verify_live_interaction.py
python scripts/export_table1_symbols.py

# 原始场景模型 → 浏览器实时物理
python scripts/export_interactive_scenes.py

# 原生 500 Hz 状态 → 同一房间、60 fps 动画 → 带说明下载版
python scripts/build_smooth_demos.py --ffmpeg /path/to/ffmpeg
python scripts/build_detail_views.py --ffmpeg /path/to/ffmpeg
python scripts/seal_scene_media.py --ffmpeg /path/to/ffmpeg
python scripts/oracle_catalog.py
python scripts/publish_clear_media.py --ffmpeg /path/to/ffmpeg
python scripts/export_oracle_signals.py
python scripts/package_oracle_demos.py
python scripts/package_physics_demos.py --ffmpeg /path/to/ffmpeg
python scripts/prepare_scene_index.py
```

渲染脚本使用项目现有 MuJoCo/Blender Python 环境。统一封顶版使用 128 samples、去噪与缓存球面光照；早期全景使用 256 samples 背景和 64 samples 动态区域。近景使用 Cycles 房间背景、缓存的 Cycles 球面光照和投影软阴影，以亚像素位置合成；相机由同一房间的裁切范围推导，物体位置与半径不变。近景为阅读方便增强灰球和黄色区的显示对比，记录中的原始 RGBA 保留。统一封顶版的所有全景也使用这一合成方式。`assets/clarity.css` 控制布局，`assets/room-world.js` 控制首屏实时物理，`scripts/oracle_catalog.py` 保存一句话中英说明。场景正式名称仍由论文自动读取。

固定房间配置在 `data/shared-room.json`。`verify_shared_room.py` 比较每次渲染实际构建的 Blender 网格、相机变换与灯光签名，防止仅统一长宽比却仍改变房间尺寸。Table 1 图标来源与哈希在 `assets/table1/source.json`。

Try it 从 `data/interactive-scenes/` 按需加载原生模型、质量、摩擦、接触参数与准备位置。所有场景共享同一个 WASM 实例，每次只保留一个场景渲染器；切换到 Watch 或离开屏幕后暂停物理。交互房间封闭玻璃墙和顶面的内表面与原程序的 x/y ±6、z 0–12 边界对齐；Watch 的玻璃房与 Try it 使用相同边界与同一相机投影；两种视图的画面区域也保持等高。Push 按冲量/质量改变速度，Drag 使用原始 Workshop.apply 的质量相关抓取力、当前重力补偿、100 的力上限与 2 的移动速度上限，手部可达高度仍为 3。拖放不触发 PUSH/THROW 的事件；延迟与第三次接触的状态持续保存到重置。

浏览器规则按 `scenes/base_15.json` 实现，包含接触变色、第三次接触上跳、延迟复制与暂停计时。`verify_live_rules.py` 用原始 Python 程序产生对照轨迹；扩展审计共 69 组实验，覆盖原演示、随机初始运动、持续抓取与释放、换砖反弹、三球接触、天花板碰撞、多个延迟复制以及零冲量。以 0.05 秒间隔比较位姿、速度、颜色、抓取状态、碰撞计数和所有定时事件，当前误差小于 10⁻⁸。4× 实时播放仅增加每个显示帧内的物理步数，积分步长仍为 0.002 秒。Python 验证环境是 MuJoCo 3.12.0，浏览器是 3.15.0。浏览器交互不包含搭建新器材的工坊流程。

首屏依赖固定版本 MuJoCo 3.15.0（Apache-2.0）和 Three.js 0.186.1（MIT），全部存放于 `assets/vendor/`，无需连接外部 CDN。首次操作才下载引擎，不影响页面先显示；部署时保持相对目录和 `.wasm` 文件即可。

以下为其他论文材料及旧版示意图的导出工具：

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
