# 数学建模全流程编排系统

一套面向数学建模竞赛的 AI 编排技能包：从赛题解析、建模计划、代码实现与验证，到论文写作、
综合校验、排版定稿，六个阶段串成一条可暂停、可恢复的流水线。

核心主张：**方案是跑出来的，不是设计出来的；数据是锁定后再写，不是写完再对。**

## 解决什么问题

常见的工作方式是计划和代码两段分离：方案写完直接开写代码，代码跑不通回头改方案，
改完数据又对不上，写论文时还在补窟窿。

本系统把 S2（建模计划）和 S3（代码）改成循环——计划驱动代码，代码运行结果反向修正计划，
迭代到结果通过验证、数据锁定，之后才进入论文写作。论文只引用锁定后的数据，不再返工。

## 核心机制

**S2 ↔ S3 循环**：验证不通过就回炉，小问题改代码、大问题回 S2 改计划，直到循环收敛。

**细粒度暂停点**：S3 的每个问题按五个节点硬暂停——写代码、运行前检查、小数据运行、
全量运行、结果检查，每一步都能介入。全自动场景切到 auto 模式（AI 自决策、无暂停，
决策留日志备查）。

**模型验证**：全量结果出来后再做一轮正式精检——四检（量纲边界、结果量级、参数稳定性、
敏感性），核心数字可回溯，外加误差、对比、情景三项检验。

**AI 痕迹治理**：论文写作阶段内置五层防线，调用 stop-slop、humanizer-zh 等工具检测改写，
控制成稿的 AI 腔调。

## 六个阶段

| 阶段 | 名称 | 做什么 |
| --- | --- | --- |
| S1 | 题目理解与初稿方案 | 读题、调研、初稿方案、创新点设计 |
| S2 | 建模计划 | 公式草案、伪代码、数据流图、验收标准 |
| S3 | 代码编程及检验 | 数据清洗、代码实现、运行验证、模型验证 |
| S4 | 论文写作 | 基于锁定数据写作，AI 痕迹治理 |
| S5 | 综合校验 | 五重质检：数据逻辑、CUMCM 标准、AIGC 治理 |
| S6 | 组装与定稿 | 排版、生成 docx、打包支撑材料 |

最终产出：论文 docx + 支撑材料（源代码、数据、图表、AI 工具使用记录）。

## 目录结构

```
orchestrating-math-modeling/
├── SKILL.md          技能骨架：核心理念、六阶段总览、执行模式
├── references/       阶段编排与通用规范（14 个模块文件）
└── scripts/          检查、验证、排版、打包工具（11 个脚本）
```

`references/` 按需加载：启动只读 3 个文件（`SKILL.md`、`索引导航.md`、`产物规范.md`），
其余模块用到哪读到哪，避免预载占满上下文。

## 安装与使用

把 `orchestrating-math-modeling/` 整个目录放进所用 AI 工具的 skills 目录：

- Trae：`~/.trae-cn/skills/`
- Claude Code 等：放入对应的 skills 目录

之后在对话里提到「数学建模」「CUMCM」「生成论文」等即可触发。默认每步暂停、等你确认；
说「全自动」则切到 auto 模式。

## 配套技能

编排过程会按需调用以下技能，需自行准备（与本包分离）：

核心编排：context-memory-keeper、problem-doc-model-selector、brainstorming、
modeling-paper-rubric-and-model-selector、authoritative-data-harvester、
model-code-and-result-generator、data-cleaning-and-visualization、scipilot-figure-skill、
nature-figure、paper-formal-writer、paper-micro-unit-generator、chinese-thesis-workbench、
quality-assurance-auditor、math-modeling-paper-review、paper-workflow-orchestrator、skill-creator

AI 痕迹消隐：stop-slop、humanizer-zh、shuorenhua、ai-flavor-remover

缺配套技能也能跑，会切换到轻量降级模式。

## 成果展示

[docs/成果展示.pdf](docs/成果展示.pdf)——完整跑一遍流程产出的论文成果。

## 已知说明

论文排版脚本（`generate_cumcm_docx.py`）输出的 docx 在不同 Office 环境下可能有细节差异，
遇到时手动微调即可。

## 许可证

[MIT](LICENSE)