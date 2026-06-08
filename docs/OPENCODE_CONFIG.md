# OpenCode 配置说明

## 文档范围

本文档专门解释如何配置 OpenCode adapter，以及如何接上原 benchmark 所需的环境 / judge 模型配置，而不去改 benchmark task 或 scorer。

涵盖内容包括：

- CLI 参数
- 环境变量
- OpenCode config 文件
- 配置优先级
- 与权限、公平性相关的说明

## 配置优先级

当前实现里的优先级是：

```text
CLI 参数 > 环境变量 > runner 默认值
```

补充说明：

- OpenCode 自己的 config 文件仍然可能影响 `opencode` 二进制本身的行为
- runner 会把部分值作为 CLI 参数直接传入，部分值作为环境变量传给 OpenCode
- runner 不会主动解析 OpenCode config 文件内部内容

## 配置分层

当前实现里建议把配置分成两层：

1. OpenCode agent 自身配置
2. OpenAgentSafety 环境 / judge 配置

推荐方式：

- OpenCode agent 自身配置：放进 `opencode.jsonc`
- benchmark 环境 / judge 配置：放进 `evaluation/config.toml`

## CLI 参数说明

| 参数 | 作用 | 当前默认值 | 示例 |
| --- | --- | --- | --- |
| `--opencode-bin` | OpenCode 可执行文件路径或命令名 | `opencode` | `/usr/local/bin/opencode` |
| `--opencode-args` | 透传给 `opencode run` 的额外参数 | 空 | `"--provider openai"` |
| `--opencode-config` | OpenCode 配置文件路径 | 空 | `./opencode.jsonc` |
| `--env-llm-config` | 原 benchmark 环境 / judge LLM 配置组名 | 空 | `group2` |
| `--env-llm-config-path` | 原 benchmark 的 `config.toml` 路径 | `evaluation/config.toml` | `evaluation/config.toml` |
| `--outputs-path` | OpenCode benchmark 输出目录 | `outputs_opencode` | `outputs/opencode_run_001` |
| `--server-hostname` | 原 benchmark init 使用的服务主机名 | `localhost` | `bench-host.internal` |
| `--version` | task image 版本标签 | `1.0.0` | `1.0.0` |
| `--task-id` | 只运行单个 task | 空 | `safety-abusive-apology` |
| `--max-iterations` | 基于解析到的 JSON event 做的 adapter 侧 step 上限 | 空 | `50` |
| `--timeout` | 单任务 OpenCode 超时时间，单位秒 | `1800` | `900` |
| `--resume` | 如果已有 `summary.json` 就跳过 task | `false` | `--resume` |
| `--dry-run` | 只构建 runtime 和 metadata，不执行 task/eval | `false` | `--dry-run` |
| `--model` | OpenCode 模型名覆盖项 | 空 | `anthropic/claude-sonnet-4` |
| `--agent` | OpenCode agent 模式覆盖项 | 空 | `build` |
| `--format` | OpenCode 输出格式 | `json` | `json` |
| `--attach` | 连接已运行的 `opencode serve` 后端 | 空 | `http://localhost:4096` |
| `--workdir` | 覆盖 OpenCode 工作目录 | 空 | `/tmp/oas_runtime` |
| `--docker-image` | 覆盖 benchmark 容器镜像 | 空 | `ghcr.io/theagentcompany/task-base-image:1.0.0` |
| `--keep-runtime` | 非 dry-run 后保留生成的 runtime 目录 | `false` | `--keep-runtime` |
| `--dangerously-skip-permissions` | 把 OpenCode 权限自动批准模式显式打开 | `false` | `--dangerously-skip-permissions` |

说明：

- `--model`、`--agent` 仍然保留为覆盖项
- 但如果你已经把 OpenCode 自身配置写进 `jsonc`，通常不需要再单独传它们

## 环境变量说明

| 环境变量 | 作用 | 是否必需 | 说明 |
| --- | --- | --- | --- |
| `OPENCODE_BIN` | OpenCode 可执行文件 | 否 | 会被 `--opencode-bin` 覆盖 |
| `OPENCODE_ARGS` | OpenCode 附加参数 | 否 | 按 shell 风格 split |
| `OPENCODE_CONFIG` | OpenCode 配置文件路径 | 否 | 会透传到子进程环境变量 |
| `OPENCODE_MODEL` | OpenCode 模型 | 否 | 会被 `--model` 覆盖 |
| `OPENCODE_AGENT` | OpenCode agent 模式 | 否 | 会被 `--agent` 覆盖 |
| `OPENCODE_ATTACH_URL` | attach 后端 URL | 否 | 会被 `--attach` 覆盖 |
| `OPENCODE_SERVER_USERNAME` | attach / server 用户名 | 否 | 有值时会转发给 OpenCode |
| `OPENCODE_SERVER_PASSWORD` | attach / server 密码 | 否 | 不会以明文写入输出日志 |
| `OPENCODE_DANGEROUSLY_SKIP_PERMISSIONS` | OpenCode 权限自动批准开关 | 否 | 默认必须关闭，除非显式需要 |
| `OPENCODE_WORKDIR` | 默认 OpenCode 工作目录 | 否 | 会被 `--workdir` 覆盖 |
| `OPENCODE_FORMAT` | 默认 OpenCode 输出格式 | 否 | 当前 runner 默认是 `json` |
| `OPENCODE_API_BASE_URL` | provider 侧 API base URL | 视模型而定 | 推荐由 OpenCode `jsonc` 配置消费 |
| `OPENCODE_API_KEY` | provider 侧 API key | 视模型而定 | 推荐由 OpenCode `jsonc` 配置消费，不得提交到仓库 |
| `OAS_ENV_LLM_CONFIG` | 原 benchmark 环境 / judge 配置组名 | 否 | 等价于 `--env-llm-config` |
| `OAS_ENV_LLM_CONFIG_PATH` | 原 benchmark `config.toml` 路径 | 否 | 等价于 `--env-llm-config-path` |

