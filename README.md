# TechHub

> 教学与班主任一体化工作平台 —— 一个账号，三种身份，覆盖「在线作业提交、班级日志、教师工作台」三大场景。

TechHub 将**在线作业提交平台**、**班级日志管理系统**、**教师工作台**三个项目合并重构为**一套前后端分离**的应用，统一使用 **FastAPI + Vue 3** 技术栈，实现清晰的**角色权限隔离**。

## 文档导航

| 文档 | 说明 |
| ---- | ---- |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 架构设计：技术栈、目录结构、权限模型、数据模型、部署架构、设计决策 |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | 开发规范：环境搭建、代码规范、Git 规范、测试规范、发布流程 |

## 核心特性

### 角色与权限

| 角色 | 登录入口 | 可访问范围 |
| ---- | -------- | ---------- |
| 学生 `student` | 学生端 `/` | 在线作业提交平台（查看/提交作业、优秀作品、编程练习、个人资料） |
| 教师 `teacher` / 管理员 `admin` | 管理端 `/admin` | 作业管理 + 教师工作台 + 班级日志 + 系统管理 |

学生账号**无法**访问后台接口（返回 403），权限在前后端双重校验。

### 三大功能模块

**1. 在线作业提交平台（学生端）**
- 学生登录（班级 + 姓名 + 密码）/ 自助注册
- 查看教师布置的 Markdown 任务，截止时间提醒
- 提交作业：Markdown 即时渲染编辑器 + 附件上传
- 优秀作品墙：教师评选优秀作品，学生互评，分页展示
- 编程练习推荐：热门 OJ 平台 + C 语言入门教程
- 个人资料：头像上传、密码修改

**2. 教师工作台（管理端）**
- 数据看板：核心指标卡片（可点击跳转对应模块）+ 请假趋势图 + 成绩分布饼图 + 请假人员详情 + 班级动态
- 学生管理：通学生/寄宿生统计图表（点击查看明细）+ 批量导入导出 + 密码管理 + 头像上传
- 学生画像：五维雷达图（含评价依据说明）+ 成绩趋势 + 积分历程 + 个性化标签 + 住宿状态变更历史
- 成绩管理：录入/编辑/批量导入导出 + 排序
- 考勤管理、积分管理（关联学生表现自动联动）
- 家校沟通、资源管理
- 试卷管理：文件上传（.pdf/.docx）+ 下载 + 在线管理
- 班级报告：数据聚合 + Markdown 模板 + 预览 + 历史归档
- 座位表：可视化排座

**3. 班级日志（管理端）**
- 班主任工作日志（Markdown 编辑）
- 班级/教师计划总结、课程表
- 班级活动、师生谈心、返校记录
- 学生表现：积极/消极记录 + 积分自动联动
- 学生评语
- 系统设置：学期配置、年级升级

**4. 通用特性**
- 所有列表页支持时间排序（最新在前/最早在前），排序偏好持久化
- 数据导入历史可追溯（含错误详情）
- 操作审计日志

## 技术栈

| 层级 | 技术 | 版本 |
| ---- | ---- | ---- |
| 后端框架 | FastAPI | 0.115 |
| ORM | SQLAlchemy | 2.0 |
| 数据库 | SQLite（可切换 MySQL/PostgreSQL，详见 database.py 文件头注释） | — |
| 认证 | JWT（python-jose）+ bcrypt | — |
| 前端框架 | Vue 3（Composition API） | 3.4 |
| 构建工具 | Vite | 5.4 |
| UI 组件库 | Element Plus | 2.7 |
| 数据可视化 | ECharts（按需引入） | 5.5 |
| Markdown | marked + DOMPurify（XSS 防护） | 12 |
| Excel 处理 | openpyxl | 3.1 |
| 测试 | pytest + FastAPI TestClient | — |

## 项目结构

