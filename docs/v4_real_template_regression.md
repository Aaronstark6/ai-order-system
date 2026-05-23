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

---

# FIX103A 第二真实模板回归

模板：

软胶囊_软胶囊爆珠模板

模板类型：

软胶囊爆珠模板

验证结果：

labels_count: 15
structured_count: 6
table_count: 0
block_count: 0
needs_review_count: 2

已识别字段：

- 文档编号 → document.doc_no
- 日期 → order.order_date
- 客户名称 → customer.name
- 客户性质 → customer.type
- 数量 → order.quantity
- 负责人 → order.owner

低置信度字段：

- 备货单号--产品代号
- 产品描述

missing_fields:

无。

识别率：

100%

## 与第一真实模板对比

| 模板 | 类型 | structured | tables | blocks |
|------|------|------|------|------|
| real_template.xlsx | 定制品订单 | 6 | 3 | 2 |
| 软胶囊爆珠模板 | 爆珠模板 | 6 | 0 | 0 |

结论：

Template Analysis / Auto Mapping 已验证至少两种真实模板。

当前状态：

**PASS**

---

# FIX104A 真实模板完整 Export 回归

## 测试目标

验证真实模板从配置到 Excel 导出的完整链路：

真实模板
→ profile 配置
→ confirmed_cells
→ operations merge
→ Excel Export
→ 输出文件单元格校验

## 测试环境

Feature Flags 当前状态：

```text
excel_feature_flags = {}
```

## 测试模板

文件名：real_template.xlsx

模板类型：软胶囊定制品订单生产要求模板

## 测试字段

| label | source_path | sheet | row | col |
|-------|-------------|-------|-----|-----|
| 文档编号 | document.doc_no | Sheet1 | 2 | 2 |
| 日期 | order.order_date | Sheet1 | 3 | 2 |
| 客户名称 | customer.name | Sheet1 | 4 | 2 |
| 客户性质 | customer.type | Sheet1 | 5 | 2 |
| 数量 | order.quantity | Sheet1 | 6 | 2 |
| 负责人 | order.owner | Sheet1 | 7 | 2 |

## 测试数据

```json
{
  "document": {
    "doc_no": "DOC-2024-001"
  },
  "order": {
    "order_date": "2024-03-15",
    "quantity": "10000",
    "owner": "张三"
  },
  "customer": {
    "name": "测试客户有限公司",
    "type": "VIP客户"
  }
}
```

## 测试步骤与结果

### 1. 测试场景

设置 template_file_path = "real_template.xlsx"
保存 confirmed_cells 映射

### 2. 合并操作

merge 结果：
- original_count: 6
- override_count: 6 (全部正确合并)
- processed_operations: 6 个

### 3. Excel 写入

- 成功写入 6 个单元格
- 无写入错误

### 4. 输出文件校验

| cell | expected | actual | pass |
|------|----------|--------|------|
| B3 | DOC-2024-001 | DOC-2024-001 | ✓ |
| B4 | 2024-03-15 | 2024-03-15 | ✓ |
| B5 | 测试客户有限公司 | 测试客户有限公司 | ✓ |
| B6 | VIP客户 | VIP客户 | ✓ |
| B7 | 10000 | 10000 | ✓ |
| B8 | 张三 | 张三 | ✓ |

cell_verify_pass_count: 6

## 结论

完整真实模板 Excel Export 回归测试：

**PASS**

验证链路：
✓ 真实模板扫描
✓ Profile 配置保存
✓ Confirmed Cells 映射
✓ Operations 合并 (_override_operations_with_confirmed_cells)
✓ Excel 写入 (V4ExcelExecutor)
✓ 输出文件回读校验

---

# FIX105A 真实模板动态表格写入验证

## 测试目标

验证真实模板中动态表格写入能力，重点验证 write_table_cell / row_offset / col_offset 链路。

## 测试环境

Feature Flags 当前状态：

```text
image_fields: missing
dynamic_tables: missing
advanced_write_modes: missing
option_write_enhancement: missing
format_protection: missing
export_readback_check: missing
```

## 模板信息

- 模板文件：软胶囊、爆珠模板 (c71a0eaf-51a9-45a4-bbec-834e1b3a2211.xlsx)
- Sheet 名称：软胶囊、爆珠
- 安全测试区域起点：B30

## 原始模板 B8:F12 区域

```
B8=代号：
软胶囊壳形状、大小和颜色：
填充量（内容物重量）：
包装数量和规格：1000瓶， 60粒/瓶
包装尺寸和要求：瓶子大小颜色，盖子样式颜色； 铝箔袋大小要求
干燥剂：默认英文的干燥剂
瓶口密封方式：默认铝箔片密封
是否贴标签：
谁设计制作标签：
标签材质和工艺要求：
批号日期：
批号默认是年月日， 生产日期和有效期是 日/月/年，有效期2年
瓶盖热缩膜：默认不做热缩膜
全包热缩膜：默认不做全包热缩膜
是否套防护塑料袋：默认套袋子，防划伤

配方：中文&英文
 | C8=None | D8=None | E8=None | F8=None
B9=其他要求：如条形码，彩盒，礼盒 | C9=None | D9=None | E9=None | F9=None
B10=其他可选包装：散装，三边封袋装，泡罩等 | C10=None | D10=None | E10=None | F10=None
B11=None | C11=None | D11=None | E11=None | F11=None
B12=None | C12=None | D12=None | E12=None | F12=None
```

## 测试数据

目标：写入 2 行 x 3 列 的动态表格数据

第 1 行（row_offset=0）：
- 产品：软胶囊
- 数量：5000
- 规格：500mg

第 2 行（row_offset=1）：
- 产品：爆珠
- 数量：8000
- 规格：300mg

## 测试结果

- 导出成功：True
- 写入操作数量：6
- 输出文件位置：output/v4_core_c71a0eaf-51a9-45a4-bbec-834e1b3a2211_20260523_211846.xlsx

### 单元格验证结果

| 单元格 | 预期值 | 实际值 | 状态 |
|--------|--------|--------|------|
| B30 | 软胶囊 | 软胶囊 | ✓ |
| C30 | 5000 | 5000 | ✓ |
| D30 | 500mg | 500mg | ✓ |
| B31 | 爆珠 | 爆珠 | ✓ |
| C31 | 8000 | 8000 | ✓ |
| D31 | 300mg | 300mg | ✓ |

## 结论

动态表格写入验证结果：**PASS**

验证链路：
✓ write_table_cell 操作类型支持
✓ row_offset 偏移计算正确
✓ col_offset 偏移计算正确
✓ 多行列数据正确写入
✓ confirmed=True 标志正常工作
✓ 输出文件回读校验通过
