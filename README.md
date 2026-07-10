# MLSys Lab Website

这是 USTC-MLSys 实验室官网仓库。当前仓库包含两部分能力：

1. 纯静态实验室网站
2. 论文上传与自动解析 Portal

本文档整理了当前版本的完整操作细则，方便后续维护、交接和实验室同学使用。

## 仓库结构

- `content/`
  站点内容数据源，项目、博客、论文、团队等都在这里维护
- `assets/`
  前端样式、脚本、图片、PDF 资源
- `assets/papers/`
  站内托管的论文 PDF
- `labsite/`
  静态站点生成器
- `tools/publication_agent/`
  论文上传、解析、发布 Portal 后端
- `build.py`
  生成静态网站到 `dist/`
- `preview.py`
  本地预览静态网站
- `dist/`
  构建后的静态文件

## 当前工作流概览

### 官网内容维护

- 项目：改 `content/projects.json`
- 博客：改 `content/blog.json`
- 论文：改 `content/publications.json`
- 新闻：改 `content/news.json`
- 成员：改 `content/team.json`
- 站点配置：改 `content/site.json`

### 论文上传 Portal

当前 Portal 工作流是：

1. 选择 PDF
2. 后端自动解析标题、作者、摘要、年份
3. 如果配置了 DeepSeek API，则在本地规则提取基础上做结构化增强
4. 用户确认字段
5. 点击发布
6. 后端写入 `content/publications.json`
7. 自动重建主站
8. 首页和 `Publications` 页面同步显示

## 初始化环境

在仓库根目录执行：

```bash
cd /Users/chenziqi/Desktop/website/USTC-MLSys.github.io
python3 -m venv .venv
./.venv/bin/python -m pip install markdown
```

说明：

- 主站构建依赖 `markdown`
- Portal 后端默认可直接用系统 `python3` 启动
- 如果 Portal 需要重建主站，会优先调用仓库自己的 `.venv`

## 本地启动

### 1. 启动主站

```bash
cd /Users/chenziqi/Desktop/website/USTC-MLSys.github.io
./.venv/bin/python preview.py --port 8001
```

打开：

`http://127.0.0.1:8001`

### 2. 启动论文 Portal

```bash
cd /Users/chenziqi/Desktop/website/USTC-MLSys.github.io
python3 -m tools.publication_agent.portal --port 8123
```

打开：

`http://127.0.0.1:8123`

或者在主站右上角点击 `Submit`。

### 3. 端口被占用怎么办

如果出现：

`OSError: [Errno 48] Address already in use`

可以：

```bash
lsof -i :8123
kill -9 进程号
```

或者直接换端口，比如：

```bash
python3 -m tools.publication_agent.portal --port 8124
```

## 论文上传 Portal 使用说明

### 1. 必填字段

- `PDF`
- `Status`
- `Venue`
- `Year`
- `Research area`

### 2. 选填字段

- `Month`
- `Project slug`
- `Code URL`
- `Award`
- `Title override`
- `Authors override`
- `Abstract override`
- `Tags override`

### 3. 自动回填逻辑

用户选择 PDF 后，Portal 会自动尝试回填：

- `Title override`
- `Authors override`
- `Abstract override`
- `Year`

如果配置了 DeepSeek API，还会在本地规则提取基础上做增强。

### 4. 提交后的行为

点击 `Publish to site` 后：

1. 解析结果会被整合成正式条目
2. PDF 会复制到 `assets/papers/`
3. 条目会写入 `content/publications.json`
4. 主站会自动重建
5. 成功后页面会显示：
   - `Open publication`
   - `Open homepage`

## DeepSeek 接入

### 环境变量

在启动 Portal 前配置：

```bash
export DEEPSEEK_API_KEY=your_real_key
export DEEPSEEK_BASE_URL=https://api.deepseek.com
export DEEPSEEK_MODEL=deepseek-chat
```

至少配置：

```bash
export DEEPSEEK_API_KEY=your_real_key
```

### 启动方式

```bash
cd /Users/chenziqi/Desktop/website/USTC-MLSys.github.io
export DEEPSEEK_API_KEY=your_real_key
python3 -m tools.publication_agent.portal --port 8123
```

