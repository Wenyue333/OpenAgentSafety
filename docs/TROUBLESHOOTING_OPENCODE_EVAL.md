# OpenCode 评测排错手册

## 使用方式

每个问题都按下面这个格式组织：

```text
现象
可能原因
排查命令
解决方法
```

## 1. OpenCode 未安装

现象：

- `opencode` 命令不存在
- `opencode_metadata.json` 中显示 `command not found`

可能原因：

- 从未安装 OpenCode CLI
- 安装过程失败

排查命令：

```bash
opencode --version
opencode --help
```

解决方法：

- 按上游支持的方式安装 OpenCode
- 安装后重新执行 help / version 检查

## 2. OpenCode 已安装但不在 `PATH`

现象：

- shell 提示 `opencode` 不存在
- 用绝对路径可以运行，但裸命令不行

可能原因：

- OpenCode 安装目录没有加入 `PATH`

排查命令：

```bash
which opencode
where opencode
```

解决方法：

- 把安装目录加入 `PATH`
- 或者直接用 `--opencode-bin /absolute/path/to/opencode`

## 3. `opencode run` 不存在

现象：

- `opencode --help` 正常
- `opencode run --help` 失败

可能原因：

- OpenCode 版本过旧或不兼容
- 当前安装包的 CLI 子命令布局不同

排查命令：

```bash
opencode --version
opencode --help
opencode run --help
```

解决方法：

- 升级到当前上游版本
- 以官方文档中的实际子命令名为准

## 4. 模型配置错误

现象：

- OpenCode 启动后立刻报错
- provider/model 解析失败

可能原因：

- `--model` 不正确
- OpenCode config 里的 provider 配置不匹配

排查命令：

```bash
opencode run --help
cat opencode.json
```

解决方法：

- 使用当前 OpenCode 版本支持的 provider/model 字符串
- 对齐 CLI 参数和 config 文件里的模型配置

## 5. API key 缺失

现象：

- OpenCode 报认证错误
- 提示缺少凭据

可能原因：

- provider key 没设置
- 环境变量名写错

排查命令：

```bash
echo $OPENCODE_API_KEY
env | grep OPENCODE
```

解决方法：

- 正确导出 provider key
- 不要把 key 写进仓库文件

## 6. API base URL 错误

现象：

- 网络连接失败
- 请求被发往错误 endpoint

可能原因：

- `OPENCODE_API_BASE_URL` 配错
- OpenCode config 中 provider block 配错

排查命令：

```bash
env | grep OPENCODE_API_BASE_URL
cat opencode.json
```

解决方法：

- 修正 base URL
- 先单独跑一个最小 `opencode run` 检查模型调用是否正常

## 7. 权限审批卡住或被拒绝

现象：

- OpenCode 在需要权限的动作上拒绝执行
- 或表现为非交互模式下无法继续

可能原因：

- 非交互模式会自动拒绝某些权限请求
- OpenCode 当前权限策略比 benchmark task 所需更严格

排查命令：

```bash
opencode run --help
cat outputs_opencode/<task_id>/opencode_stderr.log
```

解决方法：

- 检查 OpenCode 权限设置
- 除非你明确接受公平性变化，否则不要默认开启 `--dangerously-skip-permissions`

## 8. working directory 错误

现象：

- agent 找不到 `instruction/task.md`
- agent 找不到 `workspace/`

可能原因：

- `--workdir` 指到了别的目录
- runtime 目录没有正确生成

排查命令：

```bash
ls outputs_opencode/<task_id>/runtime
cat outputs_opencode/<task_id>/instruction.txt
cat outputs_opencode/<task_id>/opencode_command.json
```

解决方法：

- 移除自定义 `--workdir`
- 让 runner 使用默认生成的 runtime 目录

## 9. Docker 不可用

现象：

- 非 dry-run 在 init/eval 之前就失败

可能原因：

- Docker 未安装
- Docker daemon 未启动

排查命令：

```bash
docker --version
docker ps
```

解决方法：

- 安装并启动 Docker
- 在 Docker 可用前先使用 `--dry-run`

## 10. task 初始化失败

现象：

- `init_stdout.log` 或 `init_stderr.log` 显示 init 非零退出
- `summary.json` 在 eval 前就标记失败

可能原因：

- benchmark 服务没有启动
- 服务主机名路由错误
- 依赖服务没有恢复到健康状态

排查命令：

```bash
cat outputs_opencode/<task_id>/init_stdout.log
cat outputs_opencode/<task_id>/init_stderr.log
```

解决方法：

- 重新检查 `docs/SETUP.md`
- 确认服务栈健康
- 确认 `SERVER_HOSTNAME` 正确

## 11. 官方 eval 失败

现象：

- `eval_result.json` 缺失
- `eval_stdout.log` / `eval_stderr.log` 中有错误

可能原因：

- task init 实际没有成功
- evaluator 解密失败
- trajectory 文件路径缺失或格式不对

排查命令：

```bash
cat outputs_opencode/<task_id>/eval_stdout.log
cat outputs_opencode/<task_id>/eval_stderr.log
```

解决方法：

- 先检查 init 日志
- 再检查生成的 `opencode_trajectory.json`
- 必要时用 `--keep-runtime` 重新跑单任务方便定位

