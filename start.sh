#!/usr/bin/env bash
# ============================================================
# TechHub 一键启动脚本
# 覆盖从零开始的完整启动流程：数据库 -> 后端 -> 前端
# 自动检测 CPU 架构（x86_64 / aarch64），兼容两种平台
#
# 用法:
#   ./start.sh          # 启动（若依赖缺失会自动安装）
#   ./start.sh --install-only   # 只安装依赖，不启动服务
# ============================================================
set -euo pipefail

# ---------- 路径配置 ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
ENV_FILE="$BACKEND_DIR/.env"

# ---------- 数据库配置（按需修改） ----------
DB_USER="root"
DB_PASSWORD="password"
DB_NAME="techhub"
DB_HOST="127.0.0.1"
DB_PORT="3306"

# ---------- 架构检测 ----------
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64)  ARCH_LABEL="x86_64";  PY_ARCH="x86_64" ;;
  aarch64|arm64) ARCH_LABEL="arm64";   PY_ARCH="aarch64" ;;
  *)             ARCH_LABEL="$ARCH";   PY_ARCH="$ARCH" ;;
esac
echo "[TechHub] 检测到 CPU 架构: $ARCH_LABEL"

# ---------- 颜色输出 ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ---------- 依赖检查：系统包 ----------
check_system_deps() {
  info "检查系统依赖..."
  local missing=()

  # Python 3
  if ! command -v python3 >/dev/null 2>&1; then missing+=(python3); fi

  # MariaDB/MySQL 服务端（Debian/Ubuntu 系为 mariadb-server）
  if ! systemctl is-active --quiet mariadb 2>/dev/null && \
     ! systemctl is-active --quiet mysql 2>/dev/null; then
    missing+=(mariadb-server)
  fi

  # Node.js (前端需要 18+)
  if ! command -v node >/dev/null 2>&1; then missing+=(nodejs npm); fi

  if [ ${#missing[@]} -gt 0 ]; then
    warn "缺少系统包: ${missing[*]}，尝试安装..."
    if command -v apt-get >/dev/null 2>&1; then
      sudo DEBIAN_FRONTEND=noninteractive apt-get update -y
      sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
        "${missing[@]}" python3-venv python3-pip curl
    elif command -v yum >/dev/null 2>&1; then
      sudo yum install -y "${missing[@]}" python3-pip nodejs npm
    else
      error "不支持的包管理器，请手动安装: ${missing[*]}"
      exit 1
    fi
  fi
  info "系统依赖 OK"
}

# ---------- 数据库初始化 ----------
setup_database() {
  info "检查 MariaDB/MySQL 服务..."
  if ! systemctl is-active --quiet mariadb 2>/dev/null && \
     ! systemctl is-active --quiet mysql 2>/dev/null; then
    sudo systemctl start mariadb 2>/dev/null || sudo systemctl start mysql 2>/dev/null
    sleep 2
  fi

  info "初始化数据库 ${DB_NAME} ..."
  # 使用 unix_socket 认证的 root 执行（Debian/Ubuntu 默认）
  if sudo mysql -e "SELECT 1" >/dev/null 2>&1; then
    # 设置 root 密码（若尚未设置）
    sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '${DB_PASSWORD}'; FLUSH PRIVILEGES;" 2>/dev/null || true
    sudo mysql -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
  else
    # root 已设密码，直接用密码连接
    mysql -u"$DB_USER" -p"$DB_PASSWORD" -h"$DB_HOST" -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null || \
    error "无法连接数据库，请手动检查 MariaDB 状态"
  fi
  info "数据库 ${DB_NAME} 就绪"
}

# ---------- 后端依赖安装 ----------
setup_backend() {
  info "配置后端虚拟环境..."
  cd "$BACKEND_DIR"

  # 创建 venv（若不存在或损坏）
  if [ ! -x ".venv/bin/python" ]; then
    rm -rf .venv
    python3 -m venv .venv
  fi

  # 使用阿里云镜像安装依赖（树莓派/国内网络友好）
  info "安装后端依赖（阿里云镜像）..."
  .venv/bin/pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/ -q
  .venv/bin/pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ -q
  # MySQL 驱动 + alembic（requirements 之外的运行时依赖）
  .venv/bin/pip install pymysql alembic -i https://mirrors.aliyun.com/pypi/simple/ -q

  # 写入 .env（不存在时）
  if [ ! -f "$ENV_FILE" ]; then
    warn "未找到 .env，基于模板生成..."
    cat > "$ENV_FILE" <<EOF
# 运行环境：development / production
ENV=development

# 数据库连接串 (MySQL)
DATABASE_URL=mysql+pymysql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}?charset=utf8mb4

# JWT 签名密钥
SECRET_KEY=techhub-dev-secret-key-2026
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS 允许来源（逗号分隔）
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://0.0.0.0:5173

# 文件上传上限（字节，默认 20MB）
MAX_UPLOAD_SIZE=20971520
EOF
    info ".env 已生成"
  fi

  # 检查 .env 中的 DATABASE_URL 是否仍是 SQLite（若是则替换为 MySQL）
  if grep -q "sqlite:///" "$ENV_FILE" 2>/dev/null; then
    warn "检测到 .env 仍使用 SQLite，切换为 MySQL..."
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=mysql+pymysql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}?charset=utf8mb4|" "$ENV_FILE"
  fi
  info "后端依赖 OK"
}