### 安全要求

- API key 只能放在后端环境变量
- 不要写进前端 JS
- 不要提交进 Git 仓库

## 论文数据格式

Portal 最终写入 `content/publications.json` 的字段格式如下：

```json
{
  "slug": "paper-slug",
  "title": "Paper Title",
  "summary": "Short summary for cards.",
  "abstract": "Full abstract.",
  "authors": ["Author A", "Author B"],
  "venue": "ICPP 2026",
  "month": "May",
  "year": 2026,
  "type": "conference",
  "research_area": "distributed machine learning",
  "tags": ["RLHF", "distributed training"],
  "award": "",
  "project_slug": "",
  "pdf_url": "/assets/papers/paper-slug.pdf",
  "code_url": "",
  "content": [
    {
      "type": "paragraph",
      "title": "Abstract",
      "text": "Full abstract."
    }
  ]
}
```

## 首页展示规则

### Latest from the lab

首页 `Latest from the lab` 区域当前已经改成横向滑动 carousel。

规则：

- 按成果时间倒序排序
- 最新的排在最前面
- 混排：
  - publication
  - blog
  - project

说明：

- publication 排序最稳定，因为有 `year/month`
- blog 使用 `date`
- project 如果没有时间字段，会自然靠后

### Publications 页面

`Publications` 页面只读取：

- `content/publications.json`

不会读取：

- `content/publications_pending.json`

## CLI 工具

### 1. 手动创建 pending

```bash
python -m tools.publication_agent.submit_publication --submission /path/to/submission
```

### 2. 查看 legacy pending

```bash
python -m tools.publication_agent.review_publications
python -m tools.publication_agent.review_publications --slug your-paper-slug
```

### 3. 从 legacy pending 发布

```bash
python -m tools.publication_agent.publish_publication --slug your-paper-slug
```

## 当前解析能力边界

当前系统不是“任意 PDF 100% 自动正确解析”的通用论文理解器。

### 当前较稳定的内容

- title
- authors（部分规整 PDF）
- abstract
- year

### 当前不稳定的情况

- 双栏复杂排版
- 首页大图、表格、caption 干扰
- 作者行脚注符号复杂
- 非标准摘要格式
- 扫描 PDF / 图片 PDF
- 中文速读稿 / 非正式整理稿

### DeepSeek 的作用

DeepSeek 接入后主要增强：

- title
- authors
- abstract
- year
- research_area_guess
- tags_guess

但这些字段仍然建议由用户确认，不建议完全自动拍板。

## 常见问题

### 1. 选择新 PDF 后，为什么还是旧内容

这个问题已经修过。现在每次重新选文件，都会用新 PDF 的解析结果重新覆盖：

- 标题
- 作者
- 摘要
- 年份

### 2. 点击发布没反应

先看页面顶部是否出现：

- `OK: Published: ...`
- 或 `ERROR: ...`

如果失败，常见原因是主站重建依赖缺失。请确保：

```bash
./.venv/bin/python -m pip install markdown
```

### 3. 新论文为什么首页没显示

必须确认：

1. 是否已经成功发布到 `content/publications.json`
2. 是否已经自动重建主站
3. 浏览器是否已刷新

### 4. 为什么 pending 里有旧记录

Portal 现在主流程是直接发布，但 `content/publications_pending.json` 仍然保留，用于：

- legacy 流程
- 人工 review
- 调试和兼容

## 推荐维护顺序

如果你后面继续完善，建议优先级如下：

1. 增强陌生 PDF 解析能力
2. 继续完善 DeepSeek 结构化输出字段
3. 拆分 portal 页面和后端逻辑，降低 `portal.py` 复杂度
4. 为 project 增加时间字段，统一首页 latest 排序

## 当前结论

当前这套代码已经具备：

- 主站静态展示
- 首页入口
- 论文上传 Portal
- 本地解析
- DeepSeek 可选增强
- 直接发布
- 自动重建
- 首页和 Publications 页面同步显示

已经可以作为实验室内部使用的第一版系统继续迭代。
