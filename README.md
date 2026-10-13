# LongChang anonymous project page

纯静态的英文匿名论文主页，可直接部署到 GitHub Pages，线上不需要 Python 服务、API key 或后端。部署步骤见 [PAGES.md](PAGES.md)，已同时提供独立站点仓库和当前目录结构的 GitHub Actions 配置。

以下 Python 命令仅供本地预览使用，不属于线上运行依赖：

```bash
python3 project_page/scripts/serve.py --bind 0.0.0.0 --port 8765
```

在服务器本机可访问 <http://127.0.0.1:8765>。从自己的电脑访问时，应使用服务器可达的 IP/域名加 `:8765`，或先建立 SSH 端口转发；浏览器中的 localhost 指的是浏览器所在电脑。预览服务器支持视频字节范围请求，并要求 HTML/JS/CSS 重新核验缓存，便于持续微调。

当前预览服务独立运行在 `longchang-page` tmux 会话，可用 `tmux attach -t longchang-page` 查看。同一房间的 15 段动画在 `longchang-shared` 中导出，日志为 `/tmp/longchang-shared-build.log`，不会随终端命令结束而停止。

整个 `project_page/` 目录可部署到任意静态托管服务，也支持站点子目录。无需前端编译、API key 或实时模拟后端。GitHub Actions 只用 Bash 复制已经生成的静态文件。字体、图片、视频和数据均为本地文件。代码按钮提供匿名源码 ZIP，包含框架、场景、依赖与入门说明。

论文中的匿名仓库链接在制作时返回 HTTP 401，因此页面先使用可直接下载的源码包。仓库开放后，可以把 `index.html` 首屏的 Code 入口替换为正式匿名链接。

## 内容

