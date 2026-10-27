# GitHub Pages

这是纯静态网站。线上只需要 HTML、CSS、JavaScript、字体、视频和数据文件；交互物理由浏览器中的 MuJoCo WASM 执行，不需要 Python 服务、API key 或后端。

## 现在准备，稍后部署

工作流只接受手动 `workflow_dispatch`，普通 push 不会发布。以下检查和打包命令也只操作本地文件。

准备目标仓库时，推荐将 `project_page/` 的内容复制到单独的站点仓库根目录，用新仓库管理网站，避免把实验文件和整个研究仓库历史一并上传。必须包含隐藏的 `.github/`、`.gitignore` 和 `.nojekyll`；例如在当前研究仓库根目录执行 `cp -a project_page/. /path/to/site-repo/`，目标须是专门用于网站的目录。也可保留整个仓库的 `project_page/` 结构，两种布局均已配置。

等准备正式上线时：

1. 将网站文件提交到目标 GitHub 仓库，确保 `.github/workflows/pages.yml` 位于默认分支的仓库根目录下。`project_page/.github/` 仅供复制为独立站点仓库时使用，GitHub 不会在研究仓库内递归执行它。
2. 打开仓库 **Settings → Pages → Build and deployment → Source**，选择 **GitHub Actions**。不要选择从分支直接发布整个研究仓库。
3. 在 **Actions → Deploy project page → Run workflow** 选择待发布分支并手动运行。后续更新也需要手动运行。

部署成功后，Actions 会给出网址，一般为 `https://用户名.github.io/仓库名/`。如果仓库名为 `用户名.github.io`，网址就是 `https://用户名.github.io/`。

工作流用 Bash 复制已有静态文件，并按原顺序合并首屏样式和普通脚本；不会运行论文实验、调用模型或执行 Python。字体样式和动态模块保留原路径，合并文件名包含内容哈希，更新后不会误用旧版合并文件。当前静态文件约 671 MiB，最大单文件约 39.5 MiB，低于 GitHub 的 100 MiB 文件限制和 GitHub Pages 的 1 GB 发布限制。打包脚本检查符号链接、单文件大小及整站大小。视频、完整测量数据与 WASM 都按需加载。

## 加载速度

2026-10-19 的优化保持页面文字、数据、图片、视频及 CSS 规则不变。发布版将 18 个普通样式表合为一个、28 个普通脚本合为一个，字体样式独立保留。本地 1366×768、冷缓存、10 Mbps / 100 ms 延迟的对照检查中，首屏资源请求从 79 次减为 36 次，初始可见文字及截图像素完全一致，首屏仍不下载视频或 WASM。该次主要内容出现时间约为优化前 1.11 秒、优化后 1.03 秒；单次模拟仅供参考，不代表线上或所有设备的速度。

图表与轨迹共用下载和解析结果，最多缓存四份已完成的 JSON；取消某一消费者不会中断其他消费者，失败后可重试。WASM 边下载边异步编译和实例化，各场景共享引擎，并保留不支持流式编译时的回退。3D 保持高画质，不再自动降分辨率或替换阴影、材质；静止物体复用阴影贴图，控制栏仅在显示值变化时更新。模拟规则、精度、播放速度与原始视频均不变。

以下为 2026-10-18 的优化前记录，便于对照：

发布包的总大小不等于一次访问的下载量。2026-10-18 在本地 gzip 预览、浏览器冷缓存下测得：首屏约 1.4 MB，不加载视频和 WASM；首次进入 Try it 额外下载约 3.1 MB，物理引擎在各场景之间共用。网页字体使用不裁减字形的 WOFF2 副本，较原先首屏少下载约 235 KB。

Chromium 限速模拟结果（1366×768，未上线的本地预览）：

| 网络条件 | 首屏主要内容出现 | 首次进入 Try it | 随后切换场景 |
| --- | --- | --- | --- |
| 10 Mbps、100 ms 延迟 | 约 1.1 秒 | 约 4.3 秒 | 约 1.0 秒 |
| 4 Mbps、150 ms 延迟 | 约 2.3 秒 | 约 8.2 秒 | 约 1.2 秒 |

这些是受控模拟，不能作为 GitHub Pages 实际访问速度的保证；访客到 GitHub 的网络、服务器压缩、缓存和设备性能都会影响结果。上线后应再从目标访客所在网络实测。长页面默认滚轮翻页；Try it 的 Wheel zoom 开关可启用普通滚轮缩放，选择在基础场景与演化场景间同步并在刷新后保留。全屏始终可直接滚轮缩放，退出后恢复选择。− / + / Fit 按钮、Ctrl/⌘ + 滚轮与手机双指缩放均继续可用。

## 上线前待定内容

- `index.html` 与仓库根目录 `README.md` 的 BibTeX 使用相同的 `@article` 格式、完整作者与 2026 年份；arXiv 编号暂写 `xxx`，正式编号确定后同步替换。
- `Code` 已链接到 `https://github.com/EnVision-Research/LongChang`；`Paper` 暂用同一地址，待 arXiv 地址确定后更新首屏及 `<noscript>` 中的 Paper 链接。
- 分享卡的 `og:image` 当前使用相对路径。最终域名确定后改为绝对 HTTPS 地址，并补充 `og:url` 和 canonical，便于社交平台识别正式网址。
- 素材体积仍有增长空间，但发布包已约 670 MiB。以后重新导出视频或添加下载包时，应再次执行打包检查。

## 构建静态目录

在 `project_page/`（或独立站点仓库根目录）中运行：

```bash
bash scripts/build_pages.sh /path/to/empty-output

# 匿名评审副本：仅将独立作者区替换为 Anonymous Authors
bash scripts/build_pages.sh --anonymous /tmp/longchang-anonymous
```

输出目录可直接交给任何支持静态文件和视频 Range 请求的网页托管服务。所有运行时路径均为相对路径，支持 GitHub 仓库子路径。WASM 使用单线程版本，不需要额外的跨源隔离响应头。

发布包只包含 `index.html`、`assets/`、`data/`、`downloads/` 和 `.nojekyll`，不包含工作流和维护脚本，因此它用于静态托管，不是完整的网站开发仓库。

## 本地模拟仓库子路径

安装 Playwright 和 Chromium 后，可在终端一执行（输出目录须为空）：

```bash
preview_root="$(mktemp -d /tmp/longchang-pages.XXXXXX)"
bash scripts/build_pages.sh "$preview_root/longchang/"
python3 scripts/serve.py --bind 127.0.0.1 --port 8782 --directory "$preview_root"
```

在终端二、同一网站目录执行：

```bash
python3 scripts/verify_pages.py --url http://127.0.0.1:8782/longchang/
python3 scripts/verify_loading.py --url http://127.0.0.1:8782/longchang/
python3 scripts/verify_zoom.py --url http://127.0.0.1:8782/longchang/
```

这会检查子路径资源、WASM、视频、交互和手机布局，不会部署。保留完整研究仓库时，还可执行 `python3 scripts/verify_site.py` 核对素材与论文源数据。

`scripts/serve.py` 仅用于本地预览；其他 Python 脚本用于重新生成素材，都不参与线上运行。部署所需素材已生成，无须在本机安装 Python、MuJoCo 或 Blender。
