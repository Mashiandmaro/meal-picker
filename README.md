# 好好吃饭

面向 iPhone 的轻量餐食搭配网页：按早餐 / 午餐 / 晚餐、减脂搭配 / 日常均衡 / 随心餐、外卖 / 便利店速食 / 自己做筛选。支持随机推荐、替换单道食物、收藏、自定义搭配、食材排除、最近选择、JSON 导入导出和离线缓存。

## 运行

不需要 Node.js、npm、数据库或 API Key。将整个目录复制到 Linux 开发机，然后运行：

```bash
cd meal-picker
python3 -m http.server 8080 --bind 0.0.0.0
```

开发机与 iPhone 在可互通的网络内时，用 iPhone Safari 打开 `http://开发机IP:8080`。不要把 `localhost` 当作手机访问地址。远程开发机需要可达的 VPN / 局域网，或部署到 HTTPS 静态网站；SSH 隧道只转发到电脑时，手机不会自动获得访问权限。

正式个人使用建议部署到 HTTPS 静态托管。所有文件使用相对路径，可部署在子目录。项目已带 GitHub Pages 自动发布配置；需先上传到你自己的仓库并启用 Pages。

## 发布到 GitHub，手机直接打开

GitHub 存放代码，GitHub Pages 托管网页。本项目没有服务器后端，适合直接使用 Pages。免费个人账号通常采用公开仓库；发布的是源代码和基础搭配，手机收藏与记录仍在浏览器本地。

首次设置：

1. 在 GitHub 新建公开仓库，例如 `meal-picker`。
2. 将本项目的文件上传至仓库根目录（`index.html` 和 `.github` 直接位于根目录，不再多套一层 `meal-picker` 文件夹）。确保 `.github/workflows/pages.yml` 和 `scripts/build_site.py` 一并提交。
3. 仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。
4. 在 **Actions → Publish meal picker → Run workflow** 启动首次发布。如果首次推送时尚未开启 Pages 导致失败，完成第 3 步后重新运行即可。
5. 工作流成功后，打开 **Settings → Pages** 显示的实际网址。通常是 `https://你的用户名.github.io/meal-picker/`。
6. 用 iPhone Safari 打开这个网址，点分享 → 添加到主屏幕。之后无需开发机保持运行，也不必与开发机处于同一网络。

以后更新：修改文件并提交到 `main` 分支，会自动发布。可以在 GitHub 网页编辑小改动，也可以在 Linux 上操作：

```bash
git pull --ff-only
# 修改代码或食谱
git add data.js app.js styles.css
git commit -m "Update meal combinations"
git push
```

- 改搭配内容：`data.js`（保留已有 ID，避免破坏收藏引用）。
- 改页面外观：`styles.css`。
- 改交互逻辑：`app.js`。
- 修改提交后等 Actions 显示成功，再联网刷新 Safari；主屏幕版本可完全关闭后重新打开。
- 在网页里“添加自己的搭配”只修改本机数据，不会自动提交到 GitHub。全设备共享的基础餐库需要修改 `data.js`。

发布流程只打包应用文件，自动按内容生成离线缓存版本，不需要每次手动改版本号。截图、测试、日志和 ZIP 包不随网页发布。GitHub Pages 的访问速度取决于手机网络，首次打开应在能访问 GitHub Pages 的网络下测试。

官方说明：https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages

## iPhone

- 推荐 iOS 16 或更新版本的 Safari。
- Safari 分享菜单 → 添加到主屏幕。若显示“作为网页 App 打开”，可以开启。
- 已处理 `viewport-fit=cover`、四边安全区、底部 Home Indicator、弹出面板动态高度、16px 输入字号、触控区域与减少动态效果。
- 只有 HTTPS 或 localhost 等安全上下文会启用 Service Worker。首次加载并缓存成功后可离线打开；普通局域网 HTTP 不支持离线。
- 页面缩放保持可用，不设置 `user-scalable=no`。
- 当前仅在浏览器内保存。没有云同步、分析追踪或远程模型调用。Safari 与主屏幕版本可能使用不同存储，请导出并导入迁移。清理网站数据、换设备、浏览器回收存储可能丢失数据。

## 数据与内容

- `data.js`：48 套原创组合及结构化食材、餐别、场景、类型和整理来源。
- `engine.js`：筛选、排除、避免近期重复、备份格式验证。
- `app.js`：交互与本地持久化。导入前检查数据，确认后替换；不把用户文本作为 HTML 执行。
- `styles.css`：iPhone 优先的布局、简约视觉与响应式样式。
- `sw.js`：静态资源离线缓存。GitHub Pages 发布时由 `scripts/build_site.py` 自动生成缓存版本；手动直接托管源码时仍需递增 `CACHE` 版本。更新由浏览器在旧页面关闭后启用。
- `.github/workflows/pages.yml`：提交到 `main` 后自动构建并发布 GitHub Pages。

这些搭配依据通用膳食原则整理，不是官方食谱原文，也没有经过营养师逐条审核。没有自动套用成人肥胖食养指南中的限制能量方案，没有伪造热量数据。餐盘图为本项目绘制的示意图，不表示实际食材比例或份量。

“减脂搭配”只表示选择非油炸、少额外酱料等方向，实际仍取决于份量、烹饪方法和整日饮食。“随心餐”对应放纵餐选项，不设置补偿或惩罚。食材排除只根据已录入标签，不能确认未知配料、食品过敏原或交叉接触；自定义搭配由使用者补充标签。

参考资料：

- https://dg.cnsoc.org/article/04/D5ZFYyhzTgmHGvOsfS-1hg.html
- https://www.nhc.gov.cn/sps/c100088/202402/9ba512ba8e314a47a181db11d2fa188d.shtml
- https://webkit.org/blog/7929/designing-websites-for-iphone-x/
- https://support.apple.com/en-lamr/guide/iphone/iphea86e5236/ios

## 验证

可选的开发检查使用 Python Playwright（运行应用本身不需要它）：

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
python3 tests/check_app.py
```

测试自行启动临时本地服务器，覆盖多种 iPhone 屏幕宽度、收藏持久化、食材筛选、替换、自定义餐、备份校验和离线加载。桌面浏览器的手机模拟不等于 iPhone 真机 Safari 验证，发布前应在实际手机上确认主屏幕启动、分享导出与安全区。
