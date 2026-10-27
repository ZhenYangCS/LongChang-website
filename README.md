# LongChang project page

纯静态英文论文主页；作者区可独立切换为匿名形式，可直接部署到 GitHub Pages，线上不需要 Python 服务、API key 或后端。部署步骤见 [PAGES.md](PAGES.md)，已同时提供独立站点仓库和当前目录结构的 GitHub Actions 配置，仅手动运行工作流才会部署，普通推送不会上线。

以下 Python 命令仅供本地预览使用，不属于线上运行依赖：

```bash
python3 project_page/scripts/serve.py --bind 0.0.0.0 --port 8765
```

在服务器本机可访问 <http://127.0.0.1:8765>。从自己的电脑访问时，应使用服务器可达的 IP/域名加 `:8765`，或先建立 SSH 端口转发；浏览器中的 localhost 指的是浏览器所在电脑。预览服务器支持视频字节范围请求，并要求 HTML/JS/CSS 重新核验缓存，便于持续微调。

当前预览服务独立运行在 `longchang-page` tmux 会话，可用 `tmux attach -t longchang-page` 查看。同一房间的 15 段动画在 `longchang-shared` 中导出，日志为 `/tmp/longchang-shared-build.log`，不会随终端命令结束而停止。

整个 `project_page/` 目录可部署到任意静态托管服务，也支持站点子目录。无需前端编译、API key 或实时模拟后端。GitHub Actions 用 Bash 复制已经生成的静态文件，并合并普通样式与脚本以减少请求。字体、图片、视频和数据均为本地文件。Code 按钮链接到公开 GitHub 仓库：`https://github.com/EnVision-Research/LongChang`。

Paper 暂时也链接到 LongChang GitHub 仓库，待 arXiv 地址确定后，再更新 `index.html` 首屏及 `<noscript>` 中的 Paper 链接。Paper 与 Code 均在新标签页打开网页，不触发文件下载。

## 内容

