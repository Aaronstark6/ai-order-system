# V4 Excel Render Rules

`excel_render_rules.json` 是 V4 Excel Renderer 原型规则配置。

- `checkbox` 用于根据结构化订单数据自动打勾。
- `text` 用于把 `description_fields` 写入指定单元格。
- 当前配置只是实验配置，不接入正式生成流程。
- V4 实验线不影响 V3 Stable。
- 后续 V4.7 Renderer 会读取这些规则并生成实验 Excel。
