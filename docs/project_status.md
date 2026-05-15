# ai-order-system V3 Stable 状态说明

## 当前版本状态

ai-order-system 当前处于 V3 Stable 稳定迭代状态。本阶段目标是稳定外贸订单解析、人工确认、产品描述、图片、Layout Engine 和 Excel 导出的完整链路。日常修改应以小步、可验证、低风险为主，不建议在同一轮中混入大规模架构调整、后端重构和前端重排。

本文件是项目功能与规则的工作记录。后续改动如果改变了页面行为、数据流、Excel 规则或 Layout Engine 规则，应同步更新这里。

## 核心工作流

1. 在配置中心创建或选择模板映射。
2. 上传 Excel 模板并配置普通字段、图片字段、文档编号、产品描述模板和 Layout Engine。
3. 首页输入或导入客户聊天内容。
4. 选择模板映射。
5. 点击 AI解析，普通订单字段由 AI 填充。
6. 人工确认文档编号、普通字段、产品描述和图片。
7. 生成 Excel。
8. 根据配置同步到本地订单目录，或打开订单目录检查结果。

## 当前核心功能

- AI解析客户聊天内容。
- txt/html 聊天记录导入。
- 普通订单字段确认与人工编辑。
- 字段库管理。
- 多模板映射。
- Excel 模板上传、删除和映射保存。
- 文档编号生成与写入。
- 文档编号可作为导出文件名。
- 产品描述模板管理与 AI 生成。
- 产品描述来源前缀标记：[AI] / [模板] / [系统] / [人工]。
- 图片字段上传。
- 图片素材池。
- 图片素材池点击上传、拖拽上传、Ctrl+V 粘贴上传。
- 图片素材池预览、删除、拖拽排序。
- V3 Layout Engine 实验功能。
- Layout 背景图上传，用模板截图辅助排版。
- Layout Region 拖拽、缩放和 Inspector 编辑。
- Layout Block 支持描述字段和图片类块。
- Layout 图片块可使用普通图片字段，也可使用图片素材池。
- Excel 模板导出。
- 本地同步导出。
- 打开订单目录。
- 缓存清理。
- AI 设置锁定/解锁与保存。

## 首页规则

首页文件主要是 `static/index.html`。

### 顶部

- 顶部标题和“进入配置中心”在同一行。
- 顶部整体高度应保持紧凑。

### 左侧客户聊天区

- 左侧区域顺序：
  1. 客户聊天内容
  2. 聊天 textarea
  3. 导入 txt/html 聊天记录
  4. AI解析按钮
- 左侧不放模板选择。
- `#message` 必须保留。
- `#chatImportInput` 必须保留。
- `#parseBtn` 必须保留。
- AI解析按钮在 1080p 屏幕下应无需整体页面滚动即可看到。
- body 不应出现整体页面滚动条。

### 右侧订单确认区

- 右侧区域保持独立滚动。
- 右侧顺序：
  1. 订单信息确认
  2. 选择模板映射
  3. 当前映射提示
  4. 文档编号信息
  5. 普通字段确认
  6. 产品描述
  7. 图片上传/图片素材池
  8. 生成按钮区域
- `#profileSelect` 必须保留。
- `#profileTips` 必须保留。
- “选择模板映射”应作为 section 标题，视觉层级与“文档编号信息”一致。
- 当前映射提示保持灰色小提示，不做成标题。

## AI解析规则

- `parseMessage()` 负责调用 `/api/parse`。
- AI解析只应填充普通订单字段和可由 AI 推断的订单信息。
- AI解析不应覆盖配置中心固定默认值。
- AI解析后可自动选择匹配的模板映射，例如根据产品形式匹配模板。
- AI解析失败时在左侧错误区显示错误。
- 解析成功后应刷新文档编号区、普通字段区、产品描述区和图片上传区。
- 不要在 UI 小修中改动 `parseMessage()` 的业务逻辑。

## 文档编号规则

文档编号信息属于订单确认的一部分，但其中若干字段来自配置中心固定默认值。

### 固定默认字段

以下字段属于配置中心固定默认值：

- 默认业务员英文名：`sales_name`
- 默认业务员代号：`salesperson_code`
- 默认公司/客户简称：`company_code`
- 默认序号：`sequence`

兼容/别名字段也按固定默认处理：

- `sales_code`
- `company_short_name`
- `serial_prefix`
- `default_sales_name`
- `default_salesperson_code`
- `default_company_code`
- `default_sequence`

### 关键规则

