# PROJECT_STATUS 项目状态管理

## 当前项目

- 项目名称：ai-order-system / 外贸订单解析系统
- 当前聊天窗口：V4第二聊天窗口
- 当前定位：在已有 V3 稳定业务流程基础上，继续整理 V4 结构化订单、规则渲染和长期协作管理文档。

## 当前系统能力概览

这个项目用于把客户聊天内容整理成外贸订单信息，并进一步生成 Excel 订单文件。系统目前主要包含：

- 客户聊天内容输入和导入。
- 使用 DeepSeek API 解析订单字段。
- 人工确认和修改订单字段。
- 字段库管理。
- Excel 模板上传、模板映射和模板配置。
- 文档编号和产品编码生成。
- 产品描述模板管理和生成。
- 图片字段上传、图片素材池、图片排序和删除。
- Layout Engine 排版配置和 Excel 渲染。
- 本地输出、下载和打开输出目录。
- V4 Product Schema、Example Order、Renderer、Excel Render Rules、Rule Preview、Rule Executor 实验链路。

## 当前已完成模块

- FastAPI 后端入口：`app/main.py`。
- 首页订单解析和确认页面：`static/index.html`。
- 配置中心页面：`static/config.html`。
- V4 Schema 页面：`static/v4_schema.html`。
- AI 解析模块：`app/ai_parser.py`。
- 字段库模块：`app/field_library.py`。
- 模板映射模块：`app/template_manager.py`。
- Excel 生成模块：`app/excel_generator.py`。
- 图片管理模块：`app/image_manager.py`。
- 产品描述模板模块：`app/description_template_manager.py`。
- Layout Engine 相关模块：`app/layout_engine.py`、`app/layout_schema.py`、`static/js/layout_designer.js`、`static/js/region_inspector.js`。
- V4 结构化实验模块：`app/v4_schema.py`、`app/v4_examples.py`、`app/v4_validator.py`、`app/v4_renderer.py`、`app/v4_excel_rules.py`、`app/v4_excel_rule_executor.py`、`app/v4_template_rule_executor.py`。
- V4 示例和规则文件：`v4/schemas/`、`v4/examples/`。

## 当前未完成 / 待优化模块

- V4 目前仍偏实验链路，尚未完全接入 V3 首页正式订单流程。
- V4 Rule Executor 后续需要更稳定地读取真实 Excel 模板副本，再按规则写入。
- 部分历史中文文件在终端中可能显示乱码，后续应逐步统一为 UTF-8。
- 前端脚本仍有较多内联逻辑，后续如要大改，应先建立专项重构任务。
- AI 解析、产品描述、图片、Layout、Excel 生成是核心链路，修改时需要小步验证。
- 暂未引入数据库、多用户登录、权限系统。

## 当前运行方式

开发运行方式：

```powershell
conda run -n ai-order-system uvicorn app.main:app --reload
```

常用访问地址：

- 首页：http://127.0.0.1:8000/
- 配置中心：http://127.0.0.1:8000/config
- V4 Schema 页面：http://127.0.0.1:8000/v4-schema

常用检查方式：

```powershell
conda run -n ai-order-system python -m py_compile app/main.py app/routes/images.py app/routes/parse.py app/routes/templates.py app/routes/v4.py
```

## 当前重要注意事项

- 不要轻易改动现有 API 路径，前端页面依赖这些接口。
- 不要在 UI 小修改中顺手重构 AI 解析、Excel 生成或 Layout Engine。
- 文档编号默认值不应被 AI 解析结果随意覆盖。
- Excel 模板、字段映射、图片路径、输出目录都要保持兼容。
- V4 新功能应先在 `/v4-schema` 验证，再考虑接入正式订单流程。
- 每次较大修改后，需要同步更新 `PROJECT_STATUS.md`、`PROJECT_STRUCTURE.md`、`VERSION_HISTORY.md`、`TASKS.md`、`COLLAB_SYNC.md` 和 `docs/README.md`。
- 新聊天开始时，应优先读取这些管理文档，再读取代码。

## 最近一次更新记录

- 更新窗口：V4第二聊天窗口
- 更新内容：建立根目录项目管理文档体系，用于状态同步、结构管理、版本管理、任务管理和协作同步。
- 本次代码影响：仅新增/更新 Markdown 文档，不修改业务代码。

最后更新：V4第二聊天窗口
