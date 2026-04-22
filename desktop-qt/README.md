# MistRelay Desktop Qt

`desktop-qt/` 是 MistRelay 的独立 Windows Beta 客户端，基于 `PySide6 + Qt Quick/QML`。
它与现有 `desktop/` Tauri 客户端并行发布，使用独立 tag、安装包和更新清单，不接管现有正式版升级链路。

## 当前能力

- 登录、会话恢复、Dashboard、任务中心、Telegram 网盘、本地下载与预览
- 客户端连接 / 代理 / 下载配置
- 服务端分类配置读取、保存、从 `config.yml` 重新导入
- Rclone 配置文件读取与保存
- Docker 状态、Docker 日志、系统资源、应用日志
- 独立 `qt-latest.json` 更新清单、签名校验、Windows 静默安装更新

## 版本与发布

- 版本源：`version.json`
- 发布 tag：`desktop-qt-v<semver>`
- Release 资产：
  - `mistrelay-desktop-qt-v<version>-setup.exe`
  - `qt-latest.json`
  - `qt-latest.json.sig`

`version.json` 里的 `verify_key` 是 Qt 更新公钥，格式为 `Ed25519 VerifyKey` 原始 32 字节的 base64。
GitHub Actions 使用独立私钥 `QT_UPDATE_PRIVATE_KEY` 生成 `qt-latest.json.sig`。
Beta 客户端不会依赖 GitHub 的 `releases/latest/download`，而是通过 `release_feed_url` 从 GitHub Releases API 中筛选 `desktop-qt-v*` 的最新资产。

## 目录结构

- `main.py`: Qt 客户端入口
- `version.json`: Qt 客户端版本与更新通道元数据
- `mistrelay_qt/app.py`: 应用装配、QML 上下文和生命周期
- `mistrelay_qt/services/`: HTTP、WS、更新、本地运行时服务
- `mistrelay_qt/viewmodels/`: 页面状态和命令
- `mistrelay_qt/qml/`: QML 页面、组件和主题
- `scripts/check_release.py`: 本地预发布检查
- `scripts/build_windows.py`: PyInstaller + NSIS Windows 构建入口
- `scripts/release_manifest.py`: 更新清单生成、验签、keygen
- `windows/installer.nsi`: Windows 安装器模板

## 本地运行

```bash
cd desktop-qt
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python main.py
```

默认会读取旧桌面端配置 `%APPDATA%/MistRelay/desktop-client.json`，并迁移到 Qt 独立配置：

- Windows: `%APPDATA%/MistRelay/desktop-client-qt.json`
- Linux/macOS 开发环境: `~/.config/MistRelay/desktop-client-qt.json`

## 本地预发布检查

```bash
cd desktop-qt
python scripts/check_release.py
```

如果要强制检查更新公钥已配置：

```bash
python scripts/check_release.py --require-update-key
```

如果要临时指向一个手动托管的更新清单，可以覆盖：

```bash
MISTRELAY_QT_UPDATE_MANIFEST_URL=https://example.com/qt-latest.json python scripts/check_release.py
```

## Windows 构建

```bash
cd desktop-qt
python scripts/build_windows.py --clean
```

该脚本会：

- 用 `PyInstaller` 生成 `onedir` 产物
- 打包 QML、图标和 `version.json`
- 调用 NSIS 生成 Windows 安装包

如果只想先验证 PyInstaller 产物：

```bash
python scripts/build_windows.py --clean --skip-installer
```

## 更新密钥

生成一套新的 Qt 更新密钥：

```bash
cd desktop-qt
python scripts/release_manifest.py keygen --output-dir build/update-keys
```

生成结果：

- `qt-update-private.key`: 放到 GitHub Secret `QT_UPDATE_PRIVATE_KEY`
- `qt-update-public.key`: 把内容写入 `version.json.verify_key`，或由 CI 在构建前注入

## GitHub Actions

工作流文件：`.github/workflows/build-windows-desktop-qt.yml`

需要的 Secrets：

- `QT_UPDATE_PRIVATE_KEY`
- `QT_UPDATE_VERIFY_KEY`

推送 `desktop-qt-v<semver>` tag 后会自动：

- 同步 `version.json` 版本号
- 注入 Qt 更新公钥
- 运行本地预发布检查
- 构建 Windows 安装包
- 生成并签名 `qt-latest.json`
- 校验清单、签名、安装包 hash 和大小
- 创建 GitHub Release