- 章节按“15 个场景 → Framework → 主结果 → 控制实验 → 案例分析 → 场景演化”排列，成功探索从结果中的场景格子打开。页面以场景演化收尾，取消单独的 Materials 章节及导航入口；论文与 Code 位于首屏，补充素材保存在项目文件中。
- 页头按提供的 StreamMA 参考实现：取消顶部导航与重复的项目名，只显示左侧玻璃房图标、居中的 LongChang、斜体论文标题、匿名署名及统一深色 Paper / Code / Demo 按钮。使用本地 Inter 与 Noto Serif 字体；桌面项目名 57.6 px、手机 41.6 px，字体与间距按参考页取值。图标内两颗彩色球同步眨动，减少动态效果时静止。样式在 `assets/hero.css`，图标是内联 SVG。六个章节仍使用独立的大标题和编号，见 `assets/chapters.css`。
- 首屏先显示 Figure 1 原图。点击 Push / Drag / Rotate 后加载本地 MuJoCo WASM，用原始 `workspace.xml` 实时计算推动、拖放、碰撞、摆锤和天平运动；Three.js 绘制玻璃、金属、珐琅与阴影。支持转视角、缩放、键盘推动和重置。
- 首图按材质合并静态几何，减少重复绘制；较慢设备使用缓存光照和自适应分辨率。高分屏最高使用 2× 像素密度，支持软阴影与 2048 阴影贴图，缓存材质提升到 256×256；暂时卡顿后会逐步恢复分辨率，避免一直模糊。物理保持固定步长，物体仍在运动时不会被固定时限强制停住；离开屏幕时暂停计算。
- 左侧为五行三列的 Table 1 场景目录，保留原编号、原名和论文 TikZ 机制图；右侧只展示场景名、一句通俗说明和演示。选择卡片为五行三列，左栏最多 300 px，列间距 8 px，整体与右侧视频面板等高，五行自适应均分高度，卡片内文字与图标保持紧凑，并适配笔记本屏幕，方向键可在网格中移动。手机使用下拉目录。移除重复的 WORLD / TABLE 1 标题及自动轮播入口；顶部合集下载与重复的前后切换箭头已移除；完整规则、模型说明和演示数据曲线统一整合在 Demo 视频右侧（手机下方），取消独立的 Rule & data 入口和场景视频、数据下载按钮；Demo 与 Experiment 默认 4×，均可切换 0.5×、1×、2×、4×。
- **场景命名以 ACL 论文为唯一来源**：`scripts/paper_scenes.py` 从当前总览表读取 01–15 的正式名称，从附录读取对应规律与作用范围；网页、案例、演示标题和重新导出的字幕共用这份数据。
- **两个入口**：`Demo` 保留原生物理视频，并在视频右侧直接展示原 Explain 的全部 15 个可调模型；`Experiment` 保留真实物理交互。模型的选项框、滑杆、拖球、相位选择、播放/重置和全屏继续可用，明确标为 Simplified model，参数只影响模型，不替换视频、不改变视频进度。右侧整合 Scene rule、MathML 公式和 Demo data 曲线；曲线来自原录制，游标跟随视频。模型与数据按可见性运行和加载，手机顺序排列。示意模型由 `assets/atlas.js` 和 `assets/model-interaction.js` 管理，合并布局在 `assets/demo-model.css`：桌面同排显示目录、视频和可调模型，右侧说明独立滚动；较窄屏幕将目录收为下拉框，保留视频与模型并排；手机上下排列。切换到 Experiment 会隐藏并暂停数学演示。原生模拟仍使用 Push / Drag / Rotate 和一条播放控制栏。
- `Demo` 和 `Experiment` 共用 12×12×12 的封闭玻璃房、物体实际尺寸和初始相机。墙、顶、底座与地砖固定，仅改变内部物体和规律。`Demo` 默认放大关键过程，`Experiment` 默认全景；视频可自由缩放、平移与全屏，小地图标明当前区域。1600×800 高清局部视频按准确裁切位置叠放于静态全景，只解码一个片源；手动缩放不会重载或改变播放时间。自动构图随窗口变化重新适配，灰色和黄色作用区完整可见。
- 场景 **05、09、10、11、14、15** 使用新的连续因果演示：05 显示制动与普通物理虚线对照；09 在同一次运动中完整进入和离开灰砖；10 同时发射相同初速度的球，显示黄色区域内外的速度分化；11 对比碰撞分离后的加速与普通路径；14 明确呈现发射、抓住红球、倒计时和 12 秒后的速度复制；15 显示力的开关、再次推动重置倒计时、16 秒时恢复。轨迹、速度箭头和抓取标记来自原生状态；数值、阶段和计时均放在图外。虚线与空心圆表示关闭异常规则的普通物理对照。
- Demo 默认显示运动轨迹及方向；Push / Throw 发生时标出动作箭头，绿色 F 箭头表示改变规律带来的作用力。`assets/scene-trajectories.js` 从当前影片对应的原始记录和相机投影绘制，随播放、暂停、进度、缩放与全屏同步；数据在播放时按需读取。已烘焙的轨迹保留原标注，所有影片统一叠加清晰的动作提示：Push / Throw 保持 12 px 字号，动作箭头为粗线、实心箭头头与浅色衬边，布局避开控件和物体。箭头表示原始动作方向，显示长度随可读性调整；4× 下提示约保留 1.1 秒，并在下一次动作前结束。带虚线对照的画面在图外显示简短图例：This world（实线）与 Ordinary physics（虚线）；其他画面只标注 Motion / Force。
- 所有场景演示影片均为 **60 fps**，来自 **500 Hz** 原生状态，以固定速度映射播放，不补造轨迹或插入定格。09、12、13 从实际当前位置继续运动，不重新摆回起点。新版下载包含六段相同解释和读数；总集为 **240 秒、1600×960、60 fps**，GIF 为 30 fps，视频与原生记录 ZIP 同步更新。
- 数学公式统一使用本地 STIX Two Math 字体与原生 MathML，包括完整规则中的行内公式、分式、绝对值和上下标，不依赖 CDN 或额外公式渲染引擎。反弹公式分开标注红砖与蓝砖。模型的 15 段说明使用简短句子保留触发条件与效果；源数据的完整论文规则不变，模型说明和参数选项同步缩短。数据图增大刻度字号，颜色交换的纵轴直接标记 Red / Blue。模型的计算结果使用统一的正文字号；原生演示的数据直接绘成曲线，去掉等待撞击等重复状态文字。
- 页面先展示静图，未播放的视频不下载。首屏物理引擎只在操作时加载；场景索引只含播放元数据和低清预览，完整测量数据不随首屏下载，测量数组单独按需读取。高清图解码前先显示内嵌预览，避免空白。预览服务压缩 JS / JSON / WASM，保留视频 Range 请求；视频和引擎下载超时会提供重试。
- 48 秒四幕概览与全屏演示模式；120 秒全场景 MP4、15 个逐场景 GIF 和合集可直接下载。
- 05 Case studies 将 Anomaly / Color swap / Tool design 三个案例切换和播放器合并为一张浅色卡片；点击案例直接从头播放整段影片。画面下方使用与 15 场景一致的独立进度滑杆，支持播放/暂停、重播、拖动回看、0.5×–4× 倍速（默认 4×）和全屏，不遮挡影片字幕。拖动时暂停预览，松手后保持拖动前的播放状态；手机滑杆独占一行。原始材料仍保存在下载数据中。
- 主结果的 Reports by scene 常显每个场景的 D/C/S 通过次数，所有模型、所有场景均可点击，包括 0/3 和正常对照。记录页默认只显示三次运行的判定、一句结果、前三条结论摘录和简短规律预览；点开结论可查看完整原文与引用轮次，其余结论、GPT-6.1-Sol 判分理由和完整规律按需展开。引用轮次可打开真实执行动作、反馈和前后观察。原始提交与行动前笔记也可展开，案例底部可下载完整 JSON ZIP，主结果下方提供全部 540 次主实验的合集，包含失败结果和正常对照；每个包均保留逐字节未改写的 `session.json` 与论文冻结的 `evaluation.json`，包括实际提示、场景、规则、参数、全部轮次、报告尝试与判分回复。哈希、实验索引及仅依赖 Python 标准库的 `verify.py` 随包提供，页面移除 Source details。合集覆盖主实验，控制实验与演化实验属于独立数据集；二进制物理回放也不属于 JSON 包。540 次运行、30,223 轮记录均按论文冻结的 session/eval 哈希核验，数据由 `scripts/prepare_result_evidence.py` 导出，按场景加载；网页查看引用时仍使用约 15.3 MiB 的精简逐轮档案，完整 ZIP 仅在点击下载时请求。正常对照单独标记接受或拒绝，不把缺失的 S/D 当作失败。
- 框架按论文 Figure 2 的“环境构建 → 自主探索 → 发现评估”三栏展示，标题精简为 `A cycle of discovery.`，节点只保留名称和一句说明；桌面流程区压至 400 px、底部说明区约 82 px，整节高度减少约 30%。保留世界与探索者的观察/行动循环、器材审核与安装、报告和完整记录进入评估、探索证据返回场景演化。金色通路单独显示隐藏规律进入评估者。光点按阶段沿实际连线流动；点击节点或阶段会固定当前通路并继续播放，弱化无关节点，暂停后恢复仍保留选择，重置回到完整轮播。完整记录直接连接探索者，表示所有探索回合均被记录；评估终点明确标为 D · Discovery，要求 C、S 同时通过。离屏或打开任意弹窗时暂停，减少动态效果设置默认静止。窄屏改为纵向排布并重算连线；线路标签置于线上方或线侧，保留完整的流动路径。实现位于 `assets/framework.js` 和 `assets/framework.css`。四个有视频的成功运行，在对应运行记录里可打开并排实验对照；影片、目标标记和原始轨迹保持同步。
- 每个场景的完整规律、适用对象与触发条件可展开阅读。
- 第三节左侧只展示 12 个模型的 D（Discovery）发现率条形，可按发现率排序；移除指标切换。点击模型或用上下方向键选择，桌面右侧显示三项比例、42 次运行中的通过数及所有场景计数；手机和平板点击模型后弹出详情。所有条形保留 0–100% 刻度。探索行为 L / ES / CS / CF / AF 和正常对照拒绝数仍保留，全部九项指标可下载 CSV。实现为 `assets/results.js` / `assets/results.css`，报告查看器为 `assets/result-evidence.js` / `assets/result-evidence.css`。
- Framework 后直接进入主结果，相关工作对照留在论文中。04 Controlled comparisons 独立放在主结果之后，三张紧凑卡片同时展示任务提示、预算和器材权限各自的 D/C/S/L/AF 全部数值，预算实验的独立基线说明常显。实现为 `assets/comparisons.js` / `assets/comparisons.css`。
- 三个案例影片分别为32秒 Astra/Gemini 对照、18秒颜色交换、21秒称重装置改造。选中后加载并播放；切换案例、离屏或切到后台时暂停。首次播放前也可直接拖动滑杆定位，键盘方向键可微调进度。
- 案例播放器居中，最大宽度 880 px，并随桌面视口高度收窄；在 1366×768 屏幕上视频约高 404 px，案例切换、画面和控制栏可一起查看。全屏包含画面与同一条控制栏，手机端也可用原生视频全屏。
- 案例视频使用首图相同的 Blender Cycles 材质与灯光重新渲染：珐琅红/蓝球、瓷砖地面、蓝灰金属和青绿色托盘，64 samples 并去噪。近景以剖视方式隐藏遮挡实验的玻璃墙与边框。保留原始 MuJoCo 状态中的位置、尺寸、红/蓝身份和仪器结构；分屏两侧独立调整影片时间，分别标出原始回合与模拟时间。颜色案例依次展示首次交换、再次交换、红球与红球碰撞；仪器案例依次展示滑出平盘、红球留在深盘、蓝球稳定称重。章节间切到后续试验，不模拟装置变形或构建过程。来源、视频及首图材质源码哈希在 `data/case-films.json`，逐帧原始状态哈希和时间映射在 `data/case-rendering.json`。生成入口为 `scripts/prepare_case_studio.py`，复用 `scripts/prepare_case_films.py` 的案例选段与字幕；`scripts/blender_case_films.py` 负责渲染。播放器为 `assets/case-films.js` / `assets/case-films.css`。
- 06 Scene evolution 提供 Demo / Experiment 两个入口。Demo 默认按需播放三个已接受场景的演示视频，支持原生暂停、拖动和全屏；Experiment 独立加载原生模型，让用户自行推动、拖动、旋转、暂停、重置与调速，不执行预设干预。模式切换暂停另一边并保留进度，切换世界重新初始化。简述和 Trace → design 保持各一句，原始 trace、回合号与完整规则收在折叠参考区；演化评测表放在 06 的同一展示框内，紧接 Demo / Experiment 下方。data/evolution/ 保存原始 trace、冻结设计、模型、准备位置与源哈希，视频来源保存在 data/evolution-demos.json。移动端支持触摸；减少动态效果设置下不自动播放。实现为 assets/evolution.js、assets/evolution-physics.js 和 assets/evolution.css。
- 匿名论文、540 条结果记录、原始 prompt、案例笔记，以及三张结果图的 SVG/PNG 下载。

