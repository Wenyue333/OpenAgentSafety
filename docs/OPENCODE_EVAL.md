# OpenCode 评测使用指南

## 目的

本文档说明如何在不改变 OpenAgentSafety 原始 benchmark 语义的前提下，使用新增的 OpenCode 适配层运行评测。

保持不变的内容包括：

- benchmark task 数据
- task instruction
- task 初始化逻辑
- 官方 deterministic scorer
- 仓库内的 post-hoc LLM-as-judge 脚本
- 原始 OpenHands 入口

新增的 OpenCode 入口是：

```bash
bash evaluation/run_opencode_eval.sh
```

原始 OpenHands 入口仍然保留：

```bash
bash evaluation/run_eval.sh
```

## 环境要求

### 操作系统

推荐：

- Linux

可用但有额外注意事项：

- Windows
- macOS

原因：

- benchmark 的官方 `init.sh` 和 `eval.py` 都假定运行在 Linux 容器路径布局中
- 当前实现通过 Docker 保留这部分行为
- 但 OpenCode 当前仍然是在宿主机上针对镜像出来的 runtime 目录运行，因此非 Linux 宿主机会有 shell、路径、浏览器行为差异

### Python

仓库原始 OpenHands baseline 文档要求：

- Python 3.12+
- Poetry

本次新增的 OpenCode runner 本身只使用 Python 标准库，因此：

- 只需要可用的 `python`
- 不强依赖额外第三方 Python 包

本地实现时实际验证环境为：

- `Python 3.7.0`

因此代码已经做了向下兼容处理。

### Docker

非 `--dry-run` 模式必须安装 Docker。

原因：

- 原始 task 初始化仍需执行 `bash /utils/init.sh`
- 原始 task 评分仍需执行 `python /utils/eval.py`
- 当前实现通过 benchmark 容器保留这两段原始逻辑

### Docker Compose

如果你要完整启动 OpenAgentSafety 所依赖的服务环境，还需要：

- Docker Compose

对应文档：

- `docs/SETUP.md`
- `servers/README.md`

### 网络与外部服务

需要：

- 能访问 benchmark 服务栈
- 能访问 OpenCode 所使用的模型 API
- 如果 task 的 init/eval 本身依赖环境 LLM，也需要对应模型 API

### 浏览器与文件系统

不少 task 会涉及：

- 浏览器访问
- 文件上传/下载
- 本地工作目录读写

如果 OpenCode 在宿主机侧进行浏览器操作，那么宿主机本身也必须能访问 benchmark 服务地址。

### GPU

不需要。

### API Key / Token

可能需要两类配置：

- OpenCode agent 自身使用的模型配置
  - 推荐放在 OpenCode 的 `jsonc` 配置文件里
- benchmark 环境 / judge 使用的环境模型配置
  - 继续沿用 `evaluation/config.toml`
- 如果使用 `opencode serve` / `--attach`，还可能需要服务侧用户名和密码

不要把这些敏感信息硬编码进仓库文件。

## Python 环境准备

本仓库有 `pyproject.toml`。

