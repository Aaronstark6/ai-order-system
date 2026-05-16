# V4.9 闭环演示说明

V4.9 已经跑通以下实验链路：

Example Order
→ Product Schema
→ Renderer description_fields
→ Excel Render Rules
→ Rule Preview operations
→ Rule Executor
→ 导出实验 Excel

演示入口：

http://127.0.0.1:8000/v4-schema

## 演示步骤

1. 选择示例订单：`soft_capsule_order_example`
2. 查看 Renderer 预览
3. 查看 Excel 渲染规则
4. 选择规则模板：`soft_capsule_template`
5. 点击“导出规则执行 Excel”
6. 下载生成的 Excel
7. 打开 Excel 检查：
   - A10 是否写入 ☑
   - B10 是否写入 产品要求
   - B14 是否写入 配方要求
   - B18 是否写入 包装要求

## 当前限制

- 当前是实验 Excel，不是正式 V3 订单模板
- 当前没有接入 V3 首页
- 当前没有写真实模板，只是新建调试 Excel
- 当前只验证规则执行链路

## 下一步

V4.10：
把 Rule Executor 从“新建调试 Excel”
升级为：
读取真实 Excel 模板副本，再按规则写入。