- 章节按“15 个场景 → Framework → 主结果 → Discovery in Practice（控制实验与案例）→ 场景演化”排列，成功探索从结果中的场景格子打开。页面以场景演化收尾，取消单独的 Materials 章节及导航入口；论文与 Code 位于首屏，补充素材保存在项目文件中。
- 页头采用居中的论文标题布局：取消顶部导航与重复的项目名，显示左侧玻璃房图标、居中的 LongChang、斜体论文标题、独立作者区及统一深色 Paper / Code / BibTeX 按钮。使用本地 Inter 与 Noto Serif 字体；桌面项目名 57.6 px、手机 41.6 px，字体与间距按参考页取值。图标内两颗彩色球同步眨动，减少动态效果时静止。样式在 `assets/hero.css`，图标是内联 SVG。五个章节使用独立的大标题，见 `assets/chapters.css`。Explore the Worlds 与 Framework 之间保留充分留白，以通栏细线、中央短线和浅绿色章节底色分隔。
- 五个章节与页头统一使用页面的浅色底色（`--paper`），分隔沿用两侧渐淡的细线与中央空心菱形；桌面章节上下留白 40 px，手机 32 px，分隔装饰不参与点击或滚动布局。
- 命名说明放在 LongChang 标志上方，以 Newsreader 衬线斜体作题注，紧接项目名，与下方作者信息区分；项目名下方留出 26 px 间距，再接论文标题。首屏按命名说明、项目名、论文标题、作者信息、资源入口排列。作者、单位、通讯作者说明分层居中排列，单位之间以留白分隔，手机上单位按两列排列。顶部只保留 Paper、Code、BibTeX 入口。页面不再使用与“无任务提示的自主科学发现”不够贴切的修身或知行语录。
- 居中论文标题下方采用左侧 Abstract、右侧 Figure 1 玻璃房的布局；论文摘要分四段呈现研究动机、探索框架、自动审核与场景演化、评测结果。整个区块沿用下方章节的同一容器，桌面两栏等宽、间隔 48 px，取消摘要和图示内部的独立宽度上限；玻璃房保持原比例占满右栏，让图的右边缘与后续章节一致。窄屏先显示摘要再显示全宽玻璃房，首图交互入口保持在图下。
- 首屏先显示 Figure 1 原图。点击 Push / Drag / Rotate 后加载本地 MuJoCo WASM，用原始 `workspace.xml` 实时计算推动、拖放、碰撞、摆锤和天平运动；Three.js 绘制玻璃、金属、珐琅与阴影。支持转视角、缩放、键盘推动和重置。
- 首页、15 个基础场景和三个演化场景共用 `assets/room-world.js` 的运动中 Push：优先匹配当前位置，Push 额外接受最近 250 ms 的已显示位置，Drag 保持 120 ms；推力按鼠标或触点的相对位移计算，箭头和施力点随选中的物体移动。操作不暂停、回退或重置物理，场景 14 的延迟复制和场景 15 的干预计时仍由原有规律处理。`verify_moving_push.py` 用真实鼠标和触屏验证连续运动中的追加推力及方向。
- 首图按材质合并静态几何，减少重复绘制；所有设备保持原有高画质材质、软阴影、2048 阴影贴图及最高 2× 像素密度，不再按帧率自动降低分辨率或替换材质。物体位姿未改变时复用阴影贴图，颜色映射和控制栏避免重复计算与更新。物理保持固定步长，物体仍在运动时不会被固定时限强制停住；离开屏幕时暂停计算。
- 左侧为五行三列的 Table 1 场景目录，保留原编号、原名和论文 TikZ 机制图；右侧只展示场景名、一句通俗说明和演示。选择卡片为五行三列，左栏最多 300 px，列间距 8 px，整体与右侧视频面板等高，五行自适应均分高度，卡片内文字与图标保持紧凑，并适配笔记本屏幕，方向键可在网格中移动。手机使用下拉目录。移除重复的 WORLD / TABLE 1 标题及自动轮播入口；顶部合集下载与重复的前后切换箭头已移除；完整规则、模型说明和演示数据曲线统一整合在 Demo 视频右侧（手机下方），取消独立的 Rule & data 入口和场景视频、数据下载按钮；Demo 与 Interactive 默认 4×，均可切换 0.5×、1×、2×、4×。
- **场景命名以 ACL 论文为唯一来源**：`scripts/paper_scenes.py` 从当前总览表读取 01–15 的正式名称，从附录读取对应规律与作用范围；网页、案例、演示标题和重新导出的字幕共用这份数据。
- 结果区左侧在模型条形图下展示探索行为（含对照的 45 次运行）和发现结果（42 次改变规律的运行）。发现率是两项检查同时通过的比例；D/C/S 保留原始通过数和分母。右侧保留逐场景报告；手机合入模型详情。
- **两个入口**：`Demo` 保留原生物理视频，并在视频右侧直接展示原 Explain 的全部 15 个可调模型；`Interactive` 保留真实物理交互。主场景和演化模型的离散选项全部展开为带简洁示意的卡片，选中状态明显，支持鼠标、触屏及方向键；连续参数仍用滑杆，拖球、相位选择、播放/重置和全屏继续可用，标题统一为 Rule illustration，并用一句操作提示说明怎么使用；Scene rule 上下加分隔线，与选项和图解分开。参数只影响示意图，不改变视频进度。右侧只展示可调模型、Scene rule 和 MathML 公式；原录制曲线归入左侧视频下方，标为 Video data，竖直时间游标按视频帧同步。模型与数据按可见性运行和加载，手机顺序排列。示意模型由 `assets/atlas.js` 和 `assets/model-interaction.js` 管理，合并布局在 `assets/demo-model.css`：桌面同排显示目录、视频和可调模型，右侧使用 `assets/model-options.js` 统一卡片选择与原模型状态；`assets/compact-model.css` 将规则放在参数和图解之前，以统一的标题、公式、卡片和结果栏组织内容，播放按钮、公式及计算结果紧凑排列，常见笔记本尺寸无需内部滚动；较窄屏幕将目录收为下拉框，保留视频与模型并排；手机上下排列。切换到 Interactive 会隐藏并暂停数学演示。原生模拟仍使用 Push / Drag / Rotate 和一条播放控制栏。
- `Demo` 和 `Interactive` 共用 12×12×12 的封闭玻璃房及物体真实尺寸。Demo 使用较低、略偏侧的固定近景，保留砖面纵深并让上抛与下落更明显；离地的球通过淡虚线连接真实地面投影，完整包含运动轨迹和作用区域；只保留播放、进度、倍速和全屏，不提供画面缩放、拖动或房间切换。Interactive 恢复原来的斜视全景，能同时看到立方体的顶面和侧面，保留 Push / Drag / Rotate；新增 Wheel zoom 开关，默认 Off，三种工具下普通滚轮均用于翻页；打开后滚轮直接缩放。选择在两处 Try it 间同步，并保存到浏览器以便刷新后恢复。全屏始终允许滚轮缩放，退出后恢复之前的选择；Ctrl/⌘ + 滚轮不受开关影响。两处 Try it 均提供 − / + / Fit 视角按钮，+ 对准当前物体群放大，Fit 只恢复相机，不重置物理；手机支持双指缩放，按钮触控尺寸至少 44 px。两个视角分别由 room_camera() 和 interactive_camera() 定义，重新生成 Demo 不会覆盖交互相机。场景标题和一句话介绍统一居中；两个章节的 Demo / Interactive 均固定在面板左上角的独立一行，采用带播放/鼠标图标的分段按钮与 Watch / Try it 提示；当前模式用深绿色实底和白字突出，按钮触控高度至少 44 px，所有屏幕尺寸切换模式时保持位置不变。
- 场景 **05、09、10、11、14、15** 使用新的连续因果演示：05 显示制动与普通物理虚线对照；09 在同一次运动中完整进入和离开灰砖；10 同时发射相同初速度的球，显示黄色区域内外的速度分化；11 对比碰撞分离后的加速与普通路径；14 明确呈现发射、抓住红球、倒计时和 12 秒后的速度复制；15 显示力的开关、再次推动重置倒计时、16 秒时恢复。轨迹、速度箭头和抓取标记来自原生状态；数值、阶段和计时均放在图外。虚线与空心圆表示关闭异常规则的普通物理对照。
- Demo 的相机与高度投影线由 `scripts/refresh_demo_camera.py`、`scripts/render_clear_scenes.py` 和 `scripts/build_detail_views.py` 生成；仅重新投影已有原生状态，不重算物理或改变时间映射。Demo 默认显示运动轨迹及方向；Push / Throw 发生时标出动作箭头，绿色 F 箭头表示改变规律带来的作用力。`assets/scene-trajectories.js` 从当前影片对应的原始记录和相机投影绘制，随播放、暂停、进度、窗口尺寸与全屏同步；数据在播放时按需读取。已烘焙的轨迹保留原标注，所有影片统一叠加清晰的动作提示：Push / Throw 保持 12 px 字号，动作箭头为粗线、实心箭头头与浅色衬边，布局避开控件和物体。箭头表示原始动作方向，显示长度随可读性调整；4× 下提示约保留 1.1 秒，并在下一次动作前结束。带虚线对照的画面在图外显示简短图例：This world（实线）与 Ordinary physics（虚线）；其他画面只标注 Motion / Force。
- 所有场景演示影片均为 **60 fps**，来自 **500 Hz** 原生状态，以固定速度映射播放，不补造轨迹或插入定格。09、12、13 从实际当前位置继续运动，不重新摆回起点。新版下载包含六段相同解释和读数；总集为 **240 秒、1600×960、60 fps**，GIF 为 30 fps，视频与原生记录 ZIP 同步更新。
- 数学公式统一使用本地 STIX Two Math 字体与原生 MathML，包括完整规则中的行内公式、分式、绝对值和上下标，不依赖 CDN 或额外公式渲染引擎。反弹公式分开标注红砖与蓝砖。模型的 15 段说明使用简短句子保留触发条件与效果；源数据的完整论文规则不变，模型说明和参数选项同步缩短。数据图增大刻度字号，颜色交换的纵轴直接标记 Red / Blue。模型底部用 13 px 的单行短字幕说明当前现象，优先精简文案并保留关键数值，随选项和播放时刻更新，避免把实时状态与泛化规律提示混在一起；原生演示的数据直接绘成曲线，去掉等待撞击等重复状态文字。
- 视频曲线明确标注纵轴物理量及单位：高度、速度、垂直速度、力、相对重力、能量或颜色；横轴标注模拟时间。显示中的 s 为模拟秒，与原生记录的计时值一致。
- 页面先展示静图，未播放的视频不下载。首屏物理引擎只在操作时加载；场景索引只含播放元数据和低清预览，完整测量数据不随首屏下载，测量数组单独按需读取。高清图解码前先显示内嵌预览，避免空白。预览服务压缩 JS / JSON / WASM，保留视频 Range 请求；视频和引擎下载超时会提供重试。
- 48 秒四幕概览与全屏演示模式；120 秒全场景 MP4、15 个逐场景 GIF 和合集可直接下载。
- 04 Discovery in Practice 与上方场景区使用相同的通栏宽度，使用并列的左右卡片：左侧三组对照均分可用高度，右侧三个选项采用论文小节原名 Forming Research Questions / Validating Scientific Claims / Using Experimental Resources。切换案例时按当前案例的内容调整高度，隐藏案例不再撑高播放器；同一案例的阶段说明保留自身高度，避免播放时跳动；每个案例都有标题和结论。每个案例先说明实验背景，再随播放显示实验目的、观察及推理，结尾给出与论文分析主题对应的结论；第一例以是否主动选择异常作为研究问题为主线，对照 Astra 的追查与 Gemini 的既定计划；明确红球先向南被推、停止、随后自行向北运动，结尾总结研究选择的差异；隐藏力的规律在场景演示中呈现，第二例写清交换/独立翻转的不同预测，第三例说明平盘失效、装置改造和红蓝球分别得到 −0.3 brick 稳定位移读数，去掉重复的泛泛结语；手机将双模型说明纵向排列。保持紧凑标题与视频高度，保留理解案例所需的上下文，独立基线等设置集中到 Full results & setup。点击案例直接从头播放整段影片。播放条紧接画面，观察过程和结论位于下方；支持播放/暂停、重播、拖动回看、0.5×–4× 倍速（案例默认 2×）和全屏，不遮挡影片字幕。拖动时暂停预览，松手后保持拖动前的播放状态；手机改为上下卡片，滑杆独占一行。原始材料仍保存在下载数据中。
- 主结果的 Reports by scene 保留按模型、场景与三次运行核对结果。报告弹窗只分 Summary / Full report，默认显示本次判定与英文评估总结；Full report 直接展示全部模型结论、报告中的实验、原始判分理由和参考规律，不再层层展开。三个 Run 用紧凑标签切换；引用轮次可打开原始动作、反馈与观察，单次完整记录仍可下载。主结果下方将 All records / Summaries 两个下载入口放在一起。全部 540 次总结按 episode、场景、重复编号及评估哈希匹配原判分，不重新评分；540 份 session/evaluation 和 30,223 轮原始记录经过哈希核验。数据与 ZIP 仍按需加载，正常对照单独显示接受或拒绝。
- 框架按论文 Figure 2 的“环境构建 → 自主探索 → 发现评估”三栏展示，五步导航置顶，步骤或节点摘要紧接导航，桌面摘要区约 82 px；删除摘要中的重复阶段编号，保留输入输出。手机按视口预留稳定的摘要高度，切换内容时流程图不会上下跳动。节点只保留名称和一句说明，桌面流程区约 400 px。保留世界与探索者的观察/行动循环、器材审核与安装、报告和完整记录进入评估、探索证据返回场景演化。金色通路单独显示隐藏规律进入评估者；Hidden law / Evaluation only 标签放在 Judge 上方的入线旁，在桌面和手机均可见，与左侧 Claims 标签分开。光点按阶段沿实际连线流动；点击节点或阶段会固定当前通路并继续播放，弱化无关节点，暂停后恢复仍保留选择，重置回到完整轮播。完整记录直接连接探索者，表示所有探索回合均被记录；评估终点明确标为 D · Discovery，要求 C、S 同时通过。离屏或打开任意弹窗时暂停，减少动态效果设置默认静止。窄屏改为纵向排布并重算连线；线路标签置于线上方或线侧，保留完整的流动路径。实现位于 `assets/framework.js` 和 `assets/framework.css`。四个有视频的成功运行，在对应运行记录里可打开并排实验对照；影片、目标标记和原始轨迹保持同步。 Explore 到 Evaluate 的证据线沿栏间通道进入 judge 中心，窄屏从记录底部单独引出，避免与记录和反馈路线相交；构建与评估节点在各自栏内居中。
- 每个场景的完整规律、适用对象与触发条件可展开阅读。
- 第三节左侧只展示 12 个模型的 D（Discovery）发现率，固定按论文顺序排列。图表下方用虚线分开两组指标卡：Discovery outcome 的 D/C/S 显示百分比、简短定义和统一的 42 次改变规律场景统计口径，D 明确标注 C + S must pass；Exploration behavior 的五项指标各自标明轮数上限或分母，覆盖含正常对照的 45 次运行。不重复显示报数段落或百分比与通过次数两套数值，精确通过次数保留在提示中。右侧模型名称旁不再放 CSV 下载图标，场景报告和完整原始 JSON 下载保持可用。1000 px 及以下通过模型详情弹窗显示指标；实现为 assets/results.js 和 assets/results.css。
- Framework 后直接进入主结果，相关工作对照留在论文中。04 Discovery in Practice 合并控制实验与案例分析：桌面左侧按论文 Table 4 标为 Task guidance / Turn budget / Apparatus access；任务引导与器材访问明确显示 Discovery rate，预算实验显示 Mean turns used；任务对照明确标为 Without guidance / With guidance；Full results & setup 只保留三张对照表，标题简要标记引导内容、轮数和预算实验的独立基线；删除重复的模型、构建权限与案例来源段落，右侧为三个可切换的原始案例影片；手机上下排列，结论与数字同排。D/C/S/L/AF 完整数据与实验设置收在 Full results & setup 中，预算实验的独立基线和无上下文压缩条件简注在表格标题中。页面去掉独立的 Scene / run 来源行；原始来源仍记录在素材数据中，500-turn 精选案例不作为 100-turn 控制实验的直接证据。原有 #controlled、#explore 和 #cases 链接仍可用。实现为 `assets/comparisons.js` / `assets/comparisons.css`。
- 三个案例影片分别为32秒 Astra/Gemini 对照、18秒颜色交换、21秒称重装置改造。选中后加载并播放；切换案例、离屏或切到后台时暂停。首次播放前也可直接拖动滑杆定位，键盘方向键可微调进度。
- 第一个案例明确比较“发现异常后是否追查”：Astra 改变计划，检验红球重新运动的延迟，并进一步推动蓝球；Gemini 继续竖直抛射与碰撞测试，未检验重新运动的原因。页面按观察、后续实验、结果三步显示可读文字，拖动进度时同步切换；两列来自同一设置下的独立运行。案例画面按窗口高度限制在 210–280 px，保留完整画面；模型名与双列观察对应视频的两半；1280×512 视频只展示原始实验近景、返回观察中的静止/运动状态，以及推动/抛射后的真实模拟计时；Gemini 的贴墙重新运动标为 Log，并说明位移几乎不可见。说明和结论放在视频外，案例默认 2× 以留出阅读时间。`scripts/prepare_case_question.py` 复用已有渲染帧合成标注，逐帧状态和计时在 `data/case-question-cues.json`；完整渲染入口会自动调用它。
- 案例播放器位于 04 的右栏，随栏宽缩放；手机上下排列，切换、画面、控制栏和阶段说明放在同一框内。全屏包含画面与同一条控制栏，手机端也可用原生视频全屏。
- 案例视频使用首图相同的 Blender Cycles 材质与灯光重新渲染：珐琅红/蓝球、瓷砖地面、蓝灰金属和青绿色托盘，64 samples 并去噪。近景以剖视方式隐藏遮挡实验的玻璃墙与边框。保留原始 MuJoCo 状态中的位置、尺寸、红/蓝身份和仪器结构；分屏两侧独立调整影片时间，原始回合与模拟时间保存在来源记录中。颜色案例依次展示首次交换、再次交换、红球与红球碰撞；仪器案例依次展示滑出平盘、红球留在深盘、蓝球稳定称重。章节间切到后续试验，不模拟装置变形或构建过程。来源、视频及首图材质源码哈希在 `data/case-films.json`，逐帧原始状态哈希和时间映射在 `data/case-rendering.json`。生成入口为 `scripts/prepare_case_studio.py`，复用 `scripts/prepare_case_films.py` 的案例选段与字幕；`scripts/blender_case_films.py` 负责渲染。播放器为 `assets/case-films.js` / `assets/case-films.css`。
- Scene Evolution 与 15 Worlds 共用 `assets/scene-layout.css`，桌面目录、视频和规则图解等高，手机使用单一下拉选择器。原场景 15 和 14 位于选择栏顶部；三个演化选项各自显示发现次数（GPT-6-Astra，3 次运行），作为演化后难度的简明信息，手机显示当前所选场景的发现次数。Demo 保留规则图解、版本化视频与同步原始数据；Interactive 隐藏解释面板。
- 演化区保留“Scene 15 → 生成 / 细化”和“Scenes 15 + 14 → 组合”的来源关系。原场景 15 和 14 标注 Passed，指选取的来源运行均通过规律正确性与证据支持评测；场景 15 的中途错误判断已在最终通过前纠正。原场景旁解释这一经历和延迟复制规律；去掉 Why this design 和 Full design & rule 入口，沿用基础场景的演示、规则图解与交互方式。
- 三段演化 Demo 使用 15 个基础场景的正面斜俯视方向、Blender Cycles 材质及 1600×800 / 60 fps 近景，地板覆盖全部画面。播放器按区域铺满，检查球体、轨迹和力箭头都留在可见区域；竖屏全屏时保留完整构图。`scripts/refresh_evolution_media.py` 从 `data/shared-room.json` 读取公共视角，先核对冻结的原生状态、动作和时间映射，再发布视频、封面与版本索引；物理记录和评测数值不变。
- Demo 近景隐藏玻璃、框架和装饰底座，避免边沿形成遮挡视线的竖杠；三个演化视频及场景 09 的视频、封面已同步导出。`refresh_demo_camera.py` 的后续近景导出也采用此设置，物理碰撞边界、记录中的轨迹和计时保持原样。
- 演化视频与封面通过 `data/evolution-media.js` 使用内容哈希版本地址，避免浏览器继续播放更新前的遮挡版本。两个导出入口都会自动重建该索引；仅替换媒体文件时可运行 `python scripts/prepare_evolution_media_index.py` 同步版本。
- 匿名论文、540 条结果记录、原始 prompt、案例笔记，以及三张结果图的 SVG/PNG 下载。

