# 快速上手示例：《潮汐记录员》

这是一个**端到端可复现的最小示例**，用一段**原创合成剧本**走完整条流水线，最后产出一份中文剧本学习版 `dist/screenplay-study.html` 和 `dist/screenplay-study.epub`。

示例里的剧本内容全部是为演示而虚构的，不含任何真实电影、剧本或字幕文本。它的作用是让你在没有版权素材的情况下，先看清楚这套工具到底产出什么、每一步在做什么。

> 真实项目请放在仓库之外，并提供你自己的剧本 PDF 和中文片名。这里只是演示。

## 文件说明

| 文件 | 作用 |
|------|------|
| `make_demo_pdf.py` | 生成一份合成剧本 PDF（含场号、CONT'D、OMITTED、(MORE)、V.O. 等标记），文本算子格式与扫描器兼容。 |
| `project.yaml` | 示例项目配置：中文片名「潮汐记录员」、页码映射、输出路径。 |
| `translated-p001-002.json` | **已经翻译好的批次**。正常流程里这一步由 AI 译者完成；这里直接提供，方便你跳过翻译、直接构建成品。 |

运行后会额外生成 `source/`、`work/`、`dist/` 三个目录，它们都不纳入版本管理。

## 一步步运行

所有命令都在本目录（`examples/tide-clerk/`）下执行：

```bash
cd examples/tide-clerk
SK=../../scripts

# 1. 生成合成剧本 PDF
python3 make_demo_pdf.py source/tide-clerk.pdf

# 2. 扫描源标记 + 抽取文本行（终审需要这些数据来核对）
python3 "$SK/scan_markers.py" project.yaml
python3 "$SK/extract_pdf.py" project.yaml

# 3. 首轮结构校验 + 确认 Stage 2 信号
python3 "$SK/validate_sample.py" project.yaml
python3 "$SK/confirm_stage2.py" project.yaml --note "demo: 3 个场号对、CONT'D、V.O.、OMITTED、(MORE)"

# 4. 放入已翻译好的批次（真实项目中这一步是 AI 翻译产出）
mkdir -p work/batches
cp translated-p001-002.json work/batches/

# 5. 终审校验 + 构建最终 HTML（会自动运行 audit 比对标记数）
python3 "$SK/validate_batch.py" work/batches/translated-p001-002.json --final
python3 "$SK/finalize_html.py" project.yaml work/batches/translated-p001-002.json \
  --display-page-start 1 --display-page-end 2

# 6. 导出 EPUB
python3 "$SK/export_epub.py" project.yaml
```

EPUB 导出需要 `ebooklib`（见仓库根目录 `requirements.txt`）：

```bash
python3 -m pip install -r ../../requirements.txt
```

## 你会得到什么

`finalize_html.py` 通过审计后，`dist/screenplay-study.html` 里包含：

- 封面（中文片名 + 翻译后的标题页信息）
- 阅读说明（标注下划线 / 加粗 / 斜体的用途）
- 可折叠的场次索引（链接到对应场景）
- 按原剧本页码排版的中英对照正文
- 边栏场号、删场（OMITTED）和接下页（MORE）等格式标记
- 浏览器本地的阅读进度记忆

终审日志会确认源标记和 HTML 标记数量完全一致，例如：

```
marker_count.scene_no          source=6 html=6
marker_count.contd             source=1 html=1
marker_count.more              source=1 html=1
marker_count.omitted           source=1 html=1
marker_count.voice_or_position source=1 html=1
html.internal_links            checked=2
```

## 想换成你自己的剧本？

把第 1 步换成你真实的剧本 PDF，并在 `project.yaml` 里填上你的中文片名，然后按仓库根目录 `README.md` 的「Use The Skill」用 AI 助手驱动翻译即可——第 4 步的批次会由 AI 译者生成，而不是这里预先提供的演示文件。
