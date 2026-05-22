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