- 场景 13 的 Demo 图解使用正面红蓝球和可点击的 1 / 2 / 3 步骤，清楚显示前两次无额外跳跃、第三次双球向上跳；持续接触与撞墙作为对照。图解标题为 Count the touches，说明用简短英文，保留向上速度 4 和原始两球的计数范围。步骤按钮与图解播放只控制示意模型，不改动左侧原始影片、进度或测量数据。

## 论文表格对应

| 论文表格 | 项目页呈现 |
| --- | --- |
| Table 1 · 场景总览 | 01 场景目录与逐场景演示 |
| Table 2 · 相关工作对照 | 保留在论文中，项目页不重复展示 |
| Table 3 · 主结果与探索行为 | 03 交互图及同屏模型详情，全部九项指标 |
| Table 4 · 控制实验 | 04 三条发现率结论；完整五项指标与设置按需展开 |
| Table 5 · 场景演化案例 | 05 原始 trace、三种演化的参考说明及实时交互 |
| Table 6 · 演化评测 | 分数直接并入三个演化选项卡；同栏底部保留两个原场景基线 |
| Table 7 · 基础场景规律 | 01 的 Demo 侧栏展示当前场景规则与公式 |
| Table 8 · 演化场景规律 | 05 的 Trace reference & full rule 展示精确规则与冻结设计 |
| Table 9 · 动作接口 | 论文附录保留参数和接口参考 |

