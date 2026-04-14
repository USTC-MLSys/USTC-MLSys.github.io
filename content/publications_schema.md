# publications 格式说明（仅供参考，不会被网站直接加载）

示例（JSON 数组中的单个出版物条目）：

```json
{
  "slug": "dhellam-iccd-2025",
  "title": "Paper Title",
  "summary": "一行摘要",
  "abstract": "论文摘要文本",
  "authors": ["Author A", "Author B"],
  "venue": "Conference or Journal",
  "month": "",
  "year": 2025,
  "type": "conference",  
  "research_area": "领域",
  "tags": ["tag1", "tag2"],
  "award": "可选奖项",
  "project_slug": "对应的 project slug（若有）",
  "pdf_url": "https://...",
  "code_url": "https://...",
  "content": [
    { "type": "paragraph", "title": "Abstract", "text": "..." }
  ]
}
```

必填字段：`slug`, `title`, `authors`, `year`。
可选字段：其余均可按需填写。
