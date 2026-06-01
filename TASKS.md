# TASKS 任务管理

## 当前主计划

### 阶段1：完善中层全部能力

任务表：

- [✓] 冻结中层规范
- [>] 补文档模型
  - [>] 2.1 semantic_summary统一审计
  - [ ] 2.2 视觉字段规范
  - [ ] 2.3 条件字段规范
  - [ ] 2.4 metadata统一
- [ ] 补条件逻辑
- [ ] 补选择逻辑
- [ ] 补表格逻辑
- [ ] 补视觉逻辑
- [ ] AI合同构建器完善
- [ ] 工作区构建器完善
- [ ] 导出策略构建器完善
- [ ] 打通中层内部主链
- [ ] 中层独立验证

### 阶段2：完善映射配置层

（待展开）

### 阶段3：完善工作页交互

（待展开）

### 阶段4：完善导出层

（待展开）

### 阶段5：稳定性验证

（待展开）

### 阶段6：产品化接入

（待展开）

---

## 历史任务区

### 已完成的历史任务

### 任务：跑通基础订单解析和 Excel 生成

- 任务目标：把客户聊天内容解析为订单字段，并生成 Excel 文件。
- 涉及文件：`app/ai_parser.py`、`app/excel_generator.py`、`static/index.html`。
- 当前状态：已完成，属于当前业务主流程。
- 备注：后续修改需要重点保护，避免影响日常使用。

### 任务：建立配置中心和模板映射

- 任务目标：让用户可以维护字段、模板、映射和导出设置。
- 涉及文件：`static/config.html`、`app/template_manager.py`、`app/routes/templates.py`、`data/template_profiles.json`。
- 当前状态：已完成。
- 备注：模板 Profile 和 Excel 模板文件是系统长期使用的关键数据。

### 任务：支持文档编号和产品编码

- 任务目标：根据业务员、客户简称、成交日期、序号、产品信息生成文档编号和产品编码。
- 涉及文件：`app/template_manager.py`、`app/excel_generator.py`、`static/index.html`。
- 当前状态：已完成。
- 备注：默认值不应被 AI 解析结果随意覆盖。

### 任务：支持产品描述模板

- 任务目标：通过模板生成产品描述，并允许人工确认。
- 涉及文件：`app/description_template_manager.py`、`data/description_templates/`、`app/ai_parser.py`。
- 当前状态：已完成。
- 备注：导出到 Excel 时需要注意去掉来源标记。

### 任务：支持图片字段和图片素材池

- 任务目标：支持上传订单图片、维护图片素材池，并参与 Excel 导出。
- 涉及文件：`app/image_manager.py`、`app/routes/images.py`、`static/index.html`。
- 当前状态：已完成。
- 备注：图片路径和缓存目录不要随意改动。

### 任务：建立 V4 结构化实验链路

- 任务目标：验证 Product Schema、Example Order、Renderer、Excel Rules、Rule Executor 的闭环。
- 涉及文件：`app/routes/v4.py`、`app/v4_schema.py`、`app/v4_examples.py`、`app/v4_renderer.py`、`app/v4_excel_rules.py`、`v4/`。
- 当前状态：已完成初步闭环。
- 备注：目前仍是实验链路，不等于完全接入正式业务流程。

### 任务：完成 V4 接入前稳定性检查

- 任务目标：统一版本标识，确认 V4 路由注册状态，新增 V4 健康检查接口，并建立接入前检查清单。
- 涉及文件：`app/main.py`、`app/routes/v4.py`、`docs/V4_INTEGRATION_CHECKLIST.md`、项目管理文档。
- 当前状态：已完成。
- 备注：新增 `GET /api/v4/health`；V4 仍保持独立实验链路，不直接接入首页正式订单流程。

## 进行中

### 任务：整理项目管理文档体系

- 任务目标：建立状态同步、结构管理、版本管理、任务管理和协作同步文件。
- 涉及文件：`PROJECT_STATUS.md`、`PROJECT_STRUCTURE.md`、`VERSION_HISTORY.md`、`TASKS.md`、`COLLAB_SYNC.md`、`docs/README.md`。
- 当前状态：持续维护。
- 备注：这些文件用于 ChatGPT / Codex / GitHub / 新聊天之间同步信息；本次已补充 V4 接入前稳定性检查记录。

## 下一步

### 任务：保证 ChatGPT / Codex / GitHub 之间信息同步

- 任务目标：每次较大修改后，同步更新项目管理文档，并通过 GitHub 保存版本。
- 涉及文件：所有项目管理文档、代码变更文件、Git 提交记录。
- 当前状态：下一步重点。
- 备注：新聊天开始时，先读管理文档，再读代码。

### 任务：检查 V4 是否需要接入正式业务流程

- 任务目标：判断 V4 Schema 和规则渲染是否已经稳定到可以接入首页订单流程。
- 涉及文件：`static/v4_schema.html`、`app/routes/v4.py`、`app/v4_*.py`、`docs/V4_INTEGRATION_CHECKLIST.md`。
- 当前状态：下一步继续验证。
- 备注：当前结论是不直接接入首页，继续通过 `/v4-schema` 和 `/api/v4/health` 独立验证。

### 任务：整理编码和中文显示问题

- 任务目标：逐步统一历史文档和代码注释的中文编码，减少终端乱码。
- 涉及文件：历史 Markdown 文档、部分 Python 注释和字符串。
- 当前状态：下一步。
- 备注：这类改动容易产生大量 diff，应单独进行。

## 以后再做

### 任务：前端脚本模块化整理

- 任务目标：把较大的页面脚本拆成更容易维护的模块。
- 涉及文件：`static/index.html`、`static/config.html`、`static/js/`。
- 当前状态：以后再做。
- 备注：不要和业务功能修改混在一起。

### 任务：更完整的自动化测试

- 任务目标：增加后端接口、Excel 生成、V4 规则执行的自动化检查。
- 涉及文件：未来测试目录、`app/`。
- 当前状态：以后再做。
- 备注：当前主要依赖编译检查和人工流程验证。

### 任务：数据库化存储

- 任务目标：把 JSON 文件存储升级为数据库。
- 涉及文件：`data/`、配置管理、模板管理、字段管理。
- 当前状态：以后再做。
- 备注：当前阶段 JSON 文件更直观，适合非专业用户维护。

## 暂缓

### 任务：多用户登录和权限系统

- 任务目标：支持不同用户登录和权限区分。
- 涉及文件：后端认证、前端登录页面、数据存储。
- 当前状态：暂缓。
- 备注：当前项目更像本地工具，暂不优先。

### 任务：Word / PDF Report Engine

- 任务目标：在 Excel 之外生成 Word 或 PDF 报告。
- 涉及文件：未来报告生成模块。
- 当前状态：暂缓。
- 备注：可作为 V5 方向。

最后更新：V4第二聊天窗口
