# PROJECT_STRUCTURE 项目结构管理

## 目录结构说明

项目根目录是 `ai-order-system`。主要目录和文件职责如下：

```text
ai-order-system/
  app/                 后端 Python 业务代码
  static/              前端页面、CSS、JavaScript
  templates/           Excel 模板和上传后的模板文件
  output/              生成的 Excel 输出文件
  data/                字段、映射、图片字段、产品描述模板等数据
  docs/                长期项目文档和开发记录
  v4/                  V4 结构化订单实验文件
  uploads/             用户上传图片和图片素材池
  config/ configs/     配置样例或历史配置
  logs/                运行日志
  build/ dist/         打包构建产物
```

## 重要目录职责

- `app/`：核心后端代码目录。负责 API、AI 解析、模板管理、Excel 生成、图片处理、Layout Engine 和 V4 实验链路。
- `static/`：前端页面目录。`index.html` 是首页订单处理页面，`config.html` 是配置中心，`v4_schema.html` 是 V4 实验页面。
- `templates/`：Excel 模板目录。`order_template.xlsx` 是基础模板，`templates/uploads/` 保存用户上传的模板文件。
- `output/`：生成结果目录。系统生成的 Excel 文件通常放在这里，也可能同步到用户配置的本地目录。
- `data/`：项目运行数据目录。保存字段库、模板映射、图片字段、应用设置和产品描述模板。
- `docs/`：长期文档目录。用于保存更详细的设计说明、开发记录、问题复盘和后续交接材料。
- `v4/`：V4 结构化订单实验目录。保存 Product Schema、Example Order、Excel Render Rules 和 V4 说明文档。
- `uploads/`：上传资源目录。主要保存订单图片、图片素材池和临时资源。

## 核心文件职责

- `app/main.py`：FastAPI 应用入口，挂载静态文件，注册路由，提供首页、配置中心和 V4 页面入口。
- `app/routes/__init__.py`：核心 API 路由集合，包括字段、设置、产品描述、Excel 生成、输出同步、缓存清理等接口。
- `app/routes/parse.py`：AI 解析相关接口。
- `app/routes/images.py`：图片上传、图片字段和图片素材池相关接口。
- `app/routes/templates.py`：模板映射、模板上传和模板配置相关接口。
- `app/routes/v4.py`：V4 Product Schema、Example、Renderer、Excel Rules、规则执行和下载相关接口。
- `app/ai_parser.py`：调用 DeepSeek API，从客户聊天中提取订单字段，并处理日期、产品描述来源标记等逻辑。
- `app/template_manager.py`：管理模板 Profile、Excel 模板文件、字段映射、文档编号设置、产品描述设置和 Layout 配置。
- `app/excel_generator.py`：根据订单数据、模板映射、产品描述、图片和 Layout 配置生成 Excel 文件。
- `app/field_library.py`：维护字段库，包括系统保留字段和用户自定义字段。
- `app/image_manager.py`：处理图片字段、上传图片、图片素材池和图片路径解析。
- `app/layout_engine.py`：根据 Layout 配置把文字和图片渲染到 Excel 指定区域。
- `app/description_template_manager.py`：管理产品描述模板文件。
- `app/app_settings.py`：管理应用设置，例如 DeepSeek API Key、本地导出同步目录、默认业务信息等。
- `app/runtime_paths.py`：处理开发环境和打包环境下的基础路径。
- `app/logger.py`：统一日志工具。

## V4 相关文件职责

- `app/v4_schema.py`：读取和保存 V4 Product Schema。
- `app/v4_examples.py`：读取和保存 V4 Example Order。
- `app/v4_validator.py`：校验 Example Order 是否符合 Schema。
- `app/v4_renderer.py`：把结构化 Example 转成可渲染的 description_fields。
- `app/v4_excel_rules.py`：读取和保存 Excel 渲染规则。
- `app/v4_excel_rules_validator.py`：校验 Excel 渲染规则。
- `app/v4_excel_rule_preview.py`：生成规则预览操作。
- `app/v4_excel_rule_executor.py`：把规则预览执行到调试 Excel。
- `app/v4_template_rule_executor.py`：把规则执行到真实模板副本。
- `v4/schemas/product_schema.json`：V4 产品结构定义。
- `v4/schemas/excel_render_rules.json`：V4 Excel 渲染规则定义。
- `v4/examples/soft_capsule_order_example.json`：V4 示例订单。

## 文件类型分类

核心业务代码：

- `app/ai_parser.py`
- `app/template_manager.py`
- `app/excel_generator.py`
- `app/field_library.py`
- `app/image_manager.py`
- `app/layout_engine.py`
- `app/routes/*.py`
- `app/v4_*.py`

配置和数据文件：

- `data/fields.json`
- `data/template_profiles.json`
- `data/mappings.json`
- `data/image_fields.json`
- `data/app_settings.json`
- `data/description_templates/*.txt`
- `v4/schemas/*.json`
- `v4/examples/*.json`

静态页面和前端资源：

- `static/index.html`
- `static/config.html`
- `static/v4_schema.html`
- `static/css/*.css`
- `static/js/*.js`

模板和输出：

- `templates/order_template.xlsx`
- `templates/uploads/*.xlsx`
- `output/*.xlsx`

项目管理文档：

- `PROJECT_STATUS.md`
- `PROJECT_STRUCTURE.md`
- `VERSION_HISTORY.md`
- `TASKS.md`
- `COLLAB_SYNC.md`
- `docs/README.md`

最后更新：V4第二聊天窗口