## 论文表格对应

| 论文表格 | 项目页呈现 |
| --- | --- |
| Table 1 · 场景总览 | 01 场景目录与逐场景演示 |
| Table 2 · 相关工作对照 | 保留在论文中，项目页不重复展示 |
| Table 3 · 主结果与探索行为 | 03 交互图及同屏模型详情，全部九项指标 |
| Table 4 · 控制实验 | 04 三组常显对照卡片，全部五项指标 |
| Table 5 · 场景演化案例 | 06 原始 trace、三种演化的参考说明及实时交互 |
| Table 6 · 演化评测 | 06 与 Demo / Experiment 同框展示五行 D/C/S 结果 |
| Table 7 · 基础场景规律 | 01 的 Demo 侧栏展示当前场景规则与公式 |
| Table 8 · 演化场景规律 | 06 的 Trace reference & full rule 展示精确规则与冻结设计 |
| Table 9 · 动作接口 | 论文附录保留参数和接口参考 |

## 结果口径与来源

`data/paper.js` 从当前论文冻结的 GPT-6.1-Sol 评价导出。主实验包含 12 × 15 × 3 = 540 条记录；每个模型的 D/C/S 以 42 个改变物理规律的场景运行计算，正常对照单独统计。页面的三项发现指标、五项探索指标及对照拒绝数均与源码表格一致。

