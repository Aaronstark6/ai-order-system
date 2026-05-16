# V4 架构说明

## V4 定位

V4 是产品结构驱动的文档生成实验线。

V3 Stable 继续作为生产版，不被 V4 影响。V4 当前用于验证 Product Schema、Example Order、结构校验和后续渲染链路，不直接接入现有生产流程。

## V3 与 V4 区别

### V3

- 字段驱动
- 字段映射到 Excel 单元格
- 适合稳定订单生成

### V4

- 产品结构驱动
- Product Schema 描述产品
- Example Order 描述真实订单
- Validator 检查结构
- 未来 Renderer 输出 Excel/Word/PDF

## 当前 V4 模块

### `v4/schemas/product_schema.json`

- 产品结构定义

### `v4/examples/`

- 示例订单数据

### `app/v4_schema.py`

- 读取/保存 Product Schema

### `app/v4_examples.py`

- 读取/保存 Example Order

### `app/v4_validator.py`

- 校验 Example 是否符合 Schema

### `app/routes/v4.py`

- V4 只读/保存 API

### `static/v4_schema.html`

- V4 Schema 和 Example 预览/编辑页

## 当前 V4 不做什么

当前不接入：

- V3 首页
- Excel正式生成流程
- AI正式解析流程
- Windows发行版主流程

## 后续路线

### V4.4

- Example 可视化编辑完善

### V4.5

- Schema 驱动 UI 雏形

### V4.6

- Schema → description_fields 转换

### V4.7

- Schema → Excel Renderer 原型

### V5

- Word/PDF Report Engine

## 风险控制

- V4 不得破坏 V3 Stable
- V4 不得直接改现有 Excel Layout Engine
- V4 新功能必须先在 `/v4-schema` 中验证
- V4 稳定后再考虑合并到主业务流程
