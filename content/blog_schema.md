# blog 格式说明（仅供参考，不会被网站直接加载）

示例（JSON 数组中的单个博文/页面）：

```json
{
  "slug": "twist",
  "title": "TWIST",
  "subtitle": "可选的副标题",
  "summary": "一行摘要",
  "description": "页面描述",
  "status": "published",  
  "date": "2025-04-10",
  "tags": ["topic1", "topic2"],
  "author": "作者名",
  "content": [
    { "type": "paragraph", "title": "Intro", "text": "..." },
    { "type": "list", "title": "Items", "items": ["a","b"] },
    { "type": "image", "src": "blog/TWIST/image.png", "alt": "..." }
  ]
}
```

注意：`content` 内的 `type` 支持 `paragraph`, `list`, `image`, `html`, `quote` 等，详见现有 `blog.json` 示例。