推荐创建虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
```

如果你还要运行原始 OpenHands baseline，可以继续安装：

```bash
poetry install
```

仅运行本次新增的 OpenCode runner 时，不额外依赖第三方 Python 包。

## OpenCode 安装与检查

根据上游 OpenCode 文档，常见安装方式包括：

```bash
curl -fsSL https://opencode.ai/install | bash
npm i -g opencode-ai@latest
scoop install opencode
choco install opencode
```

安装后建议先检查：

```bash
opencode --version
opencode --help
opencode run --help
opencode serve --help
opencode session --help
opencode export --help
```

如果 `opencode` 未安装：

- `--dry-run` 仍然可以运行
- runner 会把探测失败结果写入 `opencode_metadata.json`
- 非 dry-run 会在真正调用 `opencode` 时失败

## OpenCode CLI 能力摘要

基于上游官方文档和源码调研，当前可以确认：

1. 推荐的非交互式入口是 `opencode run [message..]`
2. 支持 batch 模式，即直接把 prompt 作为命令行参数传入
3. 支持通过 `--dir` 指定工作目录
4. 支持通过 `--format json` 输出 JSON 事件流
5. 支持通过 `--model` 指定模型
6. 支持通过 `--agent` 指定 agent 模式
7. 支持通过 `--attach` 连接到 `opencode serve`
8. 支持 `session` / `export` 等 session 能力
9. OpenCode 的权限控制会影响 benchmark 公平性
10. `--dangerously-skip-permissions` 不应默认开启

## 两套模型配置要分清

当前 OpenCode 接入里有两套模型配置：

1. OpenCode agent 自己调用模型时使用的配置
2. OpenAgentSafety benchmark 环境 / judge 使用的环境模型配置

其中：

- OpenCode agent 配置：建议放在 OpenCode 的 `jsonc` 配置文件中
- 环境 / judge 配置：继续沿用原 benchmark 的 `evaluation/config.toml`

也就是说：

- 你不一定需要在 runner 里单独传 `--model` 或 `OPENCODE_API_KEY`
- 但你仍然需要提供 `evaluation/config.toml` 中的 `env-llm-config`，因为原始 task init、NPC 或 eval 可能依赖它

## OpenCode runner 在 benchmark 中的位置

OpenCode 路径保持以下部分不变：

- `workspaces/tasks` 中的 task 数据
- task instruction 文件
- task init 脚本
- 官方 task eval
- 仓库内 post-hoc judge 脚本

替换掉的只有 agent 执行层。

OpenCode 接收到的 runner 级 prompt 与当前 OpenHands 路径保持一致：

- `Complete the task provided in instruction/task.md`
- 如果 task 依赖 GitLab，会额外附加 GitLab 凭据提示

## 如何运行 dry-run

`--dry-run` 会检查：

- task 枚举
- runtime 目录构建
- instruction 备份
- OpenCode 命令渲染
- metadata / probe 输出

`--dry-run` 不要求：

- Docker
- OpenCode

示例：

```bash
bash evaluation/run_opencode_eval.sh \
  --opencode-bin opencode \
  --outputs-path outputs_opencode \
  --server-hostname localhost \
  --version 1.0.0 \
  --task-id safety-abusive-apology \
  --dry-run
```

等价的 Python 直接入口：

```bash
python evaluation/opencode_runner.py \
  --opencode-bin opencode \
  --outputs-path outputs_opencode \
  --server-hostname localhost \
  --version 1.0.0 \
  --task-id safety-abusive-apology \
  --dry-run
```

## 如何运行单任务 smoke test

```bash
bash evaluation/run_opencode_eval.sh \
  --opencode-bin opencode \
  --opencode-config ./opencode.jsonc \
  --env-llm-config group2 \
  --outputs-path outputs_opencode \
  --server-hostname localhost \
  --version 1.0.0 \
  --task-id safety-abusive-apology
```

推荐调试时加上：

```bash
bash evaluation/run_opencode_eval.sh \
  --opencode-bin opencode \
  --opencode-config ./opencode.jsonc \
  --env-llm-config group2 \
  --outputs-path outputs_opencode \
  --server-hostname localhost \
  --version 1.0.0 \
  --task-id safety-abusive-apology \
  --format json \
  --timeout 1800 \
  --max-iterations 50
```

## 如何运行完整 benchmark

```bash
bash evaluation/run_opencode_eval.sh \
  --opencode-bin opencode \
  --opencode-config ./opencode.jsonc \
  --env-llm-config group2 \
  --outputs-path outputs_opencode \
  --server-hostname localhost \
  --version 1.0.0
```

## 如何 resume

```bash
bash evaluation/run_opencode_eval.sh \
  --opencode-bin opencode \
  --opencode-config ./opencode.jsonc \
  --env-llm-config group2 \
  --outputs-path outputs_opencode \
  --server-hostname localhost \
  --version 1.0.0 \
  --resume
```

当前 resume 规则是：

- 如果 `outputs_opencode/<task_id>/summary.json` 已存在，则跳过该 task

## 推荐的从零运行顺序

1. 先按 `docs/SETUP.md` 启动 benchmark 服务栈
2. 确认服务可以访问
3. 安装并检查 OpenCode
4. 配置 OpenCode 的 `jsonc` 文件
5. 准备 `evaluation/config.toml`，并写好环境 / judge 模型配置
6. 先跑一次 `--dry-run`
7. 再跑一次单任务 smoke test
8. 检查：
   - `opencode_stdout.log`
   - `opencode_stderr.log`
   - `opencode_metadata.json`
   - `eval_result.json`
   - `summary.json`
9. 最后再跑完整 benchmark

## 输出目录结构

当前实现会生成：

```text
outputs_opencode/
  opencode_results.json
  traj_<task_id>.json
  eval_<task_id>.json
  <task_id>/
    instruction.txt
    init_stdout.log
    init_stderr.log
    opencode_command.json
    opencode_stdout.log
    opencode_stderr.log
    opencode_raw_output.jsonl
    opencode_metadata.json
    opencode_trajectory.json
    eval_stdout.log
    eval_stderr.log
    eval_result.json
    summary.json
    runtime/
      instruction/
      workspace/
      utils/
      npc/
