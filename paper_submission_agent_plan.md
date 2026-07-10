# 实验室论文展示自动化方案

## 目标

本方案的目标是：

- 不改当前网站论文展示风格
- 继续沿用现有论文卡片页和论文详情页渲染逻辑
- 只新增一套“提交新论文 -> 自动补全 -> 审核 -> 发布”的后台流程

最终效果是：实验室同学在论文 `accepted` 后，提交一份 PDF 和少量必要信息，系统自动生成与当前网站一致的论文展示条目，审核后发布到网站。

当前展示代码继续沿用：

- `content/publications.json`
- `labsite/render.py`

## 当前论文页实际展示内容

根据当前代码排查，论文展示分为两部分：

### 1. 论文卡片页展示

卡片页当前会展示：

- `venue`
- `month/year`
- `title`
- `authors`
- `summary`
- `tags`
- `pdf_url`
- `code_url`
- `award`

### 2. 论文详情页展示

详情页当前会展示：

- `title`
- `abstract`
- `venue`
- `month`
- `year`
- `award`
- `tags`
- `pdf_url`
- `code_url`
- `authors`
- `research_area`
- `content`
- `project_slug` 对应的关联项目卡片

因此，如果想新增一篇 paper，并且展示效果与当前 `Mantle` 一致，必须保证生成的数据字段与现有 `publications.json` 格式兼容。

## 字段设计

### 1. 页面真正依赖的核心字段

必需字段：

- `slug`
- `title`
- `summary`
- `abstract`
- `authors`
- `venue`
- `year`
- `research_area`
- `tags`
- `pdf_url`

强烈建议提供：

- `month`
- `type`
- `content`

可选增强字段：

- `code_url`
- `award`
- `project_slug`

## 字段来源划分

### 1. 自动从 PDF 解析

这些字段优先从 PDF 提取：

- `title`
- `authors`
- `abstract`

### 2. agent 自动生成或推断

这些字段可由系统自动补全：

- `slug`
- `summary`
- `type`
- `tags`
- `content`

### 3. 人工确认或补充

这些字段建议由提交人或管理员确认：

- `status`
- `venue`
- `month`
- `research_area`
- `project_slug`
- `code_url`
- `award`

## 第一版产品形态

第一版建议不要先做网页后台，而是做一个稳定的“提交包 + 命令行工具”。

每篇论文提交为一个目录：

```text
submission/
  paper.pdf
  meta.json
```

其中：

- `paper.pdf` 必填
- `meta.json` 提供少量人工字段

推荐的 `meta.json` 模板如下：

```json
{
  "status": "accepted",
  "venue": "SOSP 2025",
  "month": "October",
  "project_slug": "",
  "code_url": "",
  "award": "",
  "research_area": "storage systems"
}
```

## 推荐目录结构

建议在网站仓库中新增以下结构：

```text
USTC-MLSys.github.io/
  assets/
    papers/
  content/
    publications.json
    publications_pending.json
  tools/
    publication_agent/
      submit_publication.py
      review_publications.py
      publish_publication.py
      common.py
      schema.py
      templates/
        meta.template.json
```

各目录用途如下：

- `assets/papers/`：存放上传后的 PDF
- `content/publications_pending.json`：待审核论文池
- `submit_publication.py`：论文提交入口
- `review_publications.py`：查看和修正待审核条目
- `publish_publication.py`：将待审核条目正式发布

## 完整工作流

### 步骤 1：实验室同学提交论文

每位同学准备：

- `paper.pdf`
- `meta.json`

执行命令：

```bash
python tools/publication_agent/submit_publication.py --submission /path/to/submission
```

### 步骤 2：系统自动处理

`submit_publication.py` 完成以下工作：

1. 读取 PDF
2. 提取 `title/authors/abstract`
3. 生成 `slug`
4. 生成 `summary`
5. 根据标题和摘要推断 `tags`
6. 生成 `content`
7. 将 PDF 复制到 `assets/papers/<slug>.pdf`
8. 生成候选论文条目
9. 追加到 `content/publications_pending.json`

### 步骤 3：管理员审核

管理员执行：

```bash
python tools/publication_agent/review_publications.py
```

重点审核内容：

- 作者顺序是否正确
- venue 是否正确
- month/year 是否准确
- tags 是否合理
- research_area 是否合适
- 是否与现有论文重复
- PDF 链接是否正常

