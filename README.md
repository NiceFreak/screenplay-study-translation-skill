# Screenplay Study Translation Skill

把英文电影 / 剧集的剧本 PDF，做成**结构可审计、便于阅读和人工审校的中文剧本学习版**（HTML + EPUB）。它结合可选的中文字幕，在保留剧本原有结构（场景标题、动作描述、角色、对白、格式标记）的前提下完成翻译。

在整个过程中，AI 同时扮演资深影视剧本译者和文档工程师；你只需要提供输入、确认第一批的风格与格式、并验收成品，而不必逐行盯着翻译质量。

> **它不绑定某一个平台。** 这是一个遵循通用 **Agent Skill / `AGENTS.md`** 约定的技能，可以在 **Claude Code**、**OpenAI Codex** 等支持该约定的 AI 编程助手里安装使用。下文「Use The Skill」一节的示例以 Codex 语法（`$skill`）书写，换成其它助手时把调用方式替换成对应写法即可，工作流程完全一致。

## 它不只是「一个技能」

「技能」只是它的入口。仓库里真正沉淀下来的，是一整套**把剧本翻译当作软件工程来做**的方法和工具——即使完全不经过 AI 助手、纯手动运行脚本，它也是一条可复现的剧本翻译工具链：

- **一条可审计的流水线**：PDF 抽取 → 标记扫描 → 分批翻译 → 逐批校验 → 生成 HTML/EPUB → 终审。每一步都有脚本和检查，而不是把整本剧本丢给模型黑箱产出。
- **明确的 AI 行为契约**（`AI_AGENT_CONTRACT.md`）：规定批次边界、停止条件和人工复核点，防止模型擅自跑飞或跳过验证。
- **静态流程规范**（`AI_AGENT_PROJECT_SPEC.md`）：固定每个阶段产出的文件和数据结构。
- **二十多个 Python 脚本**：抽取、扫描、打包上下文、校验、构建、合并、审计、成本估算等，主体只依赖标准库。
- **领域知识库**（`references/`）：行业剧本格式惯例、术语表、校验规则、排障与设计决策。
- **合成 fixture + 回归测试 + CI**：全部用不含版权的合成数据，保证流程可复现、可回归。

## Scope

适合：英文电影 / 剧集剧本 PDF，最好仍能看出场景标题、动作描述、角色名和对白结构。可以搭配中文字幕，也可以只用剧本 PDF。

不适合：OCR 识别很差的扫描件、整理过度的粉丝文本、小说化改写文本，或已经看不出剧本结构的文档。当前默认交付物是 HTML 和 EPUB。

## Install / Update

在 Codex 中安装远程仓库：

```text
Use $skill-installer to install https://github.com/NiceFreak/screenplay-study-translation-skill
```

也可以直接运行系统安装脚本：

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo NiceFreak/screenplay-study-translation-skill \
  --path . \
  --name screenplay-study-translation