## 结果口径与来源

`data/paper.js` 从当前论文冻结的 GPT-6.1-Sol 评价导出。主实验包含 12 × 15 × 3 = 540 条记录；每个模型的 D/C/S 以 42 个改变物理规律的场景运行计算，正常对照单独统计。页面的三项发现指标、五项探索指标及对照拒绝数均与源码表格一致。

源文件哈希在 `data/provenance.json`。预算实验使用无上下文压缩的匹配基线，其 100-turn 条件与主实验基线不同。场景演化另有一组原始场景运行，因此其 Scene 14/15 数值与主实验逐场景结果不同。网页已说明这两个区别。

主视频精选 Scene 07 r3、Scene 06 r1、Scene 14 r2、Scene 15 r3。它们全部在论文当前 GPT-6.1-Sol 评分中同时通过 C/S。原始主实验 Astra 共7个成功 runs，分布为Scene 06两次、07一次、14一次、15三次。来源在 `data/discovery-provenance.json`，完整笔记和报告在 `downloads/successful-runs.json`。

SVG 交互和 illustration MP4/GIF 是用于解释规律的简化模型，不作为真实探索证据。普通摩擦、接触或运动在部分场景中被简化或省略，每个场景底部注明范围。

`Demo` 直接运行 `scenes/base_15.json` 的原始物理程序，保留物体大小、颜色、质量、摩擦、重力与碰撞规律。初始位置按公开脚本布置；连续碰撞示例不再摆回起点，记录每次推动前的实际位置。当前数据包含准备位置、干预、原始规则回调事件、源哈希、500 Hz 状态采样及关闭异常规则的普通物理对照。视频取最近的原生状态，不使用光流补帧；玻璃外壳和展示底座仅用于呈现。这些是专门制作的演示，不是模型自主探索，不计入主实验的 540 条结果。

