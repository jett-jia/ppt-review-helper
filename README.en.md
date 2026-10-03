# PPT Review Helper

Turn a professor's slide deck into a revision sheet you can actually memorize.

Point it at a `.pptx` or `.pdf` lecture file. It strips the page numbers, footers,
repeated headers and "Thank you" slides, then sorts what is left into five
buckets — **definitions, formulas, conclusions, common mistakes, and short-answer
topics** — and writes two Markdown files: a condensed revision sheet and a mind-map
outline you can drop straight into XMind or Mubu.

Everything runs locally. Your lecture files never leave your computer.

---

## The problem it solves

Exam week is not spent memorizing, it is spent flipping pages. A chapter is eighty
slides, but maybe twenty sentences will actually be tested, scattered between
agenda slides, section dividers, decorative images and a closing "Thank you".
Reading through it takes an hour or two, and afterwards you still cannot say which
line mattered.

This tool automates the flipping. It reads each sentence's wording to decide
whether it is a definition, a formula, a caveat, or a short-answer prompt, then
groups them so you can see at a glance what the chapter actually asks you to know.

What it deliberately does **not** do: understand the subject for you, or guess what
your professor will ask. It selects and sorts. The judgement stays yours.

## Example output

Input: `demo/计算机网络_第3章_传输层.pptx` (10 slides including footers, page
numbers, a repeated header and a closing slide). Excerpt:

```markdown
## 核心定义（5 条）

- ★ 传输层是指为两台主机中的应用进程提供端到端通信服务的层次。（P3）
- ★ 端口是指传输层用来标识应用进程的 16 位编号。（P4）

## 公式（2 条）

- 吞吐量 = 窗口大小 / 往返时间 RTT（P7）

## 易错点（2 条）

- 易错点：流量控制是端到端的，拥塞控制面向整个网络，两者不要混淆。（P9）
```

The generated notes are in Chinese, because the classifier is tuned for Chinese
course material. Full samples live in `demo/sample_output/`.

## Install

Requires Python 3.10 or newer.

```bash
git clone https://github.com/jett-jia/ppt-review-helper
cd ppt-review-helper
pip install -r requirements.txt
```

Two dependencies, both pure Python — nothing to compile:

| Package | Used for |
| --- | --- |
| python-pptx | reading `.pptx` decks |
| pypdf | reading `.pdf` handouts |

## Install as an agent skill

The repository is also an agent skill (`SKILL.md` at the root). Installed into
Codex, Claude Code, or a similar tool, it fires on requests like "turn these
slides into revision notes" without you naming it.

```bash
# option 1: the skills registry (detects which AI tools you have)
npx skills add jett-jia/ppt-review-helper

# option 2: Codex's bundled skill-installer
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo jett-jia/ppt-review-helper --path . --name ppt-review-helper
```

Option 3 is manual: clone the repository and drop the whole directory into your
skills folder (`~/.codex/skills/` for Codex).

The skill is only a wrapper — the actual work is done by the Python package in
this repository, so **install the Python dependencies too**:

```bash
pip install -r requirements.txt
```

Restart your AI tool afterwards, or start a new conversation.

## Usage

```bash
# writes both the revision sheet and the mind map into output/
python -m ppt_review lecture.pptx

# choose the output directory
python -m ppt_review lecture.pdf -o my-notes

# only definitions, for terminology questions
python -m ppt_review lecture.pptx --only 名词解释
```

| Flag | Meaning |
| --- | --- |
| `input` | path to a `.pptx` or `.pdf` lecture file |
| `-o, --outdir` | output directory, defaults to `output/` |
| `--only` | restrict to one bucket: `名词解释` / `简答` / `公式` / `易错点` / `结论` / `全部` (default) |
| `--format` | `all` (default) / `review` / `mindmap` |
| `--title` | Markdown H1, defaults to the file name |
| `--stdout` | print to the terminal instead of writing files |
| `--version` | print the version number |

The `--only` values are Chinese because they map onto the five Chinese bucket
names the classifier produces.

## How it works

Four modules, each with one job, each replaceable on its own:

```
lecture file
   ↓
[ parsers.py ]   parse pptx / pdf into a uniform "page → text blocks" structure
   ↓
[ cleaner.py ]   drop page numbers, footers, repeated headers, closing slides;
                 rejoin sentences broken by the slide layout
   ↓
[ extractor.py ] classify each block into one of five buckets, mark ★ / ☆
   ↓
[ renderer.py ]  render the revision sheet and the mind-map outline
```

### How a sentence gets classified

Classification is keyword-based rather than a trained model, for a practical
reason: the rules are readable and editable. If your professor tests something
else, edit the keyword lists at the top of `extractor.py` — there is nothing to
retrain.

| Bucket | Signal | Example |
| --- | --- | --- |
| 公式 (formula) | math symbols, or an `X = Y` equality | `吞吐量 = 窗口大小 / RTT` |
| 易错点 (pitfall) | 易错 / 误区 / 常见错误 / 切忌 / 容易混淆 | `易错点：两者不要混淆` |
| 核心定义 (definition) | 是指 / 称为 / 定义为 / 是一种 | `端口是指…的 16 位编号` |
| 简答考点 (short answer) | ends with a question mark, or 简述 / 试述 / 比较 / 列举 | `简述 TCP 与 UDP 的区别。` |
| 结论 (conclusion) | 因此 / 所以 / 结论 / 可知 / 定理 / 性质 | `因此拥塞控制站在网络整体角度` |

### Where ★ and ☆ come from

Two signals, in priority order:

1. **The deck says so.** 重点 / 必考 / 考点 / 掌握 → ★; 了解 / 选学 / 补充 → ☆.
2. **Repetition.** With no explicit marker, a term appearing three or more times
   across the deck is treated as emphasised → ★.

### Known limitations

- **Scanned PDFs and image-only slides yield nothing.** They are pictures; OCR is
  required first. The tool says so explicitly instead of pretending it read them.
- **Formulas embedded as images cannot be read.** Common in real decks, and
  unsolved here.
- **Keyword classification will misfire.** A sentence like "因此…说明…" is both a
  conclusion and a short answer; the fixed priority order decides, which may not
  match your reading.
- **No OCR, no LLM calls.** Intentional, to keep lecture files on your machine and
  the dependency list at two packages. If you want semantic-level extraction, the
  structured output of `extractor.py` is a clean input for your own model.

## Demo material

```bash
# regenerate the sample decks (needs reportlab on top of the usual deps)
pip install reportlab
python demo/make_demo.py

# run it
python -m ppt_review demo/计算机网络_第3章_传输层.pptx -o demo/sample_output
```

## Contributing

Issues and pull requests are welcome. Useful directions:

- keyword rules for humanities subjects (the current set leans STEM)
- `.docx` support (one function in `parsers.py`)
- extracting text from tables

Before submitting, run the self-check. It pushes the sample decks through the
whole pipeline and asserts that cleaning and classification still work:

```bash
python tests/test_pipeline.py
```

Plain stdlib asserts — no pytest required.

## License

[MIT](LICENSE)