```

本地开发时，可以把仓库当前内容同步到已安装 skill：

```bash
rsync -a --delete --exclude='.git/' ./ "${CODEX_HOME:-$HOME/.codex}/skills/screenplay-study-translation/"
```

脚本主体使用 Python 标准库；EPUB 导出需要 `requirements.txt` 中的 `ebooklib`：

```bash
python3 -m pip install -r requirements.txt
```

安装或更新后，如 Codex 没有立刻识别新 skill，请重启 Codex。

## Use The Skill

在 Codex CLI / IDE 中，可以运行 `/skills` 从列表选择 `screenplay-study-translation`，也可以在提示词里直接输入 `$screenplay-study-translation` 显式调用。普通文字里写 “使用 screenplay-study-translation skill” 通常也能触发，但发布文档和可复现流程里推荐使用 `$screenplay-study-translation`。

普通使用时，不需要手动串联所有脚本。把真实项目放在 skill 仓库外，然后在 Codex 中给出剧本 PDF、可选字幕、输出目录和中文片名即可。用户主要只需要四个动作：

### 1. 生成预览

```text
Use $screenplay-study-translation.
剧本 PDF: /path/to/screenplay.pdf
中文字幕: /path/to/subtitles.ass
中文片名: 示例影片
输出目录: /path/to/output
生成预览。
```

Codex 会新建项目，完成抽取、字幕解析、source scan、项目级术语/封面/阅读说明准备，只翻译第一批并生成 HTML 预览，然后停止等待验收。

### 2. 翻译下一批

```text
Use $screenplay-study-translation.
项目: /path/to/output/示例影片-project
翻译下一批。
```

这表示只处理下一批并停下，不会自动跑完整本。

### 3. 生成成品 HTML

```text
Use $screenplay-study-translation.
项目: /path/to/output/示例影片-project
生成成品 HTML。
```

Codex 会合并已验证批次，生成最终 `dist/screenplay-study.html` 并运行 audit。

### 4. 导出 EPUB

```text
Use $screenplay-study-translation.
项目: /path/to/output/示例影片-project
导出 EPUB。
```

Codex 会从最终 HTML 生成 `dist/screenplay-study.epub`。

如果第一批预览通过，并且用户想让 Codex 自动继续跑完剩余批次，可以使用这句授权语：

```text
预览通过，继续跑完整本。
```

这句话视为明确授权 continuous batch execution：Codex 会从下一批开始逐批翻译、验证和生成预览；只要没有 FAIL、UNCERTAIN、工具错误或范围不清，就自动运行到最终 HTML/EPUB 交付。

中文片名是新项目必填输入，用于 HTML 封面和读者可见标题；不要从文件名、字幕名或模型判断推断。高质量中文字幕强烈建议提供，但技术上可选；没有字幕时，不输出字幕标签，AI 翻译全部元素。

## Recommended Project Layout

真实翻译项目建议放在仓库外，或放在用户指定输出目录中：

```text
my-film-project/
  project.yaml
  inputs/
    screenplay.pdf
    subtitles.ass
  references/
    terminology.md
    front_matter.md
    reader_notes.md
  work/
    source-lines.json
    source-markers.json
    subtitles.json
    style-profile.json
    context/
    batches/
    logs/
    reports/
  dist/
    screenplay-study.html
    screenplay-study.epub