- 固定默认字段只用于页面初始化。
- 固定默认字段不应被 AI解析结果覆盖。
- 固定默认字段不应随 `parseMessage()` 自动变化。
- 首页允许用户手动修改这些输入框。
- 用户手动修改后，再次 AI解析仍应保持用户当前输入。
- 重新生成文档编号必须使用当前输入框里的值。
- 输入框存在时，重新生成文档编号不应偷偷回退到配置默认值。

### 文档编号组成

默认文档编号规则：

`{sales_name}-{company_code}{deal_date_yyyymmdd}{sequence}-{product_code}`

默认产品编码规则：

`{salesperson_code}{deal_date_mmdd_no_leading_zero}{ingredient_initials}{dosage_form_code}`

剂型代码映射：

- 硬胶囊/胶囊：C
- 软胶囊：S
- 软糖：G
- 滴剂/液体饮料：D
- 粉末/固体饮料：B 或 P，按当前规则实现为准
- 凝胶/果冻：N
- 片剂/压片：T
- 泡腾片：E

### 日期规则

- 网页日期可以用浏览器 date input 显示。
- 内部导出日期统一按 `YYYYMMDD`。
- `order_date` 和 `deal_date` 会互相补齐。

## 普通字段规则

- 普通字段由字段库管理。
- 每个模板映射可单独勾选启用字段。
- 启用字段会显示在首页“普通字段确认”区域。
- 普通字段可配置 Excel 单元格。
- 普通字段可配置默认值。
- 文档编号保留字段不应作为普通字段显示。
- 系统字段 key 不能随意删除或改名。

## 产品描述规则

- 产品描述按模板生成。
- 产品描述模板存放在 `data/description_templates/`。
- 配置中心可选择、编辑和恢复产品描述模板。
- 首页点击 AI解析后，如当前模板启用产品描述，系统会调用 `/api/generate-description`。
- 产品描述网页中保留来源标记。
- Excel 导出时去掉来源标记。
- 当前仍不使用 Excel 富文本红字。
- 产品描述内容可人工编辑。
- 人工编辑时会标记 `[人工]`。
- 系统自动同步产品编码时使用 `[系统]` 标记。
- 产品描述中的成分缩写可用于文档编号产品编码。
- 成分缩写有人工编辑保护，人工改过后 AI/系统不应轻易覆盖。

## 图片字段规则

- 图片字段是全局字段库的一部分。
- 每个模板映射可单独启用图片字段。
- 首页可为每个启用图片字段上传图片。
- 支持 PNG/JPG/JPEG。
- 图片上传接口为 `/api/upload-image`。
- 图片字段参与 Excel 写入和 Layout Engine。
- 不要改变图片缓存路径规则，除非同步改后端和导出逻辑。

## 图片素材池规则

图片素材池是可选的订单级图片集合。

### 支持操作

- 点击上传。
- 拖拽上传。
- Ctrl+V 粘贴上传。
- 预览。
- 删除。
- 拖拽排序。

### 粘贴上传规则

- 粘贴事件只在图片素材池区域处理。
- 从 `event.clipboardData.items` 中读取 `image/*`。
- 非图片剪贴板内容直接忽略。
- 剪贴板图片转换为 `File` 后，复用现有 `uploadPoolImages(files)`。
- 上传接口仍是 `/api/image-pool/upload`。
- 不新增后端接口。
- 上传失败使用现有 `submitResult` 错误提示。
- 粘贴/拖入时允许轻微视觉反馈，例如蓝色边框和浅蓝背景，持续约 500ms。

### Layout Engine 关系

- 图片素材池可参与 Layout Engine。
- Layout Block 配置 `use_image_pool` 时，可以从素材池读取图片。
- 素材池顺序会影响 Layout 使用图片的顺序。
- 删除或排序素材池图片后，生成 Excel 应使用当前页面上的素材池状态。

## V3 Layout Engine 规则

Layout Engine 目前仍标注为实验功能，但已经是 V3 Stable 工作流的一部分。

### 配置中心功能

- 启用/关闭 Layout Engine。
- 新增 Region。
- 保存 Layout 配置。
- Layout 保存状态显示为：
  - `Layout 已保存`
  - `Layout 有未保存修改`
- Layout 保存状态应显示在“新增区域”和“保存 Layout 配置”按钮右侧。
- 切换模板映射时，如果 Layout 有未保存修改，应提示用户确认。
- 可上传模板背景图作为 Layout Designer 的视觉参考。
- 可读取 Excel 几何信息，用真实行列辅助定位。

