# 开发脚本说明

本目录包含MistRelay项目的开发辅助脚本。

## 脚本列表

### 1. start-dev.sh
**用途**: 一键启动开发环境  
**功能**:
- 启动Docker后端服务
- 启动前端开发服务器(Vite)
- 同时运行前后端,方便开发调试

**使用方法**:
```bash
./dev-scripts/start-dev.sh
```

---

### 2. build-frontend.sh
**用途**: 构建前端并重启Docker  
**功能**:
- 构建前端生产版本
- 自动重启Docker容器以应用更改

**使用方法**:
```bash
./dev-scripts/build-frontend.sh
```

---

### 3. watch-backend.sh
**用途**: 监听后端代码变化  
**功能**:
- 监听Python后端文件变化
- 自动重启Docker容器
- 提高开发效率

**使用方法**:
```bash
./dev-scripts/watch-backend.sh
```

---

### 4. build-windows-client.sh
**用途**: 触发 GitHub Actions 的 Windows 客户端构建并下载产物  
**功能**:
- 创建并推送 `desktop-v<version>` tag
- 在 `windows-latest` Runner 上编译 Tauri Windows 客户端
- 构建完成后自动创建 GitHub Release（含签名安装包和 `latest.json` 更新清单）
- 自动下载 `.exe` 安装包产物到本地目录

**前置条件**:
- 已安装并登录 `gh` (`gh auth login`)
- 仓库已推送到 GitHub
- 仓库 Settings > Secrets 中已设置 `TAURI_SIGNING_PRIVATE_KEY`
- 需要先把要构建的代码提交并推送到目标分支/提交

`TAURI_SIGNING_PRIVATE_KEY` 需要填入 `tauri signer generate` 生成的私钥文件内容本身。
如果使用当前仓库这套 key，`TAURI_SIGNING_PRIVATE_KEY_PASSWORD` 保持空即可。
`desktop/tauri.conf.json` 中 updater `pubkey` 需要填写 `.key.pub` 文件里的 base64 内容本身，不要手动解码。
不要把 updater 的 `pubkey`、文件路径或被空格打断的 base64 文本填进 `TAURI_SIGNING_PRIVATE_KEY`。

**使用方法**:
```bash
./dev-scripts/build-windows-client.sh 0.1.1
```

可选参数:
```bash
./dev-scripts/build-windows-client.sh <version> <remote> <download-dir>
```

**发布结果**:
- 自动创建 `desktop-v<version>` 的 GitHub Release
- 自动上传 Windows 签名安装包（`.exe` + `.exe.sig`）和 `latest.json` 到 Release
- 自动将该 Release 标记为 `latest`
- 自动生成按分类整理的 Release Notes
- 桌面客户端的 updater 会自动从 `latest.json` 检查更新

> 也可以直接推送 `v*` tag（如 `v0.1.1`）触发同一工作流。

---

## 生产环境

生产环境请使用根目录的标准Docker命令:

```bash
# 构建并启动
docker compose up -d --build

# 停止
docker compose down

# 查看日志
docker compose logs -f
```

根目录的 `start.sh` 是Docker容器内部使用的启动脚本,无需手动执行。

## 桌面客户端

桌面客户端是完全独立的项目，位于 `desktop/` 目录，拥有独立的前端源码和 Rust 后端。
不通过 `docker compose` 生成，而是由 `.github/workflows/build-windows-desktop.yml` 在 `v*` 或 `desktop-v*` tag 推送后由 Windows Runner 自动构建。

桌面端本地开发：
```bash
cd desktop
npm install
npm run dev
```
