# TechHub 架构设计文档

> 版本：2.0 ｜ 更新：2026-08-24 ｜ 适用对象：后端 / 前端 / 测试 / 运维

## 1. 项目定位

TechHub 是一套面向中职学校的「教学 + 班主任一体化工作平台」，将原先分散的三个系统合并为**一套前后端分离**的应用：

| 原系统 | 定位 | 合并后形态 |
| ------ | ---- | ---------- |
| 在线作业提交平台 | 学生交作业、教师评优 | **学生端**（`/`） |
| 班级日志管理系统 | 班主任班级事务 | **管理端**模块（`/admin`） |
| 教师工作台 | 教师日常教务 | **管理端**模块（`/admin`） |

**核心设计目标**：一个账号、三角色、权限严格隔离。

## 2. 技术栈

| 层 | 技术 | 版本 | 说明 |
| --- | ---- | ---- | ---- |
| 后端框架 | FastAPI | 0.115 | 自动生成 OpenAPI 文档 |
| ORM | SQLAlchemy | 2.0 | 声明式模型 |
| 数据库 | SQLite | — | 单文件，可平滑切换 MySQL/PostgreSQL |
| 认证 | python-jose + bcrypt | — | JWT（HS256）+ bcrypt 密码哈希 |
| 前端框架 | Vue 3 | 3.4 | Composition API + `<script setup>` |
| UI 库 | Element Plus | 2.7 | 后台与表单 |
| 图表 | ECharts | 5.5 | 数据看板、通宿生统计 |
| 构建 | Vite | 5.4 | 开发热更新 + 生产构建 |
| Markdown | marked + DOMPurify | 12 | 作业正文/日志渲染 + XSS 防护 |
| Excel | openpyxl | 3.1 | 导入/导出 |
| 测试 | pytest | — | 后端自动化测试 |

## 3. 目录结构

```
techhub/
├── backend/
│   ├── app/
│   │   ├── main.py            # 应用入口：CORS、静态挂载、路由注册、建表、迁移
│   │   ├── config.py          # 配置（env 驱动）
│   │   ├── database.py        # engine / SessionLocal / Base / get_db / run_migrations
│   │   ├── security.py        # 密码哈希 + JWT 签发/校验
│   │   ├── deps.py            # 依赖：get_current_user / require_roles
│   │   ├── utils.py           # to_dict / safe_filename 等工具
│   │   ├── audit.py           # 操作审计日志 + 批量查询辅助
│   │   ├── schemas.py         # Pydantic 请求/响应模型
│   │   ├── models/            # SQLAlchemy 模型（按域分组）
│   │   │   ├── user.py        #   User
│   │   │   ├── school.py      #   School / Classroom / Student
│   │   │   ├── homework.py    #   Assignment / Submission / ExcellentWork / WorkComment
│   │   │   ├── workbench.py   #   Score / Leave / Point / Communication / Resource / Exam / Seat / Setting / ImportHistory
│   │   │   ├── classlog.py    #   WorkLog / ClassPlan / TeacherPlan / Schedule / Activity / Talk / ReturnRecord / Performance / StudentComment
│   │   │   └── operation_log.py
│   │   ├── routers/           # 按业务域分组的 API 路由
│   │   │   ├── auth.py        #   登录/注册/密码
│   │   │   ├── meta.py        #   班级选项、编程练习（公开）
│   │   │   ├── homework.py    #   作业/提交/优秀作品/评论
│   │   │   ├── students.py    #   学校/班级/学生 CRUD + Excel 导出 + 密码管理 + 通宿生统计
│   │   │   ├── workbench.py   #   教师工作台（成绩/考勤/积分/沟通/资源/试卷/座位）+ 批量导入
│   │   │   ├── classlog.py    #   班级日志（日志/计划/课表/活动/谈心/返校/表现/评语）
│   │   │   ├── admin.py       #   账号管理 / 系统设置 / 数据看板
│   │   │   └── uploads.py     #   通用文件上传
│   │   └── seed.py            # 假数据生成（Faker）
│   ├── tests/                 # pytest 自动化测试
│   ├── requirements.txt
│   └── run.py                 # uvicorn 启动入口
├── frontend/
│   ├── src/
│   │   ├── api/               # axios 封装 + 各域 API 函数
│   │   │   └── index.js       # 所有 API 接口定义
│   │   ├── router/            # 路由 + 角色守卫
│   │   ├── layout/            # StudentLayout / AdminLayout（可折叠侧边栏）
│   │   ├── components/        # Markdown / MarkdownEditor / StudentSelect
│   │   ├── views/student/     # 学生端页面（8 个）
│   │   └── views/admin/       # 管理端页面（22 个）
│   ├── vite.config.js         # dev 代理 /api、/uploads → 8080
│   └── package.json
└── docs/                      # 本文档集
```

## 4. 权限模型

| 角色 | 登录入口 | 可访问范围 | 服务端约束 |
| ---- | -------- | ---------- | ---------- |
| `student` | `/`（学生端） | 仅作业提交平台 | `require_student` / `get_current_user` |
| `teacher` | `/admin`（管理端） | 作业管理 + 工作台 + 班级日志 + 系统管理 | `require_teacher` |
| `admin` | `/admin`（管理端） | 同教师 + 账号管理 | `require_teacher`（含 admin） |

**双重校验**：
- 后端：`deps.require_roles(*roles)` 依赖注入，越权返回 `403`；
- 前端：`router.beforeEach` 路由守卫，按角色重定向。

**数据隔离**：学生只能看到/提交**本班级**的作业（`homework._check_student_access`）。

