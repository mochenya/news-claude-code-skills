---
name: cron-script-generator
description: Use when creating or migrating a system-crontab launcher that runs `hermes chat -q` and delivers results with `hermes send`. Covers prompt structure, target selection, delivery mode, safe crontab installation, and verification. Do not use for editing only an existing prompt, inspecting an existing crontab, or creating a Hermes built-in cron job.
version: 2.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [cron, shell, scheduling, messaging, automation]
    related_skills: [scheduled-news-briefs]
---

# Cron 启动器脚本生成

## 目标与定位

为需要多步处理、主动推送、附件或多条消息的任务创建系统 crontab 启动器。

为什么涉及 IM 推送必须走脚本，而不是 Hermes 内置 cron job：

- 内置 cron job 的任务会话不能调用 IM 发送消息：`send_message` 被调度器跳过，final-response 自动投递完全依赖 job 记录的 `deliver` 配置，配错即静默失败、无回执可查。
- 脚本路线由任务内显式执行 `hermes send --to` CLI 完成投递：exit code 可验证、日志可追溯、失败可重试并非零退出。
- 因此：凡需要推送到 IM（Telegram / 飞书等）的定时任务，一律用本 Skill 创建启动器；只有不涉及投递的纯本地任务可用 Hermes 内置 cron job。

责任边界：

- shell 启动器负责环境、锁、日志和调用 `hermes chat -q`；
- Agent 负责采集、处理、生成交付物并执行 `hermes send`；
- 实际消息投递统一使用 `hermes send --to`，不使用 `send_message`，不依赖 Agent final-response 自动投递。

## 适用边界

使用本 Skill：

- 新建 `run-{job-slug}.sh` 系统定时任务；
- 将既有 Hermes cron 任务迁移为系统 crontab 启动器；
- 任务需要主动推送报告、文件、附件或多步交付。

不使用本 Skill：

- 只修改已有启动器的 prompt；
- 只检查、修复或列出系统 crontab；
- 创建 Hermes 内置 cron job（仅限不涉及 IM 投递的纯本地任务；涉及推送的仍用本 Skill）。

## 创建前确认

开始前确认以下参数；缺失且无法从上下文确定时才询问用户。

| 参数 | 要求 |
|---|---|
| `JOB_SLUG` | kebab-case，且不与现有 `run-*.sh` 重名 |
| 调度 | cron 表达式、时区、是否需要避免与其他任务撞时 |
| 主工作流 | 一个主 Skill 或一个 workflow 文档 |
| 输入与窗口 | 数据源、时间范围、正常跳过条件 |
| 交付物 | 短文本、Markdown 报告、附件，或多步交付 |
| 推送目标 | 固定 `platform:destination[:thread_id]` |
| 异常策略 | 重试次数、正常跳过与异常退出的边界 |

目标不默认 Telegram。根据用户指定的平台、频道和线程确定；未知时执行：

```bash
hermes send --list
hermes send --list <platform>
```

完成标准：任务的调度、主工作流、目标和交付物类型均已明确。

## Prompt 结构

`HERMES_QUERY` 保持短而可执行。业务细节由主 Skill 或 workflow 承担，不在启动器 prompt 复制一遍。

```text
任务名称：{任务名称}

完成 {任务名称}：{输入 → 处理 → 交付的一句话路径}。

前置条件：
- 主工作流：加载并遵循 {主 Skill 或 workflow 路径}
- 执行参数：{时间窗口、输入、市场或运行模式}

执行路径：
1. {检查前提或正常跳过条件}
2. {采集或运行确定性脚本}
3. {处理、筛选、生成最终交付物}
4. 按“推送规则”执行实际投递并验证

完成条件：
- {所需报告或文件已生成且非空}
- {内容符合主工作流}
- {每一条必需消息均成功投递}

退出条件：
- {正常跳过条件}：exit 0，不推送或按任务约定推送
- {采集/处理失败}：非零退出，不使用旧数据或旧文件
- 推送失败：{重试次数}后仍失败则非零退出

推送规则：
- 目标：{platform:destination[:thread_id]}
- 使用下方内容类型对应的完整 `hermes send --to` 命令
- 未确认命令成功前不得视为完成
```

完成标准：prompt 有一个主工作流、明确完成/退出条件，以及固定推送目标和完整命令。

## 消息推送规范

### 目标格式

固定写入 `platform:destination[:thread_id]`，例如：

```text
telegram:-1001234567890:17585
discord:#ops
slack:C0123ABCD
```

不要只写“发送到某平台”，不要让 Agent 自行猜测目标。

### 短文本

短文本使用 heredoc 传入 stdin，避免 Markdown、引号和换行转义问题：

```bash
cat <<'MESSAGE_EOF' | hermes send --to "{TARGET}" --json
{最终短消息正文}
MESSAGE_EOF
```

### 长 Markdown 报告

长内容先写入本任务专属临时文件，再以 `--file` 发送。写入后必须验证非空；禁止将旧文件当作本次结果发送。

```bash
cat <<'BRIEF_EOF' > /tmp/{job-slug}.md
{完整最终报告正文}
BRIEF_EOF
test -s /tmp/{job-slug}.md
hermes send --to "{TARGET}" --file /tmp/{job-slug}.md --json
```

`--file` 只读取文本作为消息正文。

### 附件与二进制文件

XLSX、PDF、图片、音视频等不能用 `--file` 作为附件。用 `MEDIA:`；需要文档形式时加 `[[as_document]]`。

```bash
hermes send --to "{TARGET}" \
  "[[as_document]] {文件标题} MEDIA:/tmp/{file-name}.xlsx" --json
```

### 多步交付

