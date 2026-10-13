# GitHub Pages

这是纯静态网站。线上只需要 HTML、CSS、JavaScript、字体、视频和数据文件；交互物理由浏览器中的 MuJoCo WASM 执行，不需要 Python 服务、API key 或后端。

## 部署

1. 将 `project_page` 目录的内容放到目标 GitHub 仓库根目录，保留 `.github/` 和 `.nojekyll`。也可保留整个仓库的 `project_page/` 结构，两种方式都已配置。
2. 打开仓库 **Settings → Pages → Build and deployment → Source**，选择 **GitHub Actions**。
3. 推送到 `main` / `master`，或在 **Actions → Deploy project page → Run workflow** 手动部署。

部署成功后，Actions 会给出网址，一般为 `https://用户名.github.io/仓库名/`。如果仓库名为 `用户名.github.io`，网址就是 `https://用户名.github.io/`。

工作流仅用 Bash 复制已经生成好的静态文件；不会运行论文实验、调用模型或执行 Python。当前所有单个文件均小于 GitHub 的 100 MB 文件限制，整站小于 GitHub Pages 的 1 GB 发布限制。视频、完整测量数据与 WASM 都按需加载。

## 构建静态目录

```bash
bash scripts/build_pages.sh /path/to/empty-output
```

输出目录可直接交给任何支持静态文件和视频 Range 请求的网页托管服务。所有运行时路径均为相对路径，支持 GitHub 仓库子路径。WASM 使用单线程版本，不需要额外的跨源隔离响应头。

`scripts/serve.py` 仅用于本地预览；其他 Python 脚本用于重新生成素材，都不参与线上运行。部署所需素材已生成，无须在本机安装 Python、MuJoCo 或 Blender。