# ---------- 前端依赖安装 ----------
setup_frontend() {
  info "配置前端依赖..."
  cd "$FRONTEND_DIR"

  if [ ! -d "node_modules" ] || [ ! -x "node_modules/.bin/vite" ]; then
    warn "node_modules 缺失或不完整，重新安装..."
    rm -rf node_modules package-lock.json
    npm install --registry=https://registry.npmmirror.com
  fi
  info "前端依赖 OK"
}

# ---------- 启动服务 ----------
start_services() {
  # 清理旧进程
  pkill -f "uvicorn.*8080" 2>/dev/null || true
  pkill -f "vite.*5173" 2>/dev/null || true
  sleep 1

  info "启动后端 (uvicorn :8080)..."
  cd "$BACKEND_DIR"
  nohup .venv/bin/python run.py > /tmp/techhub_backend.log 2>&1 &
  BACKEND_PID=$!
  echo "  后端 PID: $BACKEND_PID，日志: /tmp/techhub_backend.log"

  info "启动前端 (vite :5173)..."
  cd "$FRONTEND_DIR"
  nohup npm run dev -- --host 0.0.0.0 > /tmp/techhub_frontend.log 2>&1 &
  FRONTEND_PID=$!
  echo "  前端 PID: $FRONTEND_PID，日志: /tmp/techhub_frontend.log"

  # 等待端口就绪
  info "等待服务启动..."
  for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1 && \
       curl -sf -o /dev/null http://127.0.0.1:5173/ >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done

  echo ""
  echo "======================================================"
  echo "  TechHub 启动完成!"
  echo "  前端:  http://localhost:5173/   (局域网: http://<本机IP>:5173/)"
  echo "  后端:  http://localhost:8080/   (API 文档: /docs)"
  echo "  数据库: ${DB_NAME} (${DB_USER}/${DB_PASSWORD})"
  echo "======================================================"
  echo ""
  echo "  登录账号（seed 数据）："
  echo "    管理员 admin / admin123"
  echo "    教师   teacher / 123456"
  echo "    学生   班级+姓名 / 123456"
  echo ""
}

# ---------- 主流程 ----------
main() {
  check_system_deps
  setup_database
  setup_backend
  setup_frontend

  if [ "${1:-}" = "--install-only" ]; then
    info "依赖安装完成（--install-only），未启动服务"
    exit 0
  fi

  start_services
}

main "$@"