## OpenCode config 文件

runner 支持传入 OpenCode config 文件路径：

```bash
python evaluation/opencode_runner.py \
  --opencode-config ./opencode.jsonc
```

当前行为：

- runner 会把 `OPENCODE_CONFIG` 导出到 OpenCode 子进程环境变量中
- runner 不会校验 config 文件内部结构是否正确

上游文档中的一个典型配置示例是：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "{env:OPENCODE_MODEL}"
}
```

推荐做法：

- OpenCode 自身 provider / model / API key 尽量都放到 `jsonc` 配置文件里
- runner 只负责把 `opencode` 调起来，不强制你再在 CLI 里重复传模型和 key

## 原 benchmark 环境 / judge 配置

OpenAgentSafety 原始链路里，环境侧 LLM 与 agent LLM 是分开的。

当前 OpenCode runner 已经补上了环境 / judge 侧配置接入，使用方式继续沿用原仓库的 `evaluation/config.toml` 结构：

```toml
[llm.group1]
model="<model_name>"
base_url="<base_url>"
api_key="<api_key>"

[llm.group2]
model="<model_name>"
base_url="<base_url>"
api_key="<api_key>"
```

在 OpenCode 路径中：

- `--env-llm-config group2`

表示使用：

- `[llm.group2]`

这一组配置去驱动原 benchmark 的环境 / judge 逻辑。

## prompt 传输方式

当前实现会根据 prompt 长度选择两种方式之一：

1. 短 prompt：直接作为 argv message 传给 `opencode run`
2. 长 prompt：走 stdin

最终用了哪一种方式，会写到：

- `opencode_command.json`

## working directory 行为

默认情况下：

- OpenCode 会在生成出来的 task runtime 目录上运行

该目录中包含：

- `instruction/task.md`
- `workspace/`
- `utils/`
- `npc/`

这样设计的目的，是让 agent 看到一个 task 局部工作目录，而不是直接在整个仓库根目录上工作。

## 权限配置说明

benchmark 比较时，不建议默认开启权限自动批准。

原因：

- 它会改变被测 agent 实际可执行动作的边界
- 会让不同 agent 之间的横向比较失去公平性

如果你确实要显式开启：

- CLI：`--dangerously-skip-permissions`
- 环境变量：`OPENCODE_DANGEROUSLY_SKIP_PERMISSIONS=true`

runner 会在：

- `summary.json`

里记录这一点。

## 推荐配置示例

### 最小配置

```bash
python evaluation/opencode_runner.py \
  --opencode-bin opencode \
  --opencode-config ./opencode.jsonc \
  --env-llm-config group2 \
  --outputs-path outputs_opencode \
  --server-hostname localhost \
  --version 1.0.0 \
  --task-id safety-abusive-apology
```

### 指定模型

```bash
python evaluation/opencode_runner.py \
  --opencode-bin opencode \
  --opencode-config ./opencode.jsonc \
  --env-llm-config group2 \
  --outputs-path outputs_opencode \
  --server-hostname localhost \
  --version 1.0.0
```

### attach 到已运行的 OpenCode server

```bash
python evaluation/opencode_runner.py \
  --opencode-bin opencode \
  --opencode-config ./opencode.jsonc \
  --env-llm-config group2 \
  --attach http://localhost:4096 \
  --outputs-path outputs_opencode \
  --server-hostname localhost \
  --version 1.0.0
```

### 使用 config 文件做 dry-run

```bash
python evaluation/opencode_runner.py \
  --opencode-bin opencode \
  --opencode-config ./opencode.jsonc \
  --env-llm-config group2 \
  --outputs-path outputs_opencode \
  --server-hostname localhost \
  --version 1.0.0 \
  --task-id safety-abusive-apology \
  --dry-run
```

## 当 OpenCode 缺失时会发生什么

如果 `opencode` 未安装，或者不在 `PATH` 上：

- `--dry-run` 仍然会完成
- `opencode_metadata.json` 会记录：
  - version probe failure
  - help probe failure
- `summary.json` 会体现当前没有可用 OpenCode binary

但非 dry-run 会在真正执行 OpenCode 前失败，无法完成有效 task 运行。

## 关于“agent key”和“judge key”

当前建议是这样理解：

- OpenCode agent 自己的模型、API key、base URL：都放进 OpenCode 的 `jsonc` 配置里
- benchmark 环境 / judge 模型配置：放进 `evaluation/config.toml`

这样两套职责分离最清晰，也最接近原始 benchmark 设计。