每条消息、每个附件单独执行一次 `hermes send --to`。所有命令均成功才算任务完成。

默认使用 `--json`，以 exit code 为成功判定：exit code 0 表示成功；非零表示失败。按任务要求重试，仍失败则非零退出。

## 启动器要求

创建 `{PROFILE_DIR}/cron/run-{JOB_SLUG}.sh`，并满足：

- 使用 `#!/bin/sh`、`set -u`、`TZ=Asia/Shanghai`；
- `HERMES_QUERY` 用 `cat <<'EOF'`，避免 prompt 内 `$` 或反引号提前展开；
- 加载 `. "$HOME/.shell_env"`，确认 `hermes` 可执行；
- 使用 `flock -n` 防止同一任务重入；
- 日志写入 `{PROFILE_DIR}/logs/cron/{JOB_SLUG}.log`；
- 支持 `DRY_RUN=1`，仅输出将执行的 `hermes chat -q`；
- 定义 `CRON_MODEL` 和 `CRON_PROVIDER` 覆盖变量；两者都为空时不向 Hermes 传入模型参数，使用配置中的默认路由；两者都非空时成对传入；只设置其中一个时非零退出；
- 写入后 `chmod +x`，并运行 `sh -n`。
- 把 prompt 从 workflow 文档迁移到 Skill 时，同步删除所有依赖旧变量的 guard 与赋值（如 `WORKFLOW_FILE`）：`set -u` 下任何残留的未定义变量引用都会让脚本在该行立即退出，cron 侧表现为静默失败。

完成标准：脚本可执行、语法通过、DRY_RUN 不会执行实际任务。

### 模型与 Provider 覆盖

启动器使用以下变量，不直接改写配置文件或使用全局默认环境变量：

```sh
CRON_MODEL="${CRON_MODEL:-}"
CRON_PROVIDER="${CRON_PROVIDER:-}"

set -- hermes chat -q "$HERMES_QUERY" --profile "$PROFILE_NAME"
if [ -z "$CRON_MODEL" ] && [ -z "$CRON_PROVIDER" ]; then
  :
elif [ -n "$CRON_MODEL" ] && [ -n "$CRON_PROVIDER" ]; then
  set -- "$@" --model "$CRON_MODEL" --provider "$CRON_PROVIDER"
else
  printf '[%s] CRON_MODEL and CRON_PROVIDER must be set together\n' "$(timestamp)"
  exit 2
fi

if [ "${DRY_RUN:-0}" = "1" ]; then
  printf '[%s] dry run command:' "$(timestamp)"
  printf ' %s' "$@"
  printf '\n'
  exit 0
fi

"$@"
status=$?
```

`CRON_MODEL` 与 `CRON_PROVIDER` 只对当前启动器进程生效；不设置时必须保持无 `--model` / `--provider` 参数。

## 安装系统 crontab

仅在用户要求安装时修改系统 crontab。

1. 导出：`crontab -l > /tmp/crontab-{job-slug}.txt`
2. 向临时文件加入明确注释和一条启动器命令。
3. 检查差异和命令路径后，执行 `crontab /tmp/crontab-{job-slug}.txt`。
4. 重新运行 `crontab -l`，确认已安装且无重复任务。

严禁 `crontab -l | sed ... | crontab -`：中间命令失败可能清空 crontab。

## 任务不运行的排查

某 cron 任务连续几天没有投递时，按此顺序定位：

1. 看 `{PROFILE_DIR}/logs/cron/{JOB_SLUG}.log` 尾部：有 `start` 行但无 `finished` 行 → 脚本中途退出。搜 `parameter not set`（`set -u` 命中未定义变量，典型为迁移残留 guard）、`not found`、`exit 1`。
2. 同一 bug 类横扫：`grep -n <可疑变量> cron/run-*.sh`。迁移删掉的变量常同时残留在多个启动器（实例：workflow→Skill 迁移后 `WORKFLOW_FILE` 残留导致两个任务各自静默失败 3 天，日志每天只多一行 `parameter not set`）。修一个必须检查全部兄弟脚本。
3. 修复后三步验证：`sh -n` → `HOME=<真实家目录> DRY_RUN=1 <script>` 冒烟 → `HOME=<真实家目录> <script>` 手动补跑（手动跑必须显式 `HOME=` 前缀，后端可能把 `$HOME` 改写成 cwd）。以日志中出现 `hermes send` 回执 msg_id 和 `finished with status=0` 为验收，不以进程消失为准。

## 常见错误

1. 使用 `send_message`：改用 `hermes send --to`。
2. 未写完整目标：补全 `platform:destination[:thread_id]`。
3. 用 `--file` 发二进制附件：改用 `MEDIA:`。
4. 长报告直接拼进命令参数：写入 `/tmp/{job-slug}.md` 后用 `--file`。
5. 复用旧临时报告：每次覆盖写入并 `test -s`。
6. 只验证 Agent 生成内容：还必须验证每次 `hermes send` 成功。

## 完成检查

- [ ] `JOB_SLUG` 唯一，脚本位于 `{PROFILE_DIR}/cron/run-{JOB_SLUG}.sh`
- [ ] prompt 指向一个主工作流，未复制业务 Skill 的冗长规则
- [ ] 推送目标完整、固定，且与用户要求的平台一致
- [ ] 短文本、长 Markdown、附件采用正确发送方式
- [ ] 每个 `hermes send` 使用 `--to`；需要可审计结果时使用 `--json`
- [ ] 脚本通过 `sh -n`，已 `chmod +x`，DRY_RUN 可用
- [ ] 若修改 crontab，已重新读取并确认无重复或遗漏
