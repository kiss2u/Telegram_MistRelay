#!/usr/bin/env bash

set -euo pipefail

WORKFLOW_FILE="build-windows-desktop.yml"
if [[ $# -lt 1 ]]; then
  echo "用法: $0 <version> [remote] [download-dir]"
  exit 1
fi

VERSION="$1"
REMOTE="${2:-origin}"
ARTIFACT_DIR="${3:-dist/windows-client}"
TAG_NAME="desktop-v${VERSION}"
HEAD_SHA="$(git rev-parse HEAD)"

if [[ ! "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+([-.+][0-9A-Za-z.-]+)?$ ]]; then
  echo "错误: 版本号格式无效: ${VERSION}"
  echo "示例: 0.1.0 或 0.1.0-beta.1"
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "错误: 未安装 GitHub CLI (gh)"
  echo "请先安装 gh 后再运行此脚本。"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "错误: GitHub CLI 未登录"
  echo "请先执行: gh auth login"
  exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "警告: 当前仓库存在未提交改动。"
  echo "发布流程只会构建当前提交以及其 tag 指向的代码，不包含本地未提交内容。"
fi

if git rev-parse "${TAG_NAME}" >/dev/null 2>&1; then
  echo "错误: 本地 tag 已存在: ${TAG_NAME}"
  exit 1
fi

if git ls-remote --exit-code --tags "${REMOTE}" "refs/tags/${TAG_NAME}" >/dev/null 2>&1; then
  echo "错误: 远端 tag 已存在: ${TAG_NAME}"
  exit 1
fi

echo "创建并推送 Windows 桌面客户端发布 tag..."
echo "版本号: ${VERSION}"
echo "远端: ${REMOTE}"

git tag -a "${TAG_NAME}" -m "MistRelay Desktop ${VERSION}"
git push "${REMOTE}" "${TAG_NAME}"

echo "Tag 已推送，正在查找构建任务..."

RUN_ID=""
for _ in {1..24}; do
  RUN_ID="$(gh run list \
    --workflow "${WORKFLOW_FILE}" \
    --event push \
    --limit 20 \
    --json databaseId,headSha \
    --jq ".[] | select(.headSha==\"${HEAD_SHA}\") | .databaseId" | head -n 1)"
  if [[ -n "${RUN_ID}" ]]; then
    break
  fi
  sleep 5
done

if [[ -z "${RUN_ID}" ]]; then
  echo "错误: 未找到由 tag ${TAG_NAME} 触发的工作流运行记录"
  exit 1
fi

echo "运行 ID: ${RUN_ID}"
echo "等待工作流完成..."
gh run watch "${RUN_ID}"

mkdir -p "${ARTIFACT_DIR}"
echo "下载 Release 资产到 ${ARTIFACT_DIR} ..."
gh release download "${TAG_NAME}" --dir "${ARTIFACT_DIR}" --clobber

echo "Windows 客户端产物已下载完成。"
echo "GitHub Release: ${TAG_NAME}"