```

`references/terminology.md` 是项目级术语底表；`references/front_matter.md` 是封面和标题页信息的读者文本；`references/reader_notes.md` 是阅读说明和本剧本出现的专业术语说明。这些 artifact 应在正式翻译前建立，后续批次复用，避免 renderer 或 agent 每批重新推断。

## Workflow

1. Intake：收集 screenplay PDF、用户提供的中文片名、可选字幕、输出目录和页码映射预期。
2. Extraction：用 `scripts/extract_pdf.py` 抽取 `work/source-lines.json`；如有字幕，用 `scripts/parse_subtitles.py` 生成 `work/subtitles.json`。
3. Source scan：用 `scripts/scan_markers.py` 生成 `work/source-markers.json`，再用 `scripts/validate_sample.py` 做首轮结构验证。
4. Setup artifacts：确认 Stage 2 后，建立项目级 terminology、front matter、reader notes 和 `work/style-profile.json`；这些是后续批次的稳定上下文。
5. Batch translation：默认 5-10 页一批。先用 `scripts/draft_batch.py` 建当前批次草稿，再用 `scripts/package_batch_context.py` 打包当前页范围所需上下文，翻译后写入 `work/batches/translated-pXXX-YYY.json`。
6. Batch validation and preview：每批运行 `scripts/validate_batch.py --final`，用 `scripts/build_html.py` 生成局部 HTML 预览。第一批用于确认整体风格与格式；通过后，用户可显式授权连续批次运行，或只说“翻译下一批”来单批推进。
7. Finalization：所有批次验证通过后，用 `scripts/merge_batches.py` 合并，用 `scripts/finalize_html.py` 生成 `dist/screenplay-study.html` 并运行 audit，再用 `scripts/export_epub.py` 生成 `dist/screenplay-study.epub`。

运行控制以 `AI_AGENT_CONTRACT.md` 为准：每批都是独立验证单元；只有用户明确授权 continuous batch execution，Codex 才能在 PASS 后自动进入下一批；遇到 FAIL、UNCERTAIN、工具错误或范围不清必须停止。

## Human Review Model

用户不需要逐行复核翻译质量。推荐的审查点只有两个：第一批 HTML 用来确认整体风格、格式还原、阅读体验和术语口径；最终 HTML 用来做成品验收。中间批次由 AI 译者以最终质量意图翻译并自行验证，除非校验返回 FAIL/UNCERTAIN 或出现高影响歧义才需要人工介入。

## What It Handles

- 完整翻译 screenplay 文档：对白、动作、场景标题、角色提示、括号说明、转场、画外音、格式标记和银幕文字。
- 使用 `.ass`、`.srt`、`.vtt` 中文字幕校准对白与风格；没有字幕时，AI 翻译全部元素。
- 生成适合阅读和审校的 HTML，并导出适合移动端阅读的 EPUB：封面、阅读说明、专业术语、场景导航、源页码、阅读进度和中文 reflow。
- 保留结构审计能力：batch JSON、source markers、HTML marker attributes、batch validation 和 final audit。

## Manual Commands

初始化项目：

```bash
python3 scripts/init_project.py my-film-project --title "Example Film" --chinese-title "示例影片"
```

抽取 PDF、解析字幕、扫描 source markers、验证样本：

```bash
python3 scripts/extract_pdf.py my-film-project/project.yaml
python3 scripts/parse_subtitles.py my-film-project/inputs/subtitles.ass --output my-film-project/work/subtitles.json
python3 scripts/scan_markers.py my-film-project/project.yaml
python3 scripts/validate_sample.py my-film-project/project.yaml
```

确认 Stage 2、创建当前批次草稿、生成低成本 batch context：

```bash
python3 scripts/confirm_stage2.py my-film-project/project.yaml
python3 scripts/plan_batches.py my-film-project/project.yaml
python3 scripts/draft_batch.py my-film-project/project.yaml --display-page-start 1 --display-page-end 5
python3 scripts/package_batch_context.py my-film-project/project.yaml --display-page-start 1 --display-page-end 5
```

验证 batch、生成预览 HTML、审计页面范围：

```bash
python3 scripts/validate_batch.py my-film-project/work/batches/translated-p001-005.json --final
python3 scripts/build_html.py my-film-project/work/batches/translated-p001-005.json --output my-film-project/dist/preview-p001-005.html --project my-film-project/project.yaml
python3 scripts/audit.py my-film-project/project.yaml --html my-film-project/dist/preview-p001-005.html --display-page-start 1 --display-page-end 5
```

合并并生成最终 HTML/EPUB：

```bash
python3 scripts/merge_batches.py --batch-dir my-film-project/work/batches --output my-film-project/work/batches/translated-pXXX-YYY.json
python3 scripts/finalize_html.py my-film-project/project.yaml my-film-project/work/batches/translated-p001-126.json
python3 scripts/export_epub.py my-film-project/project.yaml
```

`finalize_html.py` 会在最终 HTML 审计通过后自动导出 `work/reports/cost-report.json`，其中包含项目级 token 和美元成本估算。该报告基于本地 batch context 和译文 artifact，不是 API 账单。

## Repository Map

```text
SKILL.md                    # 翻译、提取和输出原则（技能入口）
AI_AGENT_CONTRACT.md        # AI 运行时边界和批次控制规则
AI_AGENT_PROJECT_SPEC.md    # 静态 pipeline 和 artifact 描述
AGENTS.md                   # 通用 agent 启动引导（Claude Code、Codex 等）
agents/openai.yaml          # Codex 平台的 UI 元数据
assets/                     # 示例配置和合成 fixture
references/                 # 工作流、术语、校验、行业惯例、排障和设计决策
scripts/                    # 抽取、扫描、打包、校验、构建、合并和审计脚本
```

本仓库只存放技能本体、脚本、规则和合成 fixture。请不要提交真实剧本 PDF、字幕文件，或生成的真实项目 `work/`、`dist/` 成果。

## Development Checks

```bash
python3 scripts/smoke.py
python3 -m compileall scripts
ruff check scripts
ruff format --check scripts
```

`scripts/smoke.py` 是主要回归检查，覆盖 extraction、marker scan、subtitle parsing、batch planning、context/cost reports、batch validation、HTML build、reflow、front matter、reader notes、scene-number/no-scene-number rendering、merge/finalize 和 audit。

## Non-goals

- 不跳过结构验证、批次验证和最终审计来做黑箱交付。
- 不处理 OCR / 破碎文本重建。
- 不处理非官方整理、粉丝版本或文学化改写文本。
- 不提供通用翻译系统。
- 不保证支持没有 screenplay 结构的输入。