成功探索视频和研究问题案例来自原始模型实验存档。三种素材的来源分别标识；页面播放秒数与模拟 counts 分开显示。

原有图解导出依次包括：普通地砖的匹配下落、吸引对象配对、等高度/等速度/等冲量、重力相位、制动阈值、发射方向、反弹高度、发射冲量、经过/绕开/越过区域、能量区内外、球与墙碰撞、重复与持续接触、第三次接触、停止红球后的延迟复制，以及零/非零干预。可通过 `?scene=07#worlds` 直接打开指定场景。

新的 15 场景视角由 `scripts/refresh_demo_camera.py` 从已准备的 unified/explained 状态缓存重建；只重新渲染相机、静态房间和球体光照，原始记录、时间映射、触发事件保持原样。先渲染全部媒体，再用 `--publish` 更新 Demo 相机、索引和视频哈希。交互相机单独导出；更改交互相机后运行 `render_interactive_previews.py` 对齐加载预览。以上均为构建步骤，GitHub Pages 只需发布静态文件。

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
python scripts/verify_video_data.py
python scripts/verify_model_interaction.py
python scripts/verify_grab_responsiveness.py
python scripts/verify_explained_views.py
python scripts/verify_zoom.py
python scripts/verify_live_rules.py --prepare --audit
python scripts/verify_live_rules.py --audit
python scripts/verify_live_interaction.py
python scripts/verify_push_responsiveness.py
python scripts/verify_moving_push.py
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