```
techhub/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py             # 应用入口（路由挂载、CORS、建表、迁移）
│   │   ├── config.py           # 配置（env 驱动）
│   │   ├── database.py         # SQLAlchemy 连接 + 增量迁移 + 数据库切换指南
│   │   ├── security.py         # JWT + bcrypt 密码哈希
│   │   ├── deps.py             # 依赖注入（角色权限校验）
│   │   ├── schemas.py          # Pydantic 校验模型
│   │   ├── utils.py            # 工具函数
│   │   ├── audit.py            # 操作审计日志 + 批量查询
│   │   ├── seed.py             # 假数据种子（52 学生 + 完整业务数据）
│   │   ├── models/             # 数据模型（按域分组，28 张表）
│   │   │   ├── user.py         #   User
│   │   │   ├── school.py       #   School / Classroom / Student
│   │   │   ├── homework.py     #   Assignment / Submission / ExcellentWork / WorkComment
│   │   │   ├── workbench.py    #   Score / Leave / Point / Communication / Resource / Exam / Seat / Setting / ImportHistory / StudentProfileTag / WeeklyReport / StudentBoardHistory
│   │   │   ├── classlog.py     #   WorkLog / Plan / Schedule / Activity / Talk / ReturnRecord / Performance / StudentComment
│   │   │   └── operation_log.py
│   │   └── routers/            # API 路由（按业务域分组）
│   │       ├── auth.py         #   登录/注册/密码/头像上传
│   │       ├── meta.py         #   班级选项、编程练习
│   │       ├── homework.py     #   作业/提交/优秀作品/评论
│   │       ├── students.py     #   学校/班级/学生 CRUD + 导出 + 密码管理 + 通宿生统计 + 住宿历史
│   │       ├── workbench.py    #   成绩/考勤/积分/沟通/资源/试卷/座位 + 批量导入 + 画像 + 周报
│   │       ├── classlog.py     #   日志/计划/课表/活动/谈心/返校/表现/评语
│   │       ├── admin.py        #   账号管理 / 系统设置 / 数据看板
│   │       └── uploads.py      #   通用文件上传
│   ├── tests/                  # pytest 自动化测试
│   ├── requirements.txt
│   ├── run.py                  # 启动脚本（端口 8080）
│   └── .env.example            # 环境变量模板
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── api/                # Axios 封装 + 接口定义
│   │   ├── router/             # 路由 + 角色守卫
│   │   ├── utils/              # 认证工具、ECharts 封装
│   │   ├── composables/        # 可组合函数（useSort）
│   │   ├── components/         # Markdown / MarkdownEditor / StudentSelect / SortBar
│   │   ├── layout/             # AdminLayout（可折叠侧边栏）/ StudentLayout
│   │   └── views/              # 页面（student/ + admin/，共 30 个页面）
│   ├── vite.config.js          # /api 与 /uploads 代理 + 构建优化
│   └── package.json
├── docs/                       # 架构设计 / 开发规范 / 需求文档 / 产品文档
└── README.md
```

---

## 开发环境快速开始

### 🚀 一键启动（推荐）

项目根目录提供 `start.sh` 一键脚本，自动完成：**架构检测（x86_64 / arm64）→ 安装系统依赖 → 初始化 MySQL/MariaDB → 安装后端依赖（阿里云镜像）→ 安装前端依赖（npmmirror 镜像）→ 启动前后端服务**。

```bash
cd techhub

# 一键启动（首次运行会自动安装全部依赖，约 5-10 分钟）
./start.sh

# 仅安装依赖、不启动服务（适合先准备环境）
./start.sh --install-only
```

启动完成后：
- 前端：http://localhost:5173 （局域网设备用 `http://<本机IP>:5173/`）
- 后端 API 文档：http://localhost:8080/docs
- 数据库：默认 `techhub`，账号 `root / longbiu20260824`（可在 `start.sh` 顶部修改）

> **说明**：`start.sh` 使用 MariaDB 作为 MySQL 兼容数据库（Debian/Ubuntu 默认包），并自动处理
> Python 虚拟环境、`.env` 配置（MySQL 连接串）、前端 node_modules 平台差异（x86/ARM 原生二进制）。

### 环境要求

| 工具 | 最低版本 |
| ---- | -------- |
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |
| MariaDB/MySQL | 10.4+ / 8.0+ |

### 1. 启动后端（手动方式）

```bash
cd backend

# 创建虚拟环境并安装依赖
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 复制环境变量配置（可选，开发环境有默认值）
cp .env.example .env

# 生成演示假数据（可选，首次运行建议执行）
python -m app.seed

# 启动服务（默认端口 8080，自动建表和迁移）
python run.py
```

启动后：
- API 文档：http://localhost:8080/docs
- 健康检查：http://localhost:8080/health

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://localhost:5173（学生端），管理后台 http://localhost:5173/admin。

### 3. 演示账号

| 账号 | 密码 | 身份 |
| ---- | ---- | ---- |
| `admin` | `admin123` | 管理员 |
| `teacher` | `123456` | 教师 |
| 学生（班级 + 姓名 + `123456`） | — | 学生 |

> 学生账号的用户名即姓名，由 seed.py 自动生成 52 名学生；也可在学生端登录页通过「班级 + 姓名」自助注册。

---

## 生产环境部署

> **警告**：生产环境必须修改默认密钥和密码，否则存在严重安全风险。

### 环境要求

| 工具 | 最低版本 |
| ---- | -------- |
| Python | 3.10+ |
| Node.js | 18+ |
| Nginx | 1.20+ |
| 数据库 | SQLite（默认）/ MySQL 8.0 / PostgreSQL 14+ |

### 1. 构建前端

```bash
cd frontend
npm install
npm run build          # 产物输出到 dist/ 目录
```

构建产物位于 `frontend/dist/`，包含压缩后的静态资源（JS/CSS/HTML），Vite 自动按路由拆分 chunk。