### 步骤 4：正式发布

确认通过后执行：

```bash
python tools/publication_agent/publish_publication.py --slug paper-slug
```

该脚本负责：

1. 从 `publications_pending.json` 中找到目标条目
2. 检查是否与正式库重复
3. 合并到 `publications.json`
4. 从 pending 中移除
5. 保持 JSON 排序和结构整洁

## 最终生成的数据格式

agent 发布前生成的标准条目建议如下：

```json
{
  "slug": "mantle-sosp-2025",
  "title": "Mantle: Efficient Hierarchical Metadata Management for Cloud Object Storage Services",
  "summary": "Mantle proposes a two-layer metadata architecture for cloud object storage, enabling scalable hierarchical namespace management.",
  "abstract": "Mantle is a new COSS metadata service for modern cloud workloads...",
  "authors": [
    "Jiahao Li",
    "Yiduo Wang",
    "Cheng Li",
    "Kang Chen"
  ],
  "venue": "SOSP 2025",
  "month": "October",
  "year": 2025,
  "type": "conference",
  "research_area": "storage systems",
  "tags": ["cloud storage", "metadata management", "distributed file systems", "object storage"],
  "award": "",
  "project_slug": "",
  "pdf_url": "/assets/papers/mantle-sosp-2025.pdf",
  "code_url": "",
  "content": [
    {
      "type": "paragraph",
      "title": "Abstract",
      "text": "Mantle is a new COSS metadata service for modern cloud workloads..."
    }
  ]
}
```

这套格式与当前网站渲染器兼容，因此不需要修改前端样式。

## PDF 存储策略

建议统一保存本地 PDF，而不是只依赖外部链接。

规则：

- 上传后复制到 `assets/papers/<slug>.pdf`
- `pdf_url` 默认写为站内路径
- 如果后续有正式外链，可以再人工替换为外部链接

优点：

- 论文刚 `accepted` 但未公开时也能先展示
- 站内链接稳定
- 不依赖外部网站路径变化

## 去重与校验机制

提交和发布阶段都建议做以下检查：

- `slug` 是否已存在
- `title` 是否与现有论文高度相似
- `authors + year` 是否疑似重复
- PDF 文件是否已存在
- 必填字段是否为空

发现冲突时：

- 不自动覆盖正式条目
- 写入 pending，并附带冲突提示
- 交给人工审核处理

## 与当前页面展示的映射关系

### 卡片页依赖字段

- `venue`
- `month/year`
- `title`
- `authors`
- `summary`
- `tags`
- `pdf_url`
- `code_url`
- `award`

### 详情页依赖字段

- `title`
- `abstract`
- `venue/month/year/award`
- `tags`
- `pdf_url`
- `code_url`
- `authors`
- `content`
- `research_area`
- `project_slug`

因此，新增系统只需要确保生成这些字段，页面风格就会自动保持与现有网站一致。

## 第一版开发顺序

推荐按以下顺序落地：

1. 新建 `content/publications_pending.json`
2. 新建 `assets/papers/`
3. 编写 `submit_publication.py`
4. 实现 PDF 提取 `title/authors/abstract`
5. 自动生成标准 JSON 条目
6. 编写 `review_publications.py`
7. 编写 `publish_publication.py`
8. 用现有一篇论文做全流程验证
9. 最后再补外部信息查询能力

## 第一版暂时不要做的功能

为了降低风险，第一版建议先不做：

- 自动全网检索论文
- 自动直接上线正式站点
- 自动改前端渲染样式
- 完全信任 PDF 元数据而不审核
- 自动覆盖已有论文条目

## 第二版可扩展能力

等第一版流程稳定后，可以继续补：

- 从 OpenReview / DBLP / arXiv 自动查询 venue/year
- 自动识别 DOI、外部 PDF、代码仓库
- 自动生成更好的 summary
- 自动推荐 tags 和 research_area
- Web 表单提交入口
- GitHub PR 自动化发布
- 实验室成员身份校验

## 实施建议总结

推荐的最小可行方案是：

- 前端展示代码完全不变
- 新增论文时只处理数据层
- 通过 `paper.pdf + meta.json` 作为提交入口
- 自动解析核心信息
- 生成候选条目进入 `publications_pending.json`
- 人工审核后再发布到 `publications.json`

这样可以在不影响现有站点风格的前提下，快速建立一套稳定、可扩展的新论文发布流程。