### Designer 和 Inspector

- Region 支持拖拽、缩放。
- Region 可通过表单/Inspector 编辑名称、范围、显示状态等。
- Region 可包含多个 Block。
- Block 类型包括：
  - `description_fields`
  - `image`
  - `image_gallery`
  - `image_stack`
- Inspector 可编辑 Block 的 source keys、exclude keys、图片尺寸、间距、数量、是否使用图片素材池等。
- Layout Designer 的 UI 调整不应影响保存逻辑。

### 导出规则

- Layout Engine 在 Excel 生成阶段渲染。
- Layout 可写入产品描述字段文本。
- Layout 可写入单张图片、图片画廊和图片堆叠。
- 图片来源可以是普通图片字段或图片素材池。
- Layout 渲染失败应记录日志，不应无提示破坏整个导出链路。

## Excel 导出规则

- Excel 生成接口为 `/api/generate-excel`。
- 导出基于当前选择的模板映射和 Excel 模板文件。
- 普通字段写入映射单元格。
- 文档编号按配置写入指定单元格。
- 产品描述按配置写入指定单元格或由 Layout Engine 渲染。
- 图片字段按配置写入单元格或由 Layout Engine 渲染。
- 日期导出统一为 `YYYYMMDD`。
- 产品描述导出时去掉来源标记。
- 导出后可打开订单目录。
- 导出后可同步到配置的本地目录。
- 如果启用“文档编号作为文件名”，导出文件名应使用当前文档编号。

## 配置中心规则

配置中心文件主要是 `static/config.html`，Layout Designer 相关脚本主要在 `static/js/layout_designer.js` 和 `static/js/region_inspector.js`。

### 模板映射管理

- 可选择当前映射。
- 可新建映射。
- 可上传模板。
- 可删除当前模板文件。
- 可删除当前映射。
- 当前映射状态显示模板状态。

### 字段库管理

- 可新增普通字段。
- 可编辑字段中文名、key、类型、说明。
- 可删除非系统保留字段。
- 每个模板映射可设置字段启用、Excel 单元格、默认值和排序。

### 图片字段管理

- 可新增图片字段。
- 可启用/禁用图片字段。
- 可设置图片字段 Excel 单元格。

### 文档编号设置

- 可启用文档编号写入 Excel。
- 可设置文档编号写入单元格。
- 可设置默认业务员英文名、业务员代号、公司/客户简称、序号。
- 可设置文档编号规则。
- 可设置产品编码规则。
- 可设置是否用文档编号作为导出文件名。

### 产品描述设置

- 可启用产品描述模板。
- 可选择产品描述模板。
- 可设置产品描述写入单元格。
- 可编辑模板内容。
- 可恢复当前模板为系统默认内容。

### 本地导出设置

- 可设置 Excel 同步文件夹路径。
- 可测试同步路径。
- 可配置导出文件名规则相关选项。

### AI 设置

- AI 设置有锁定/解锁流程。
- 不应在普通 UI 调整中改动 AI 设置保存逻辑。

### 缓存清理

- 可清空 output、上传图片缓存和 Layout 临时图片。
- 不应影响模板、字段、映射和正式订单目录。

## 主要接口备忘

- `GET /api/fields`
- `POST /api/fields`
- `PUT /api/fields/{key}`
- `DELETE /api/fields/{key}`
- `GET /api/template-profiles`
- `POST /api/template-profiles`
- `DELETE /api/template-profiles/{profile_id}`
- `POST /api/template-profiles/{profile_id}/upload-template`
- `DELETE /api/template-profiles/{profile_id}/template`
- `POST /api/template-profiles/{profile_id}/mappings`
- `POST /api/template-profiles/{profile_id}/layout-config`
- `POST /api/template-profiles/{profile_id}/layout-preview`
- `GET /api/template-profiles/{profile_id}/geometry`
- `GET /api/app-settings`
- `POST /api/app-settings`
- `POST /api/test-export-sync-dir`
- `POST /api/parse`
- `POST /api/generate-description`
- `POST /api/generate-excel`
- `POST /api/sync-output`
- `POST /api/open-output-folder`
- `GET /api/download/{filename}`
- `GET /api/image-fields`
- `POST /api/image-fields`
- `POST /api/upload-image`
- `POST /api/image-pool/upload`
- `GET /api/description-templates`
- `GET /api/description-templates/{template_name}`
- `POST /api/description-templates/{template_name}`
- `POST /api/description-templates/{template_name}/restore-default`
- `POST /api/clear-cache`
- `GET /api/ai-settings/status`
- `POST /api/ai-settings/unlock`
- `POST /api/ai-settings`