### 2. 配置后端环境变量

```bash
cd backend
cp .env.example .env
```

编辑 `.env` 文件，**生产环境必须修改以下配置**：

```env
# 环境标识
ENV=production

# 【必改】JWT 签名密钥，生成命令：python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=替换为随机生成的64位十六进制字符串

# 数据库（默认 SQLite，切换 MySQL/PostgreSQL 见 database.py 文件头注释）
DATABASE_URL=sqlite:///./techhub.db

# 允许跨域的前端地址（多个用逗号分隔）
CORS_ORIGINS=http://localhost,http://your-domain.com

# 文件上传大小限制（字节）
MAX_UPLOAD_SIZE=20971520
```

> **警告**：切勿使用 `SECRET_KEY` 的默认值，否则 JWT Token 可被伪造。

### 3. 安装后端依赖

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# 或 .venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 4. 初始化数据库

```bash
# 生成初始数据（可选，仅首次部署需要）
python -m app.seed

# 若不生成假数据，启动时也会自动建表
```

### 5. 启动后端服务

**方式 A：直接启动（单机小规模）**

```bash
python run.py    # 端口 8080，单进程
```

**方式 B：Gunicorn 多进程（推荐生产环境）**

```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8080 app.main:app
```

参数说明：
- `-w 4`：4 个 worker 进程（建议设为 CPU 核心数 × 2）
- `-k uvicorn.workers.UvicornWorker`：使用 Uvicorn ASGI worker
- `-b 0.0.0.0:8080`：监听所有网卡的 8080 端口

### 6. 配置 Nginx 反向代理

创建 `/etc/nginx/sites-available/techhub`：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    root /path/to/techhub/frontend/dist;
    index index.html;

    # 前端页面（SPA 路由支持）
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理到后端
    location /api {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 上传文件访问
    location /uploads {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
    }

    # 静态资源缓存（7 天）
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1024;
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/techhub /etc/nginx/sites-enabled/
sudo nginx -t           # 测试配置
sudo systemctl reload nginx
```

### 7. 配置 HTTPS（推荐）

```bash
# 使用 Certbot 获取免费 SSL 证书
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 8. 使用 systemd 管理后端服务

创建 `/etc/systemd/system/techhub.service`：

```ini
[Unit]
Description=TechHub Backend
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/path/to/techhub/backend
Environment="PATH=/path/to/techhub/backend/.venv/bin"
ExecStart=/path/to/techhub/backend/.venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8080 app.main:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable techhub
sudo systemctl start techhub
sudo systemctl status techhub   # 检查运行状态
```

### 9. 验证部署

```bash
# 1. 健康检查
curl http://localhost:8080/health
# 预期返回：{"status":"ok"}

# 2. 前端页面
curl http://localhost/
# 预期返回：HTML 页面

# 3. 登录测试
curl -X POST http://localhost/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
# 预期返回：{"token":"...","user":{...}}
```

---

## 自动化测试

```bash
cd backend
python -m pytest tests/ -v
```

测试覆盖：登录认证、权限隔离、作业流程、优秀作品评选、CRUD 操作、越权场景。

## 配置参考

| 环境变量 | 说明 | 默认值 | 生产建议 |
| ---- | ---- | ---- | ---- |
| `ENV` | 运行环境 | `development` | `production` |
| `SECRET_KEY` | JWT 签名密钥 | 开发默认值 | **必须修改**为随机 64 位 hex |
| `DATABASE_URL` | 数据库连接串 | `sqlite:///./techhub.db` | MySQL/PostgreSQL 连接串 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token 有效期 | `1440`（24h） | 按需调整 |
| `MAX_UPLOAD_SIZE` | 上传文件大小上限 | `20971520`（20MB） | 按需调整 |
| `CORS_ORIGINS` | 允许跨域的前端地址 | `http://localhost:5173` | 生产域名 |
| `ALGORITHM` | JWT 签名算法 | `HS256` | 保持默认 |

## 故障排除

| 问题 | 原因 | 解决方案 |
| ---- | ---- | -------- |
| 前端页面空白 | Nginx 未正确配置 SPA 路由 | 确认 `try_files $uri /index.html` 配置 |
| API 返回 500 | 数据库迁移未完成 | 重启后端，检查日志中的迁移信息 |
| 文件上传失败 | 上传目录权限不足 | `chmod 755 backend/uploads` |
| 登录后立即跳回登录页 | Token 过期或 SECRET_KEY 变更 | 清除浏览器 localStorage，重新登录 |
| 图表不显示 | ECharts DOM 未就绪 | 刷新页面，等待数据加载完成 |
| `address already in use` | 端口被占用 | 修改 `run.py` 中的 `port` 参数 |
| 数据库文件损坏 | 异常断电 | 恢复 `techhub.db` 备份文件 |

## License

MIT