源文件哈希在 `data/provenance.json`。预算实验使用无上下文压缩的匹配基线，其 100-turn 条件与主实验基线不同。场景演化另有一组原始场景运行，因此其 Scene 14/15 数值与主实验逐场景结果不同。网页已说明这两个区别。

主视频精选 Scene 07 r3、Scene 06 r1、Scene 14 r2、Scene 15 r3。它们全部在论文当前 GPT-6.1-Sol 评分中同时通过 C/S。原始主实验 Astra 共7个成功 runs，分布为Scene 06两次、07一次、14一次、15三次。来源在 `data/discovery-provenance.json`，完整笔记和报告在 `downloads/successful-runs.json`。

SVG 交互和 illustration MP4/GIF 是用于解释规律的简化模型，不作为真实探索证据。普通摩擦、接触或运动在部分场景中被简化或省略，每个场景底部注明范围。

`Demo` 直接运行 `scenes/base_15.json` 的原始物理程序，保留物体大小、颜色、质量、摩擦、重力与碰撞规律。初始位置按公开脚本布置；连续碰撞示例不再摆回起点，记录每次推动前的实际位置。当前数据包含准备位置、干预、原始规则回调事件、源哈希、500 Hz 状态采样及关闭异常规则的普通物理对照。视频取最近的原生状态，不使用光流补帧；玻璃外壳和展示底座仅用于呈现。这些是专门制作的演示，不是模型自主探索，不计入主实验的 540 条结果。