Interactive 默认选择 Drag，初始静止，抓住物体或点击播放后才运行；鼠标移到标签上或键盘聚焦时预加载。首次仍按住的 Drag 会在加载后交给画布，提前松开则取消。已松手完成的 Push 会在加载后执行一次；重置、切换工具、离开视图或取消操作会清除待执行手势。Push 使用最终松手位置，并允许瞄准点越过墙面，避免推力方向被坐标夹紧反转；物体仍受真实墙面碰撞约束。空白处点击不会启动物理。`assets/images/interactive-room-*.webp` 与真实初始视角、物体位置一致，可用 `scripts/render_interactive_previews.py` 在构建时重新生成。Interactive 从 `data/interactive-scenes/` 按需加载原生模型、质量、摩擦、接触参数与准备位置。所有场景共享同一个 WASM 实例，每次只保留一个场景渲染器；切换到 Demo 或离开屏幕后暂停物理。交互房间封闭玻璃墙和顶面的内表面与原程序的 x/y ±6、z 0–12 边界对齐；Demo 与 Interactive 使用相同物理边界，各自保留适合观看与操作的相机。Push 按冲量/质量改变速度，Drag 使用原始 Workshop.apply 的质量相关抓取力、当前重力补偿、100 的力上限与 2 的移动速度上限，评测工具的默认可达高度仍为 3；网页访客可抓取整个房间内的物体，目标按物体尺寸限制在真实墙面和顶面内。竖直拖动直接控制高度，左右拖动沿当前视角移动，按住 Shift 拖动则在同一高度平面滑动；松手或取消触摸会释放物体。拖放不触发 PUSH/THROW 的事件；延迟与第三次接触的状态持续保存到重置。

