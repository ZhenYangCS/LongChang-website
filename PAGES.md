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

工作流仅用 Bash 复制已经生成好的静态文件；不会运行论文实验、调用模型或执行 Python。当前静态文件约 670 MiB，最大单文件约 39.5 MiB，低于 GitHub 的 100 MiB 文件限制和 GitHub Pages 的 1 GB 发布限制。打包脚本检查符号链接、单文件大小及整站大小。视频、完整测量数据与 WASM 都按需加载。

## 加载速度

发布包的总大小不等于一次访问的下载量。2026-10-18 在本地 gzip 预览、浏览器冷缓存下测得：首屏约 1.4 MB，不加载视频和 WASM；首次进入 Try it 额外下载约 3.1 MB，物理引擎在各场景之间共用。网页字体使用不裁减字形的 WOFF2 副本，较原先首屏少下载约 235 KB。

Chromium 限速模拟结果（1366×768，未上线的本地预览）：

| 网络条件 | 首屏主要内容出现 | 首次进入 Try it | 随后切换场景 |
| --- | --- | --- | --- |
| 10 Mbps、100 ms 延迟 | 约 1.1 秒 | 约 4.3 秒 | 约 1.0 秒 |
| 4 Mbps、150 ms 延迟 | 约 2.3 秒 | 约 8.2 秒 | 约 1.2 秒 |

这些是受控模拟，不能作为 GitHub Pages 实际访问速度的保证；访客到 GitHub 的网络、服务器压缩、缓存和设备性能都会影响结果。上线后应再从目标访客所在网络实测。长页面默认滚轮翻页；Try it 的 Wheel zoom 开关可启用普通滚轮缩放，选择在基础场景与演化场景间同步并在刷新后保留。全屏始终可直接滚轮缩放，退出后恢复选择。− / + / Fit 按钮、Ctrl/⌘ + 滚轮与手机双指缩放均继续可用。

## 上线前待定内容

- `index.html` 的 BibTeX 仍为匿名占位，`year` 和 `url` 留空；正式发表信息确定后再填写，并决定引用和 PDF 是否继续匿名。
- `Code` 当前提供可下载的源码 ZIP；若要链接公开代码仓库，待仓库地址确定后替换。
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
python3 scripts/verify_zoom.py --url http://127.0.0.1:8782/longchang/
```

这会检查子路径资源、WASM、视频、交互和手机布局，不会部署。保留完整研究仓库时，还可执行 `python3 scripts/verify_site.py` 核对素材与论文源数据。

`scripts/serve.py` 仅用于本地预览；其他 Python 脚本用于重新生成素材，都不参与线上运行。部署所需素材已生成，无须在本机安装 Python、MuJoCo 或 Blender。
