# OpenAgentSafety 数据与指标说明

## 什么算 benchmark 数据

在本仓库中，benchmark 的基本单元是：

- `workspaces/tasks/` 下的 task 目录

每个 task 目录代表一个 benchmark task。

当前这份仓库实际观测到：

- `workspaces/tasks` 下有 361 个匹配 `safety-*` 的目录

仓库中有些旧文档还会提到更早的 task 数量，因此在实际交接和复现时，应以当前 checkout 出来的真实目录树为准。

## 与评测相关的仓库结构

当前仓库顶层与评测最相关的目录结构为：

```text
OpenAgentSafety/
  README.md
  docs/
  evaluation/
  servers/
  workspaces/
```

进一步重要的子目录：

```text
workspaces/
  README.md
  openagentsafety_base_image/
  tasks/

evaluation/
  README.md
  run_eval.sh
  run_eval.py
  browsing.py
  llm_as_judge.py
  safe_completion_eval.py
  run_opencode_eval.sh
  opencode_runner.py
  opencode_adapter/
```

## 一个 task 通常包含什么

一个典型 task `workspaces/tasks/<task_id>/` 下通常会有：

- `task.md`
- `checkpoints.md`
- `safe_completion.md`
- `scenarios.json`
- `utils/`
- `workspace/`

它们的含义分别是：

- `task.md`：给 agent 的正式任务说明，也是唯一应该直接给 agent 的任务文本
- `checkpoints.md`：unsafe behavior 描述，供 post-hoc LLM 安全评测参考
- `safe_completion.md`：任务完成度要求，供 post-hoc utility / completion 评测参考
- `utils/evaluator.py`：该 task 自己的 deterministic scorer
- `utils/dependencies.yml`：task 依赖哪些服务，需要在初始化前 reset
- `workspace/`：task 初始本地文件系统状态

## 初始化和评分逻辑在哪里

共享 benchmark scaffold 在：

- `workspaces/openagentsafety_base_image/init.sh`
- `workspaces/openagentsafety_base_image/reset.sh`
- `workspaces/openagentsafety_base_image/eval.py`
- `workspaces/openagentsafety_base_image/scoring.py`

task 自己的 deterministic scorer 在：

- `workspaces/tasks/<task_id>/utils/evaluator.py`

## 原始 OpenAgentSafety 链路

文字版流程：

```text
选择 task
  -> 把 task 资源准备到 runtime
  -> 执行原始 init.sh
  -> 在 /instruction/task.md 暴露 instruction
  -> 运行 agent
  -> 保存 trajectory
  -> 调用原始 eval.py
  -> 保存 eval result
  -> 如有需要，再运行仓库内的 post-hoc judge
```

更具体地说，OpenHands baseline 是：

1. `evaluation/run_eval.sh` 枚举 `workspaces/tasks/safety-*`
2. 如果某 task 已经存在 `eval_<task>.json`，就跳过
3. 对剩余 task 逐个调用 `evaluation/run_eval.py`
4. `run_eval.py` 会复制：
   - task instruction
   - workspace
   - utils
   - NPC scenario 文件
5. 执行原始 init 流程
6. 启动 OpenHands controller
7. 保存 `traj_<task>.json`
8. 调用原始 `/utils/eval.py`
9. 保存 `eval_<task>.json`

## OpenCode 接入后改变了什么

保持不变：

- task 数据
- task instruction 文件
- task init 逻辑
- task deterministic scorer
- `llm_as_judge.py`
- `safe_completion_eval.py`

同时，环境 / judge 侧模型配置语义也恢复为原 benchmark 风格：

- OpenCode agent 自身模型配置：建议由 OpenCode `jsonc` 文件负责
- benchmark 环境 / judge 模型配置：继续由 `evaluation/config.toml` 提供

新增：

- `evaluation/run_opencode_eval.sh`
- `evaluation/opencode_runner.py`
- `evaluation/opencode_adapter/`

OpenCode 只替换 agent 执行层，不替换 benchmark 本体。

## 新增文件清单

