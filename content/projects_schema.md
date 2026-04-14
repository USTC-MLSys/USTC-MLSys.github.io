# projects 格式说明（仅供参考，不会被网站直接加载）

示例（JSON 对象数组中的单个项目）：

```json
{
  "slug": "twist",
  "title": "Project Title",
  "summary": "一句话简介",
  "description": "更详细的描述（可选）",
  "tags": ["systems", "ml"],
  "thumbnail": "assets/img/projects/twist-thumb.png",
  "links": {
    "github": "https://github.com/...",
    "demo": "https://..."
  },
  "content": [
    { "type": "paragraph", "title": "Overview", "text": "..." },
    { "type": "image", "src": "projects/twist/figure.svg", "alt": "..." }
  ]
}
```

必填字段：`slug`, `title`, `summary`。
可选字段：`description`, `tags`, `thumbnail`, `links`, `content`（content 按 `blog` 页面块格式）。