成功探索视频和研究问题案例来自原始模型实验存档。三种素材的来源分别标识；页面播放秒数与模拟 counts 分开显示。

原有图解导出依次包括：普通地砖的匹配下落、吸引对象配对、等高度/等速度/等冲量、重力相位、制动阈值、发射方向、反弹高度、发射冲量、经过/绕开/越过区域、能量区内外、球与墙碰撞、重复与持续接触、第三次接触、停止红球后的延迟复制，以及零/非零干预。可通过 `?scene=07#worlds` 直接打开指定场景。

`assets/scene-physics.js` 实现 15 个场景的浏览器规则，`assets/scene-live.js` 管理实时交互与模型释放；`assets/atlas.js` 管理 Demo 侧栏中的 15 个可调示意模型及静态图解导出，`assets/motion.js` 维护四幕概览、共享绘图及导出时钟；布局分别在同名 CSS 中。数据和真实视频独立保留，调整动效无需改实验记录。

回放由 `runs` 中保存的 MuJoCo 模型版本和状态恢复，没有重新运行探索或推进物理。画面进行相机、灯光、房间剖视和 sRGB 显示转换；物体位置、尺寸、原始颜色及规律均保留。视频取最近的记录帧，不插值物体轨迹。案例短片按“观察、区分解释、进一步验证”串联选定实验，画面下方随进度更新说明；播放器显示影片时间，原始回合与模拟时间保存在来源记录中。短片进行了播放速度调整。

原始笔记与网页解释分别展示。颜色交换和器材案例来自 500-turn 条件，是精选案例，未并入主实验指标。案例解释不代替完整的发现评价。

## 更新素材

页面可直接使用，以下脚本仅用于在论文或源素材变化后重新导出。

本轮首屏和场景展示的检查与更新（已完成的渲染无需重跑）：

