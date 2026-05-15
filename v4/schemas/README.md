# V4 Product Schema

V3 Stable 是当前生产版，继续承载现有订单解析、Excel 生成、图片素材池、Layout Engine 和配置中心流程。

V4 Dev 是实验线，用于逐步沉淀新的产品结构模型。本目录只定义结构模型配置，不会影响 V3 功能，也不会被现有业务流程自动加载。

当前 `product_schema.json` 的目标是描述：

- 产品形式结构化
- 勾选项
- 产品参数
- 包装参数
- 图片参数
- 未来 Word/PDF/Excel 多渲染器

后续可在独立迭代中逐步接入 UI、AI 解析和 Excel 渲染器。在正式接入前，V4 schema 仅作为实验配置与设计基线。