**学生登录**：学生通过「班级 + 姓名 + 密码」登录，账号由教师创建学生档案时自动同步生成。

## 5. 数据模型概览

### 5.1 表清单（28 张表）

| 域 | 表 | 关键字段 |
| --- | --- | -------- |
| 认证 | `users` | username、password_hash、role、class_id、name |
| 基础 | `schools` / `classrooms` / `students` | 学校/班级/学生档案（student_type 通学/寄宿） |
| 作业 | `assignments` / `submissions` / `excellent_works` / `work_comments` | 任务/提交/优秀/评论 |
| 工作台 | `scores` / `leaves` / `points` / `communications` / `resources` / `exams` / `seats` / `settings` | 成绩/考勤/积分/沟通/资源/试卷/座位/设置 |
| 日志 | `work_logs` / `class_plans` / `teacher_plans` / `schedules` / `activities` / `talks` / `return_records` / `performances` / `student_comments` | 日志/计划/课表/活动/谈心/返校/表现/评语 |
| 审计 | `operation_logs` | 操作审计日志 |
| 导入 | `import_history` | 数据导入历史（类型/文件名/成功/失败/错误详情） |

### 5.2 关键关联

- `points.performance_id` → `performances.id`：积分关联表现记录，可实现积分追溯
- `students.class_id` → `classrooms.id`：学生归属班级
- `users.class_id + users.name` → 学生账号唯一标识（取代原 username 唯一约束）
- `import_history.user_id` → `users.id`：导入操作人追溯

> 说明：模型刻意**不定义 ORM relationship**，关联查询通过 `db.get()` / `filter()` 手动完成，以避免模块间循环 import。

## 6. API 约定

- **前缀**：`/api`
- **认证**：`Authorization: Bearer <token>`（`HTTPBearer`）
- **响应**：成功返回 JSON 对象或 `{items, total}`；错误用 `HTTPException`（`{detail: ...}`）
- **分页**：`?page=&page_size=`（默认 20），`keyword` / `class_id` / `student_id` 等过滤
- **文件**：`POST /api/uploads` 上传 → 返回 `{url, filepath, filename, size}`；`/uploads/**` 静态访问
- **文件上传**：试卷上传 `POST /api/exams/upload`（FormData），下载 `GET /api/exams/{id}/download`
- **批量导入**：`POST /api/students/import` / `POST /api/scores/import`（FormData），含模板下载
- **文档**：`/docs`（Swagger UI）、`/redoc`

## 7. 前端架构

### 7.1 布局系统

- **AdminLayout**：深色可折叠侧边栏（220px ↔ 64px）+ 顶部面包屑 + 用户菜单
- **StudentLayout**：顶部导航栏 + 居中内容区 + 底部页脚
- 全局 CSS 变量系统：品牌色、中性色、阴影、圆角、间距统一管理

### 7.2 组件复用

| 组件 | 用途 | 使用页面 |
| ---- | ---- | ---- |
| `Markdown.vue` | Markdown 渲染（marked + DOMPurify） | 作业审阅、优秀作品 |
| `MarkdownEditor.vue` | Markdown 编辑器 | 作业创建/编辑 |
| `StudentSelect.vue` | 学生下拉选择器 | 积分、表现、成绩、谈心等 |

### 7.3 数据可视化

- ECharts 用于数据看板（折线图、饼图）和学生管理（通宿生环形图）
- 图表支持点击交互（通宿生图点击跳转明细）

## 8. 部署架构

### 开发环境
```
浏览器 → Vite(:5173) ──/api,/uploads──▶ FastAPI(:8080) ──▶ SQLite(techhub.db)
```

### 生产环境（建议）
```
浏览器 → Nginx(:80)
         ├── /            → 前端静态产物(dist/)
         ├── /api、/uploads → uvicorn(多 worker, :8080)
         └── HTTPS 证书终止
```
- 数据库迁移到 MySQL/PostgreSQL（SQLAlchemy 连接串切换即可）
- 使用 `gunicorn -k uvicorn.workers.UvicornWorker` 多进程部署

## 9. 数据库迁移策略

- 启动时自动执行 `create_all`（新表）+ `run_migrations()`（增量字段/表）
- 迁移逻辑在 `database.py` 中，通过 SQLAlchemy `inspect` 检查现有结构
- 新增字段使用 `ALTER TABLE ADD COLUMN`，新表使用 `CREATE TABLE IF NOT EXISTS`
- 生产环境建议引入 Alembic 做正式迁移管理

## 10. 关键设计决策（ADR 摘要）

| 决策 | 选择 | 理由 |
| ---- | ---- | ---- |
| 后端框架 | FastAPI（弃用原 Express） | 原生 OpenAPI、类型提示、异步支持 |
| 前端框架 | Vue3（弃用原 React） | 与班级日志系统一致，Element Plus 生态成熟 |
| ORM 无 relationship | 手动查询 | 避免循环 import，换取模型文件解耦 |
| 数据库 | SQLite | 单文件易备份，满足单校规模；预留迁移路径 |
| 认证 | JWT + bcrypt | 无状态、前后端分离友好 |
| 密码哈希 | bcrypt（弃用 passlib） | 规避 passlib/bcrypt 4.x 兼容问题 |
| 学生账号 | 班级+姓名 定位 | 解决重名问题，支持自助注册 |
| 积分联动 | 表现创建时自动生成积分 | 减少重复录入，积分可追溯 |
| 文件管理 | 试卷上传独立接口 | 格式校验、分块写入、大小限制 |
| 批量导入 | openpyxl + 逐行校验 | 精确错误定位，导入历史可追溯 |