## 12. `evaluation/config.toml` 缺失或 `--env-llm-config` 配错

现象：

- non-dry-run 一开始就报缺少 `--env-llm-config`
- 或提示 `config.toml` 缺失
- 或提示某个 `[llm.<name>]` 配置组缺少 `model/base_url/api_key`

可能原因：

- 没有准备原 benchmark 风格的 `evaluation/config.toml`
- `--env-llm-config` 指向了不存在的配置组
- 配置组字段不完整

排查命令：

```bash
cat evaluation/config.toml
```

解决方法：

- 按原始 `evaluation/README.md` 的格式创建 `evaluation/config.toml`
- 确保存在类似：

```toml
[llm.group2]
model="<model_name>"
base_url="<base_url>"
api_key="<api_key>"
```

- 并在运行时传：

```bash
--env-llm-config group2
```

## 13. post-hoc LLM judge 缺少模型配置

现象：

- 之后运行 `evaluation/llm_as_judge.py` 或 `evaluation/safe_completion_eval.py` 时失败

可能原因：

- 这些脚本自己的模型/环境变量没有配置

排查命令：

```bash
cat evaluation/llm_as_judge.py
cat evaluation/safe_completion_eval.py
```

解决方法：

- 如果你要运行这两个脚本，需要单独配置它们所需的模型环境
- 注意 OpenCode runner 本身没有修改这两个脚本

## 14. 单任务超时

现象：

- `summary.json` 中出现 `timed_out: true`

可能原因：

- task 太大，当前 timeout 不够
- provider 延迟高
- 浏览器交互慢或阻塞

排查命令：

```bash
cat outputs_opencode/<task_id>/summary.json
cat outputs_opencode/<task_id>/opencode_stdout.log
cat outputs_opencode/<task_id>/opencode_stderr.log
```

解决方法：

- 增大 `--timeout`
- 调试时先用 `--task-id` 缩小范围
- 检查 task 是否依赖当前不可用的服务或浏览器能力

## 15. stdout / stderr 太大

现象：

- 日志非常大，不方便查看

可能原因：

- provider 输出过于冗长
- tool 重试过多

排查命令：

```bash
ls -lh outputs_opencode/<task_id>/
```

解决方法：

- 如果使用了 `--format json`，优先看 `opencode_raw_output.jsonl`
- 跑完整 benchmark 前先用单任务调试
- 需要时对日志做归档

## 16. `--resume` 后仍重复运行

现象：

- 本来希望跳过的 task 又重新执行了

可能原因：

- 对应 task 的 `summary.json` 不存在
- 两次运行用了不同的 `--outputs-path`

排查命令：

```bash
ls outputs_opencode/<task_id>/summary.json
cat outputs_opencode/opencode_results.json
```

解决方法：

- 保持相同的 `--outputs-path`
- 确认 resume 依赖的 `summary.json` 已经生成

## 17. result 文件缺失

现象：

- `eval_result.json` 或 `traj_<task_id>.json` 不存在

可能原因：

- 运行在中间阶段失败了
- 当前其实是 dry-run

排查命令：

```bash
cat outputs_opencode/<task_id>/summary.json
```

解决方法：

- 先确认是否用了 `--dry-run`
- 按 init -> OpenCode -> eval 的顺序检查日志

## 18. OpenCode 输出不是 JSON

现象：

- trajectory 映射效果较弱或不完整
- raw output 文件是 `.txt` 而不是 `.jsonl`

可能原因：

- 没有使用 `--format json`
- 当前 OpenCode 版本与预期不一致

排查命令：

```bash
cat outputs_opencode/<task_id>/opencode_command.json
cat outputs_opencode/<task_id>/opencode_raw_output.jsonl
```

解决方法：

- 优先使用 `--format json`
- 用 `opencode run --help` 确认当前版本是否支持对应格式

## 19. 要不要开 `--dangerously-skip-permissions`

现象：

- 你在权衡是否为了减少权限阻塞而打开自动批准

可能原因：

- 某些 task 所需动作超过了当前 OpenCode 权限策略

排查命令：

```bash
cat outputs_opencode/<task_id>/summary.json
cat outputs_opencode/<task_id>/opencode_metadata.json
```

解决方法：

- 默认保持关闭
- 只有在你明确接受权限模型变化时才开启
- 开启后必须在 benchmark 报告里披露

## 20. Windows 上 `bash evaluation/run_opencode_eval.sh` 失败

现象：

- 系统提示 `bash` 不存在

可能原因：

- 没有安装 Git Bash、WSL 或其他 bash 环境

排查命令：

```bash
bash --version
```

解决方法：

- 安装可用的 bash 环境
- 或者直接调用 Python 入口：

```bash
python evaluation/opencode_runner.py --dry-run
```

## 21. 宿主机无法解析 `the-agent-company.com`

现象：

- 宿主机侧 OpenCode 浏览器 / tool 请求失败
- 但容器内 init 似乎是正常的

可能原因：

- 容器内 `init.sh` 只修改了容器自己的 `/etc/hosts`
- 宿主机没有对应 hosts 映射

排查命令：

```bash
ping the-agent-company.com
```

解决方法：

- 按 `servers/README.md` 修改宿主机 hosts 文件
- 确保它指向实际承载 benchmark 服务的主机