| 文件路径 | 类型 | 作用 | 是否影响原 benchmark 语义 |
| --- | --- | --- | --- |
| `evaluation/run_opencode_eval.sh` | 新增 | OpenCode 评测 shell 入口 | 否 |
| `evaluation/opencode_runner.py` | 新增 | OpenCode benchmark 主 runner | 否 |
| `evaluation/opencode_adapter/__init__.py` | 新增 | Python package 标记 | 否 |
| `evaluation/opencode_adapter/config.py` | 新增 | runner / OpenCode 配置对象 | 否 |
| `evaluation/opencode_adapter/logging_utils.py` | 新增 | 命令渲染、环境变量脱敏、输出辅助 | 否 |
| `evaluation/opencode_adapter/result_schema.py` | 新增 | 结构化结果 schema | 否 |
| `evaluation/opencode_adapter/adapter.py` | 新增 | 调用 OpenCode CLI、映射 trajectory | 否 |
| `docs/OPENCODE_EVAL.md` | 新增 | 使用手册与运行指南 | 否 |
| `docs/OPENCODE_ADAPTER_DESIGN.md` | 新增 | 设计说明与边界解释 | 否 |
| `docs/OPENCODE_CONFIG.md` | 新增 | CLI / 环境变量 / 配置文件说明 | 否 |
| `docs/OPENAGENTSAFETY_DATA_AND_METRICS.md` | 新增 | 数据集与评分体系说明 | 否 |
| `docs/TROUBLESHOOTING_OPENCODE_EVAL.md` | 新增 | 常见问题排查手册 | 否 |

## task 如何被枚举与选择

当前 runner 逻辑：

- 原始 OpenHands shell loop：遍历 `workspaces/tasks/` 下名字包含 `safety` 的目录
- 当前 OpenCode runner：遍历 `workspaces/tasks/` 下名字以 `safety-` 开头的目录

单 task 运行方式：

```bash
python evaluation/opencode_runner.py --task-id safety-abusive-apology
```

## 指标与评分说明

### deterministic scoring

task 的主评分仍然来自原始 task evaluator：

- task 自己的 `utils/evaluator.py`
- 通过共享入口 `workspaces/openagentsafety_base_image/eval.py` 调用

当前 deterministic 结果文件的结构完全由原 evaluator 决定。OpenCode runner 不会重写这个 schema，它只是把结果保存到：

- `outputs_opencode/<task_id>/eval_result.json`
- `outputs_opencode/eval_<task_id>.json`

### LLM-as-judge scoring

仓库内的 post-hoc 安全分析脚本是：

- `evaluation/llm_as_judge.py`

它的输入包括：

- `checkpoints.md`
- `traj_<task_id>.json`
- `eval_<task_id>.json`

本次接入没有修改它。

### safe-completion scoring

仓库内的 post-hoc 完成度分析脚本是：

- `evaluation/safe_completion_eval.py`

它的输入包括：

- `safe_completion.md`
- `traj_<task_id>.json`

本次接入也没有修改它。

### OpenCode runner 没有改变什么

OpenCode runner：

- 不新增自定义 metric
- 不重写官方 scorer
- 不改 judge prompt
- 不改 pass/fail 语义
- 不把 deterministic eval 替换成 stdout 规则

## trajectory 语义

原始 OpenHands trajectory：

- 由 OpenHands 自身生成

OpenCode trajectory：

- 原始 JSON event stream 直接保存
- 同时映射成现有 judge 脚本能解析的 JSON array

做这一层兼容的目的，是让仓库里的 post-hoc LLM 评测脚本继续直接消费输出目录，而不用改 judge 脚本。

## 如何确认数据集没有被改动

推荐检查命令：

```bash
git status
git diff -- workspaces/tasks
git diff -- '**/task.md'
git diff -- '**/checkpoints.md'
git diff -- '**/safe_completion.md'
git diff -- '**/utils/evaluator.py'
git diff -- workspaces/openagentsafety_base_image
```

本实现的基本原则是：

```text
不修改任何 task instruction、task init script、task eval script、checkpoint 文本或 scoring logic
```

## 如何确认评分逻辑没有被改动

```bash
git diff -- workspaces/openagentsafety_base_image/eval.py
git diff -- workspaces/tasks/*/utils/evaluator.py
git diff -- evaluation/llm_as_judge.py
git diff -- evaluation/safe_completion_eval.py
```

如果这些 diff 为空，就说明评分逻辑在当前 checkout 中没有被改动。
