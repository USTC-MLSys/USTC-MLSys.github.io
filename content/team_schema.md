# team 格式说明（仅供参考，不会被网站直接加载）

示例（JSON 数组中的单个成员）：

```json
{
  "name": "Cheng Li",
  "role": "Principal Investigator",
  "group": "faculty",  
  "bio": "简短个人介绍",
  "research_interests": ["parallel computing", "storage"],
  "homepage": "https://...",
  "github": "https://github.com/...",
  "email": "name@domain"
}
```

必填字段：`name`, `role`, `group`。
可选字段：`bio`, `research_interests`, `homepage`, `github`, `email`。

## 团队分类（group）说明

建议使用的 `group` 值（保持小写）：

- `faculty`：教职人员 / PI
- `postdoc`：博士后（Postdoctoral researchers）
- `phd`：博士生
- `master`：硕士生
- `engineer`：工程师 / 研究助理
- `alumni`：校友 / 前成员

说明：在现有站点代码中，`group` 字段用于分组与排序（显示顺序）。建议在新增成员时，使用以上规范值之一以保证前端渲染和排序行为一致。

示例（带有分类）：

```json
{
  "name": "Alice Example",
  "role": "Postdoctoral Researcher",
  "group": "postdoc",
  "bio": "Works on distributed systems and LLM training.",
  "research_interests": ["distributed systems", "ml"],
  "homepage": "https://...",
  "github": "https://github.com/...",
  "email": "alice@example.edu"
}
```