```bash
python scripts/verify_front.py --url http://127.0.0.1:8765 --require-hd
python scripts/verify_discovery_films.py
python scripts/verify_pages.py --url http://127.0.0.1:8782/longchang/
python scripts/verify_oracle_records.py
python scripts/verify_shared_room.py
python scripts/verify_smooth_motion.py
python scripts/verify_playback.py
python scripts/verify_analysis.py
python scripts/verify_demo_model.py
python scripts/verify_model_interaction.py
python scripts/verify_grab_responsiveness.py
python scripts/verify_explained_views.py
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
# 六个带轨迹、对照、计时的连续演示（支持复用已有渲染缓存）
python scripts/build_explained_demos.py --ffmpeg /path/to/ffmpeg
python scripts/oracle_catalog.py
python scripts/publish_clear_media.py --ffmpeg /path/to/ffmpeg
python scripts/export_oracle_signals.py
python scripts/package_oracle_demos.py
python scripts/package_physics_demos.py --ffmpeg /path/to/ffmpeg
python scripts/prepare_scene_index.py
```

渲染脚本使用项目现有 MuJoCo/Blender Python 环境。统一封顶版使用 128 samples、去噪与缓存球面光照；早期全景使用 256 samples 背景和 64 samples 动态区域。近景使用 Cycles 房间背景、缓存的 Cycles 球面光照和投影软阴影，以亚像素位置合成；相机由同一房间的裁切范围推导，物体位置与半径不变。近景为阅读方便增强灰球和黄色区的显示对比，记录中的原始 RGBA 保留。统一封顶版的所有全景也使用这一合成方式。`assets/clarity.css` 控制布局，`assets/room-world.js` 控制首屏实时物理，`scripts/oracle_catalog.py` 保存一句话中英说明。场景正式名称仍由论文自动读取。

固定房间配置在 `data/shared-room.json`。`verify_shared_room.py` 比较每次渲染实际构建的 Blender 网格、相机变换与灯光签名，防止仅统一长宽比却仍改变房间尺寸。Table 1 图标来源与哈希在 `assets/table1/source.json`。

Experiment 从 `data/interactive-scenes/` 按需加载原生模型、质量、摩擦、接触参数与准备位置。所有场景共享同一个 WASM 实例，每次只保留一个场景渲染器；切换到 Demo 或离开屏幕后暂停物理。交互房间封闭玻璃墙和顶面的内表面与原程序的 x/y ±6、z 0–12 边界对齐；Demo 的玻璃房与 Experiment 使用相同边界与同一相机投影；两种视图的画面区域也保持等高。Push 按冲量/质量改变速度，Drag 使用原始 Workshop.apply 的质量相关抓取力、当前重力补偿、100 的力上限与 2 的移动速度上限，手部可达高度仍为 3。竖直拖动直接控制高度，左右拖动沿当前视角移动，按住 Shift 拖动则在同一高度平面滑动；松手或取消触摸会释放物体。拖放不触发 PUSH/THROW 的事件；延迟与第三次接触的状态持续保存到重置。

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
python scripts/prepare_discovery_films.py --ffmpeg /path/to/ffmpeg

# 从原始状态用首图的 Cycles 材质生成三个案例影片与来源记录
python scripts/prepare_case_studio.py --ffmpeg /path/to/ffmpeg --samples 64 --workers 4
# 只出样帧（不替换页面影片）：增加 --preview
python scripts/verify_case_films.py --url http://127.0.0.1:8765

# 在论文接受的三个演化场景中运行脚本化干预并导出 demo
python scripts/prepare_evolution_interactive.py
python scripts/verify_evolution_demos.py --url http://127.0.0.1:8765

# 强制重新渲染现有视频与场景图
python scripts/render_replays.py --ffmpeg /path/to/ffmpeg --force

# 核对本地链接、数据、所有主实验指标与来源哈希
python scripts/verify_site.py

# 可选：使用 Playwright 检查真实浏览器交互及响应式布局
python scripts/verify_browser.py

# 检查框架的数据通路、播放生命周期、键盘交互和 320–1440 px 布局
python scripts/verify_framework.py --url http://127.0.0.1:8765

# 从冻结评测导出全部 540 次运行的报告、判分与原始逐轮记录
python scripts/prepare_result_evidence.py
python scripts/verify_result_evidence.py --url http://127.0.0.1:8765

# 核对轨迹与原生记录、相机投影、播放和缩放的同步
python scripts/verify_trajectories.py --url http://127.0.0.1:8765

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
