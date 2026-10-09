<div align="center">

# BlockSurvey Skills

**在你已经在用的 AI 里，创建人们愿意填完的问卷，并像专家一样给任何问卷打分。**

[English](README.md) · [中文](README.zh-CN.md)

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-9-8A2BE2.svg)](#技能目录)
[![Agent Skills standard](https://img.shields.io/badge/Agent%20Skills-SKILL.md%20standard-111111.svg)](https://agentskills.io)
[![Tests](https://github.com/BlockSurvey/blocksurvey-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/BlockSurvey/blocksurvey-skills/actions/workflows/ci.yml)
[![Built with Claude Opus](https://img.shields.io/badge/built%20with-Claude%20Opus-D97757.svg)](https://www.anthropic.com/claude)

</div>

> 完整中文翻译正在进行中（Phase 2）。下面是简要介绍和技能目录；完整说明请看 [English README](README.md)。

- ✍️ **一句话生成高转化率问卷**：筛选题与跳转逻辑、平衡的量表、能让人点"开始"的欢迎页、人口统计题放在最后，最佳实践从一开始就内置。
- 🎯 **给任何问卷打 0–100 分**：**77 项专家评分标准 + 48 项静态检查**，给出等级、能否发布的结论、显示受访者会在哪里流失的漏斗视图，以及按优先级排列、每条都附修改建议的问题清单。
- 🔑 **不需要 API Key**：全部在你自己的 LLM 里运行（Claude Code、Codex、Cursor、Gemini CLI、ChatGPT）。分数由无依赖的 Python 脚本计算，你的数据不会被发送到任何地方。

适用于任何问卷工具：Google Forms、Typeform、SurveyMonkey、Qualtrics、Microsoft Forms、纸质问卷、BlockSurvey，或者你直接粘贴的一组题目。

## 30 秒安装

```bash
npx skills add BlockSurvey/blocksurvey-skills
```

只装一个：`npx skills add BlockSurvey/blocksurvey-skills --skill survey-score`。手动安装：把 `skills/*` 复制到 `~/.claude/skills/`（Claude Code）、`~/.codex/skills/`（Codex CLI）、`.cursor/skills/`（Cursor）或 `~/.gemini/skills/`（Gemini CLI）。

ChatGPT / Claude.ai（没有文件系统）：把 [`prompts/<skill>.md`](prompts/) 上传到 Project 或自定义 GPT。

安装后直接用自然语言提问即可，例如："给这份问卷打分"、"帮我做一份 B2B SaaS 的流失调研问卷"、"修复我的问卷"。

## 技能目录

<!-- catalog:start -->
**9 个技能**，分为 4 类。每个技能是一个含 `SKILL.md` 的文件夹。

### ✍️ 创建 Create (2)

_Start from a brief or a proven template._

| 技能 Skill | 功能 What it does | 试着说 Try saying |
| --- | --- | --- |
| [**survey-create**](skills/survey-create/SKILL.md) | Creates a complete, high-conversion survey from a one-line brief. | “Create a churn survey for a B2B SaaS that cancelled in the last 30 days.” |
| [**survey-templates**](skills/survey-templates/SKILL.md) | A library of 12 ready-to-use, pre-validated survey templates. | “Give me an NPS survey template for Acme Projects that closes on 30 November.” |

### ✅ 验证 Validate (2)

_Know if it is ready before anyone sees it._

| 技能 Skill | 功能 What it does | 试着说 Try saying |
| --- | --- | --- |
| [**survey-score**](skills/survey-score/SKILL.md) | Score any survey, questionnaire or form 0-100 against a professional 77-item rubric plus 48 static checks, and get a grade, a publish verdict, a funnel view of… | “Score this survey and tell me what to fix first.” |
| [**survey-lint**](skills/survey-lint/SKILL.md) | Fast, deterministic survey lint with no AI judgement. | “Lint survey.json and fail CI on any blocker or high finding.” |

### 🔧 改进 Improve (3)

_Fix the problems, route the right people, test it on simulated respondents._

| 技能 Skill | 功能 What it does | 试着说 Try saying |
| --- | --- | --- |
| [**survey-fix**](skills/survey-fix/SKILL.md) | Applies the fixes from a survey score report or lint run to the survey itself and returns a patched survey, a before-and-after changes table, the decisions… | “Fix my survey using the score report.” |
| [**survey-logic**](skills/survey-logic/SKILL.md) | Designs and checks survey routing. | “Only show the follow-up to detractors and screen out non-customers.” |
| [**survey-pretest**](skills/survey-pretest/SKILL.md) | Runs a synthetic cognitive pretest of a survey before launch. | “Pretest this questionnaire with simulated respondents. Where will people drop off?” |

### 🚀 发布 Ship (2)

_Get people to start it, then get it into your survey tool._

| 技能 Skill | 功能 What it does | 试着说 Try saying |
| --- | --- | --- |
| [**survey-copy**](skills/survey-copy/SKILL.md) | Writes the conversion copy around a survey so more people start and finish it. | “Write the welcome screen, invite email and two reminders for this survey.” |
| [**survey-export**](skills/survey-export/SKILL.md) | Exports a survey into formats any survey tool can take. | “Export this survey so I can paste it into Google Forms.” |
<!-- catalog:end -->

## 评分原理

LLM 负责判断（一次性完成 77 项评分标准的判断），代码负责计算：`survey_lint.py` 运行 48 项静态检查，`survey_score_calc.py` 算出分数、等级、结论、七个维度得分和漏斗视图。不调用任何 API，同样的判断结果总会得到同样的分数。详见 [English README](README.md#how-the-score-works)。

---

<div align="center">

由 [BlockSurvey](https://blocksurvey.io) 团队打造 · 移植自 BlockSurvey 产品内的 Survey Score · Built with Claude Opus · [MIT](LICENSE)

</div>
