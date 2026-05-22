# V4 Excel 功能状态说明

## 当前阶段

V4 Excel 主功能已完成一轮基础闭环验证。

最新验证任务：

- FIX96 Excel 主功能总验证

验证结果：

- 动态表格：PASS
- 图片导出：PASS
- 公式保护：PASS
- 多 sheet：PASS

## 已完成能力

### 1. 普通字段写入

支持将 Workspace confirmed fields 写入指定 Excel 单元格。

### 2. 图片字段

支持：

- 模板配置页设置图片字段
- Workspace 上传图片
- confirmed_cells 携带图片数据
- 导出 Excel 时插入图片

### 3. 动态表格

支持：

- products/items/order_items 等列表数据
- row_offset 多行写入
- col_offset / table_col_offset 多列写入
- Workspace 确认后保留 offset
- 后端合并 operations 时不覆盖多行

### 4. 公式保护

支持导出时跳过已有公式单元格，避免覆盖模板公式。

### 5. 多 sheet

支持 operation / confirmed item 指定 sheet。

## 当前边界

1. Excel 主功能优先完成。
2. Word / PDF / PPT 暂不进入。
3. 诊断系统暂不继续扩展。
4. 多 sheet 和公式保护已具备基础能力，但后续仍需真实业务模板回归验证。
5. 动态表格已通过最小验证，后续需要用真实业务模板继续验证。

## 后续建议

下一阶段建议：

1. 用真实外贸模板进行 end-to-end 测试。
2. 梳理模板配置页字段命名和使用说明。
3. 清理历史误提交影响，仅在必要时处理。
4. 再决定是否进入 Word / PDF / PPT 能力。

---

## Excel 配置字段速查表

### 基础字段

| 字段 | 作用 | 示例 | 场景 |
|------|------|------|------|
| target_cell | 起始单元格 | B10 | 普通写入 / 表格写入 |
| sheet_name | 指定 sheet | Sheet2 | 多 sheet |

### 动态表格字段

| 字段 | 作用 | 示例 | 场景 |
|------|------|------|------|
| row_offset | 行偏移 | 1 | 多产品、多行 |
| col_offset | 列偏移 | 2 | 横向表格 |
| table_col_offset | 配置页列偏移字段 | quantity=1 | 表格配置 |

示例：

起始：

target_cell=B10

配置：

product_name → col_offset=0
quantity → col_offset=1
spec → col_offset=2

结果：

B10 产品名
C10 数量
D10 规格

下一行：

B11
C11
D11

### 图片字段

| 字段 | 作用 | 示例 |
|------|------|------|
| type=image | 图片字段 | logo |
| target_cell | 图片锚点 | B10 |

支持：

- Workspace 上传
- confirmed_cells
- Excel 插图

### 分组字段

| 字段 | 作用 | 示例 |
|------|------|------|
| single_choice | 单选配置 | package_type |
| option_value | 单选值 | capsule |

### 数据来源

动态表格支持：

products
items
order_items
details
table_rows

示例：

```json
{
  "products":[
    {
      "product_name":"软胶囊",
      "quantity":"5000"
    }
  ]
}
```

---

## 真实业务模板使用流程

### Excel 使用流程

步骤：

1. **上传 Excel 模板**

   - 进入模板配置页面
   - 选择 Excel 文件上传

2. **配置模板字段**

   **普通字段：**

   - customer_name
   - country
   - contact_person

   **图片字段：**

   - type=image
   - target_cell

   **动态表格字段：**

   - target_cell
   - table_col_offset

3. **Workspace 确认**

   支持：

   - 普通字段确认
   - 图片上传
   - 动态表格确认

4. **导出 Excel**

   - 点击导出按钮
   - 系统读取配置和 confirmed fields
   - 执行写入操作

5. **下载结果文件**

   - 生成新的 Excel 文件
   - 保留模板格式和公式
   - 下载到本地

---

## 动态表格配置示例

### 场景描述

模板：

| B10 | C10 | D10 |
|-----|-----|-----|
| 产品名 | 数量 | 规格 |

### 配置步骤

1. **product_name 字段**

   - target_cell=B10
   - col_offset=0

2. **quantity 字段**

   - target_cell=B10
   - col_offset=1

3. **spec 字段**

   - target_cell=B10
   - col_offset=2

### AI 输出数据

```json
{
  "products":[
    {
      "product_name":"软胶囊",
      "quantity":"5000",
      "spec":"500mg"
    },
    {
      "product_name":"爆珠",
      "quantity":"8000",
      "spec":"300mg"
    }
  ]
}
```

### 最终结果

| B10 | C10 | D10 |
|-----|-----|-----|
| 软胶囊 | 5000 | 500mg |
| B11 | C11 | D11 |
| 爆珠 | 8000 | 300mg |

---

## 图片字段配置示例

### 场景描述

需要在 Excel 模板的 B5 位置插入公司 logo。

### 配置步骤

1. **字段设置**

   - 字段名：logo
   - type=image
   - target_cell=B5

2. **Workspace 操作**

   - 进入 Workspace 页面
   - 上传图片文件
   - 确认图片字段

3. **导出流程**

   - confirmed_cells 携带图片数据
   - Excel 导出时自动插图

---

## 多 Sheet 配置示例

### 场景描述

模板包含多个 sheet，需要分别写入不同位置。

### 配置示例

**Sheet1 配置：**

- target_cell=B10
- sheet_name=Sheet1（默认）

**Sheet2 配置：**

- target_cell=C20
- sheet_name=Sheet2

### 结果

- Sheet1 的 B10 单元格写入数据
- Sheet2 的 C20 单元格写入数据

---

## 公式保护说明

### 场景描述

模板包含计算公式，需要在导出时保留。

### 示例

**模板已有公式：**

```
=SUM(C10:D10)
```

位于 B10 单元格。

### 导出行为

- 保持公式不变
- 不覆盖已有公式
- 公式计算结果正常显示

### 实现原理

系统检测到目标单元格包含公式时，跳过写入操作，保留原公式。

---

## 当前能力边界

### 当前已支持

- [x] 普通字段写入
- [x] 图片字段导出
- [x] 动态表格写入
- [x] 公式保护
- [x] 多 sheet 支持

### 当前暂不进入

- [ ] Word 文档
- [ ] PDF 导出
- [ ] PPT 演示文稿
- [ ] 高级诊断系统

### 待验证能力

以下能力已具备基础实现，后续仍需真实业务模板回归验证：

- 多 sheet 协作写入
- 公式保护稳定性
- 动态表格复杂场景

---

## 下一阶段路线

### 近期任务

1. **真实业务模板回归测试**
   - 收集实际外贸模板
   - 覆盖常见字段类型
   - 验证完整导出流程

2. **配置页体验整理**
   - 梳理字段命名规范
   - 优化用户交互
   - 完善使用说明

3. **真实外贸流程 end-to-end 测试**
   - 从模板上传到结果下载
   - 验证完整数据流
   - 收集使用反馈

### 中期评估

完成以上验证后，再决定是否进入：

- Word 文档支持
- PDF 导出能力
- PPT 演示文稿