浏览器规则按 `scenes/base_15.json` 实现，包含接触变色、第三次接触上跳、延迟复制与暂停计时。`verify_live_rules.py` 用原始 Python 程序产生对照轨迹；扩展审计共 69 组实验，覆盖原演示、随机初始运动、持续抓取与释放、换砖反弹、三球接触、天花板碰撞、多个延迟复制以及零冲量。以 0.05 秒间隔比较位姿、速度、颜色、抓取状态、碰撞计数和所有定时事件，当前误差小于 10⁻⁸。4× 实时播放仅增加每个显示帧内的物理步数，积分步长仍为 0.002 秒。Python 验证环境是 MuJoCo 3.12.0，浏览器是 3.15.0。浏览器交互不包含搭建新器材的工坊流程。

首屏依赖固定版本 MuJoCo 3.15.0（Apache-2.0）和 Three.js 0.186.1（MIT），全部存放于 `assets/vendor/`，无需连接外部 CDN。进入或预加载交互时才下载引擎，不影响页面先显示；部署时保持相对目录和 `.wasm` 文件即可。网页字体使用完整字形的 WOFF2 压缩副本，原 TTF 留给素材导出脚本；可用 `python scripts/compress_fonts.py` 重新生成（仅维护时需要 fonttools[woff]）。

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
# 仅更新第一个案例的说明和状态标记，复用已生成的帧：
python scripts/prepare_case_question.py --ffmpeg /path/to/ffmpeg
# 只出样帧（不替换页面影片）：增加 --preview
python scripts/verify_case_films.py --url http://127.0.0.1:8765

