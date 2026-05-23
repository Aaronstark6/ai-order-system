# V4 真实模板回归测试记录

## 当前测试模板

文件名：

real_template.xlsx

模板类型：

软胶囊定制品订单生产要求模板

说明：

该模板不是通用产品明细表模板，而是定制品订单生产要求模板。
因此不应使用国家、联系人、单价、交期、Logo 等通用字段作为强制 missing 判断。

## FIX102A 真实模板初测

结果：

- labels_count: 51
- table_regions_count: 9
- block_regions_count: 4
- template_structure.tables: 3
- template_structure.blocks: 2
- structured_count: 6
- table_count: 3
- block_count: 1
- needs_review_count: 2

已识别字段：

- 文档编号 → document.doc_no
- 日期 → order.order_date
- 客户名称 → customer.name
- 客户性质 → customer.type
- 数量 → order.quantity
- 负责人 → order.owner

低置信度字段：

- 产品详细要求
- 产品描述

## FIX102B 冒号标签清洗

处理内容：

支持以下格式：

- 客户名称:
- 客户名称：
- 数量:
- 数量：
- 联系人 :
- 日期 ：

结论：

冒号清洗生效。

## FIX102C 复跑真实模板

结论：

- 客户名称: → 客户名称
- 数量： → 数量

均能正确识别。

该模板中不存在的字段不应计入 missing：

- 国家
- 联系人
- 产品名称
- 规格
- 包装
- 单价
- 交期
- Logo

## FIX102D 真实模板期望集合

模板类型：

软胶囊定制品订单

期望字段：

| label | source_path | required | field_type |
|------|-------------|----------|------------|
| 文档编号 | document.doc_no | true | text |
| 日期 | order.order_date | true | text |
| 客户名称 | customer.name | true | text |
| 客户性质 | customer.type | true | text |
| 数量 | order.quantity | true | text |
| 负责人 | order.owner | true | text |
| 产品详细要求 | product.fields.产品详细要求 | false | text |
| 产品描述 | product.fields.产品描述 | false | text |

识别结果：

- expected_count: 8
- recognized_count: 8
- recognition_rate: 100%

## 表格/区块识别

识别结果：

- table_count: 3
- block_count: 2

表格摘要：

1. 产品详细要求、软胶囊、 片剂、固体饮料、软糖
2. 盖子密封方式、袋口密封、瓶口热塑封
3. 生产日期/批号、不打批号日期、瓶底打批号日期等

## 当前结论

该真实模板回归测试结果：

**PASS**

Template Analysis / Auto Mapping 对该模板可用。

## 后续建议

1. 为不同真实模板建立独立期望字段集合。
2. 不要用通用字段集合评估所有模板。
3. 后续可增加模板类型自动识别。
4. 继续测试其他类型模板，例如爆珠、固体饮料、片剂等。

---

## 测试环境与 Feature Flags 说明

本轮真实模板回归主要验证以下能力：

- scan_excel_labels
- analyze_template
- generate_auto_mapping
- Template Analysis
- Auto Mapping

这些能力通常不依赖 Excel Export Feature Flags。

当前系统存在以下 Excel 功能开关：

- image_fields
- dynamic_tables
- advanced_write_modes
- option_write_enhancement
- format_protection
- export_readback_check

注意：

本轮真实模板回归未验证完整 Excel Export 链路。

后续如果测试以下能力，必须先记录 Feature Flag 状态：

- 图片导出
- 动态表格导出
- 高级写入模式
- option 写入增强
- 格式/公式保护
- 导出结果回读检查

否则可能出现：

功能被关闭，但误判为代码异常。

后续 Export / Workspace / Executor 测试报告中，应增加：

```text
TEST ENVIRONMENT

image_fields:
dynamic_tables:
advanced_write_modes:
option_write_enhancement:
format_protection:
export_readback_check:
```