```

## 每个输出文件的含义

| 文件 | 作用 |
| --- | --- |
| `instruction.txt` | 当前 task 原始 instruction 备份 |
| `init_stdout.log` | 原始 task 初始化 stdout |
| `init_stderr.log` | 原始 task 初始化 stderr |
| `opencode_command.json` | 实际调用 OpenCode 的命令和 prompt 传输方式 |
| `opencode_stdout.log` | OpenCode 标准输出 |
| `opencode_stderr.log` | OpenCode 标准错误 |
| `opencode_raw_output.jsonl` | `--format json` 时的原始 JSON 事件流 |
| `opencode_metadata.json` | OpenCode 版本/help 探测结果与脱敏后的运行元数据 |
| `opencode_trajectory.json` | 为兼容 scorer/judge 而映射出的 trajectory |
| `eval_stdout.log` | 原始 benchmark eval stdout |
| `eval_stderr.log` | 原始 benchmark eval stderr |
| `eval_result.json` | 原始 eval 产出的任务评分结果 |
| `summary.json` | 单任务 OpenCode 运行摘要 |
| `opencode_results.json` | 按 task 聚合的汇总结果 |
| `traj_<task_id>.json` | 供现有 judge 脚本使用的平铺 trajectory 文件 |
| `eval_<task_id>.json` | 供现有 judge 脚本使用的平铺 eval 结果文件 |

## 如何查看任务成功或失败

OpenCode 执行相关：

- `outputs_opencode/<task_id>/opencode_stdout.log`
- `outputs_opencode/<task_id>/opencode_stderr.log`
- `outputs_opencode/<task_id>/opencode_metadata.json`

官方评分相关：

- `outputs_opencode/<task_id>/eval_result.json`
- `outputs_opencode/<task_id>/eval_stdout.log`
- `outputs_opencode/<task_id>/eval_stderr.log`

最终状态：

- `outputs_opencode/<task_id>/summary.json`

## 如何比较 OpenHands 和 OpenCode 结果

建议直接比较以下 artifacts：

1. `traj_<task_id>.json`
2. `eval_<task_id>.json`
3. task 级别的 `summary.json`
4. 如有需要，再运行仓库原有的 post-hoc judge 脚本对两个输出目录做横向比较

## 如何确认数据集和 scorer 没被改动

检查 task 数据：

```bash
git status
git diff -- workspaces/tasks
git diff -- '**/task.md'
git diff -- '**/scenarios.json'
```

检查评分逻辑：

```bash
git diff -- workspaces/openagentsafety_base_image/eval.py
git diff -- workspaces/tasks/*/utils/evaluator.py
git diff -- evaluation/llm_as_judge.py
git diff -- evaluation/safe_completion_eval.py
```

本实现不应修改：

- task instruction
- task init script
- task evaluator
- checkpoints 文件
- safe completion 文件
- 原始 OpenHands 入口

## 重要说明：公平性与运行等价性

当前 adapter 保留了评分语义，但没有做到与原 OpenHands 运行环境完全等价：

- benchmark init 和官方 eval 仍在 Docker 中运行
- OpenCode 当前运行在宿主机上，针对镜像出来的 runtime 目录执行

因此，这套实现：

- 适合做接入验证、单任务调试和 benchmark 自动化运行
- 不能直接证明 OpenCode 与 OpenHands 的权限模型、shell 语义、浏览器语义完全等价

建议结合以下文档一起阅读：

- `docs/OPENCODE_ADAPTER_DESIGN.md`
- `docs/OPENCODE_CONFIG.md`
- `docs/OPENAGENTSAFETY_DATA_AND_METRICS.md`
- `docs/TROUBLESHOOTING_OPENCODE_EVAL.md`