# 在论文接受的三个演化场景中运行脚本化干预并导出 demo
python scripts/prepare_evolution_interactive.py
# Use the same camera, materials and 60 fps presentation as the original scenes.
python scripts/refresh_evolution_media.py --ffmpeg /path/to/ffmpeg
python scripts/verify_evolution_demos.py --url http://127.0.0.1:8765
python scripts/verify_evolution_model.py --url http://127.0.0.1:8765

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

# 核对轨迹与原生记录、固定构图、播放和全屏的同步
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

作者姓名、单位和个人链接保存在 `index.html` 的 `AUTHORS_BEGIN` / `AUTHORS_END` 作者区内；BibTeX 也包含具名作者。PDF 和数据下载保持匿名。第三方库、字体的版权声明及文献引用照常保留。`bash scripts/build_pages.sh --anonymous /tmp/longchang-anonymous` 仅替换页头作者区，不修改 BibTeX 或当前页面。

## 匿名检查与引用格式

`python -B scripts/verify_anonymity.py --ocr --report /tmp/project-page-anonymity-audit.json` 检查整个目录及 ZIP/GZ 内部、PDF 正文和元数据、图片/视频/字体元数据；OCR 覆盖静态图片及动画/视频的首、中、末帧。身份词从作者区自动读取，检查脚本不保存真实姓名。检查报告保存在发布目录之外。

页头提供 BibTeX 入口，页面底部用代码框和复制按钮展示 `#bibtex-entry`。引用与仓库根目录 `README.md` 保持一致，采用 [StreamMA](https://zhenyangcs.github.io/StreamMA-website/) 的 `@article` 格式，包含论文标题、完整作者、`journal` 和年份；未知 arXiv 编号写为 `xxx`，即 `journal={arXiv preprint arXiv:xxx}`。
