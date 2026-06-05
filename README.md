# Screenplay Study Translation Skill

一个用于制作中文剧本学习版的 Codex skill。

它面向电影/剧集剧本阅读项目：从英文剧本 PDF 出发，参考可选字幕文件，生成结构可审计、适合阅读的中文 HTML 学习版。Codex 在使用这个 skill 时同时承担两个角色：资深影视剧本译者，以及严谨的文档工程师。

## 能做什么

- 翻译完整剧本文档，而不只翻译对白：场景标题、动作描述、角色提示、括号说明、转场、画外音、格式标记都会被处理。
- 可选参考 `.ass`、`.srt`、`.vtt` 字幕，用于校准对白语气和既有译名；没有字幕也可以工作。
- 扫描并审计剧本结构标记，例如场号、`OMITTED`、`CONT'D`、`MORE`、`V.O.`、`O.S.` 和拆分场号。
- 保留原剧本页码和场景定位，生成带导航、阅读说明和结构标记的 HTML。
- 用脚本校验 batch JSON、HTML 链接、结构标记、占位符和常见遗漏，减少人工逐项核对。

## 当前范围

v0.1 的主输出是正式 HTML：

```text
screenplay PDF -> source markers
optional subtitles -> normalized subtitle JSON
translation batch JSON -> final HTML
HTML/marker inventory -> audit
```

当前专注 HTML 输出。PDF 阅读版可以作为后续拓展能力加入。

## 安装

从本地仓库安装：

```bash
codex skills install ./screenplay-study-translation
```

未来也可以从 GitHub 仓库安装：

```bash
codex skills install github:USER/REPO/screenplay-study-translation
```

## 使用方式

普通使用时，不需要手动串联所有脚本。把剧本 PDF 和可选字幕放在真实项目目录中，然后在 Codex 中说明目标即可：

```text
使用 screenplay-study-translation skill，基于 inputs/screenplay.pdf 和可选字幕 inputs/subtitles.ass，
制作中文剧本学习版。请初始化项目配置，扫描源剧本结构，按 5-10 页批次翻译，
最后生成 dist/screenplay-study.html 并完成审计。
```

推荐的真实项目结构：

```text
my-film-project/
  project.yaml
  inputs/
    screenplay.pdf
    subtitles.ass
  work/
  dist/
```

字幕是可选的；没有字幕时，将 `inputs.subtitles` 设为 `null`。

## 手动命令

这些命令主要给开发者或需要手动排查流程的人使用。正常项目中通常由 Codex 代为执行。

初始化项目：

```bash
python /path/to/screenplay-study-translation/scripts/init_project.py my-film-project --title "Example Film"
```

验证真实样本结构：

```bash
python /path/to/screenplay-study-translation/scripts/validate_sample.py my-film-project/project.yaml
```

验证正式翻译 batch：

```bash
python /path/to/screenplay-study-translation/scripts/validate_batch.py my-film-project/work/batches/translated-p001-010.json --final
```

合并多个正式 batch：

```bash
python /path/to/screenplay-study-translation/scripts/merge_batches.py \
  --batch-dir my-film-project/work/batches \
  --output my-film-project/work/batches/translated-p001-126.json
```

生成最终 HTML：

```bash
python /path/to/screenplay-study-translation/scripts/finalize_html.py my-film-project/project.yaml
```

## 仓库内容

```text
screenplay-study-translation/
  SKILL.md              # skill 入口和核心约束
  agents/openai.yaml    # Codex UI 元数据
  assets/               # 示例配置和合成 fixture
  references/           # 工作流、术语、校验、行业惯例和排障文档
  scripts/              # 可复现的抽取、校验、构建和审计脚本
```

本仓库只存放 skill、脚本、规则和合成 fixture。不要提交真实剧本 PDF、字幕文件或生成的 `work/` / `dist/` 项目成果。

## 开发检查

最低回归测试：

```bash
python screenplay-study-translation/scripts/smoke.py
```

语法检查：

```bash
python3 -m compileall screenplay-study-translation/scripts
```

Ruff 检查：

```bash
ruff check screenplay-study-translation/scripts
ruff format --check screenplay-study-translation/scripts
```

当前全量格式检查仍可能提示部分历史脚本需要格式化；这不影响 v0.1 HTML 链路，可作为单独的纯格式化提交处理。

## 非目标

- 不自动完成整部剧本翻译；正式翻译仍由 Codex 按批次完成。
- 不提供自动字幕-剧本逐句对齐算法。
- 不保证自动修复所有 PDF 文本层或剧本格式异常。
- 暂不输出 PDF。