## 前端稳定性规则

- 首页右侧保持独立滚动。
- body 不应出现整体滚动条。
- 左侧 AI解析按钮必须可见。
- 不要随意改关键 id：
  - `message`
  - `chatImportInput`
  - `parseBtn`
  - `profileSelect`
  - `profileTips`
  - `documentNoConfirmArea`
  - `confirmForm`
  - `descriptionConfirmArea`
  - `imageUploadArea`
  - `generateBtn`
  - `downloadExcelBtn`
  - `submitResult`
  - `layoutDirtyStatus`
- UI 小修应优先只改 HTML/CSS，避免碰业务函数。
- 移动 DOM 时必须确认依赖 id 的 JS 仍能找到元素。
- 不要把右侧独立滚动改坏。
- 不要把配置中心 Layout Designer 的保存状态和 dirty 状态逻辑改坏。

## 后端与业务逻辑禁区

以下场景除非明确要求，否则不要改：

- AI 解析提示词和解析结构。
- `parseMessage()` 核心流程。
- `submitOrder()` 核心流程。
- Excel 写入逻辑。
- Layout Engine 渲染逻辑。
- 图片上传后端接口。
- 图片缓存目录规则。
- 模板映射持久化结构。
- 字段库系统字段规则。
- AI 设置存储和解锁逻辑。

## 当前不建议做的事

- 暂不做 Excel 富文本红字。
- 暂不做大规模前端重构。
- 暂不做数据库重构。
- 暂不做多用户登录。
- 暂不一次性重构产品描述 AI 生成逻辑。
- 暂不把 V3 Layout Engine 重写成独立前端框架。
- 暂不把所有内联首页脚本拆模块，除非安排专项重构。
- 暂不改变现有 API 路径。

## 每次修改后的回归清单

基础回归：

- 首页能打开。
- 配置中心能打开。
- 当前模板映射能加载。
- AI解析按钮可见。
- AI解析正常返回。
- 普通字段显示和填充正常。
- 日期显示稳定。
- 文档编号显示正常。
- 文档编号默认值不被 AI 覆盖。
- 手动修改文档编号字段后，再次 AI解析不覆盖用户输入。
- 重新生成文档编号使用当前输入框内容。
- 产品描述能生成。
- 产品描述来源前缀正常。
- Excel 能生成。
- Excel 产品描述去掉来源前缀。
- Excel 模板格式尽量保持。
- 图片字段上传正常。
- 图片素材池点击上传正常。
- 图片素材池 Ctrl+V 粘贴上传正常。
- 图片素材池删除和排序正常。
- Layout Engine 保存状态正常。
- Layout Engine 保存后状态变为已保存。
- Layout 有未保存修改时状态变为未保存。
- Layout 图片块使用素材池时能参与导出。
- 下载/打开目录按钮正常。
- 同步目录逻辑正常。

UI 回归：

- 首页 body 无整体滚动条。
- 首页右侧独立滚动。
- 左侧 AI解析按钮在 1080p 可见。
- 模板选择区域在订单确认标题下方、文档编号上方。
- “选择模板映射”和“文档编号信息”标题风格一致。
- 图片素材池提示文案可见。
- 配置中心 `layoutDirtyStatus` 在 Layout 按钮右侧。

配置回归：

- 新建映射正常。
- 上传模板正常。
- 删除模板文件正常。
- 删除映射正常。
- 保存当前映射正常。
- 字段库新增、编辑、删除正常。
- 图片字段新增、启用、保存正常。
- 文档编号设置保存正常。
- 产品描述模板保存和恢复正常。
- 本地同步路径测试正常。

## 常用验证命令

语法检查：

```powershell
conda run -n ai-order-system python -m py_compile app/main.py app/routes/images.py app/routes/parse.py app/routes/templates.py
```

启动服务：

```powershell
conda run -n ai-order-system uvicorn app.main:app --reload
```

常用访问地址：

- 首页：`http://127.0.0.1:8000/`
- 配置中心：`http://127.0.0.1:8000/config`

## 维护原则

- 小修只碰小范围文件。
- 修改前先确认现有逻辑入口。
- 不要回滚用户已有改动。
- 不要为 UI 小调改后端。
- 不要新增接口来解决可复用现有接口的问题。
- 对图片、Excel、Layout、文档编号这四类功能要格外保守。
- 每次完成后记录验证方式和残余风险。
