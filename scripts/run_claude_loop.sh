#!/bin/bash
#
# Claude Code 自动执行脚本
# 用于自动化多次调用 Claude Code 进行开发工作
# 支持中断后自动续跑
#
# 用法:
#   ./run_claude_loop.sh              # 自动检测进度并继续
#   ./run_claude_loop.sh --reset      # 重置从头开始
#   ./run_claude_loop.sh 5            # 执行5次（从当前进度继续）
#   ./run_claude_loop.sh 5 --force 1 # 强制从指定task开始
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_progress() {
    echo -e "${CYAN}[PROGRESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - 进度: $1/$2"
}

log_task() {
    echo -e "${YELLOW}[TASK $1]${NC} $2"
}

# 获取任务列表文件
TASK_FILE=".tasks/data_fetch_tasks.md"
PROGRESS_FILE=".tasks/.progress"
LOG_DIR="logs/claude_loop"

# 检测当前进度
detect_progress() {
    # 方法1: 检查 progress 文件
    if [ -f "$PROGRESS_FILE" ]; then
        local last_task=$(cat "$PROGRESS_FILE")
        if [ -n "$last_task" ] && [[ "$last_task" =~ ^[0-9]+$ ]]; then
            echo "$last_task"
            return
        fi
    fi

    # 方法2: 检查最近的日志文件
    if [ -d "$LOG_DIR" ]; then
        local latest_log=$(ls -t "$LOG_DIR"/run_*.log 2>/dev/null | head -1)
        if [ -n "$latest_log" ]; then
            # 从日志中提取最后执行的 task
            local last_task=$(grep -oP 'Task[0-9]+' "$latest_log" | tail -1 | grep -oP '[0-9]+')
            if [ -n "$last_task" ]; then
                echo "$last_task"
                return
            fi
        fi
    fi

    # 默认从 Task 1 开始
    echo "0"
}

# 保存进度
save_progress() {
    echo "$1" > "$PROGRESS_FILE"
}

# 重置进度
reset_progress() {
    rm -f "$PROGRESS_FILE"
    log_info "进度已重置"
}

# 获取任务内容
get_task() {
    local task_num=$1
    # 提取第 N 个 Task 的内容
    local total_tasks=$(grep -c "^## Task" "$TASK_FILE")
    if [ "$task_num" -gt "$total_tasks" ]; then
        echo ""
        return
    fi

    local task_content=$(sed -n "/^## Task $task_num:/,/^## Task/p" "$TASK_FILE" | sed '$d' | sed '1d')
    echo "$task_content"
}

# 获取总任务数
get_total_tasks() {
    grep -c "^## Task" "$TASK_FILE"
}

# 显示帮助
show_help() {
    echo "用法: $0 [选项] [执行次数] [起始task]"
    echo ""
    echo "选项:"
    echo "  --reset     重置进度，从 Task 1 开始"
    echo "  --status    显示当前进度"
    echo "  --force N  强制从指定 task 开始"
    echo ""
    echo "参数:"
    echo "  [执行次数]   - 要调用 Claude Code 的次数（默认: 剩余任务数）"
    echo "  [起始task]   - 从第几个 task 开始（默认: 自动检测）"
    echo ""
    echo "示例:"
    echo "  $0                      # 自动检测进度并继续"
    echo "  $0 --reset              # 重置从头开始"
    echo "  $0 --status             # 查看当前进度"
    echo "  $0 5                    # 执行5次"
    echo "  $0 10 --force 3        # 强制从 Task 3 开始执行10次"
    echo ""
    echo "可用任务 ($((TOTAL_TASKS))个):"
    grep "^## Task" "$TASK_FILE" | sed 's/## //'
}

# ==================== 主逻辑 ====================

# 检查任务文件
if [ ! -f "$TASK_FILE" ]; then
    log_error "任务文件不存在: $TASK_FILE"
    exit 1
fi

TOTAL_TASKS=$(get_total_tasks)

# 解析参数
RESET=false
FORCE_START=0
CUSTOM_RUNS=0

while [ $# -gt 0 ]; do
    case "$1" in
        --reset)
            RESET=true
            shift
            ;;
        --status)
            CURRENT=$(detect_progress)
            log_info "当前进度: Task $CURRENT / $TOTAL_TASKS"
            if [ "$CURRENT" -lt "$TOTAL_TASKS" ]; then
                log_info "剩余任务: $((TOTAL_TASKS - CURRENT)) 个"
            fi
            exit 0
            ;;
        --force)
            FORCE_START=$2
            shift 2
            ;;
        *)
            if [[ "$1" =~ ^[0-9]+$ ]]; then
                CUSTOM_RUNS=$1
            fi
            shift
            ;;
    esac
done

# 创建日志目录
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/run_$(date '+%Y%m%d_%H%M%S').log"
SESSION_FILE="$LOG_DIR/sessions.txt"

# 确定起始 task
if [ "$RESET" = true ]; then
    reset_progress
    START_TASK=1
elif [ "$FORCE_START" -gt 0 ]; then
    START_TASK=$FORCE_START
    log_info "强制从 Task $START_TASK 开始"
else
    LAST_COMPLETED=$(detect_progress)
    START_TASK=$((LAST_COMPLETED + 1))
    if [ "$START_TASK" -le 1 ]; then
        START_TASK=1
    fi
fi

# 确定执行次数
if [ "$CUSTOM_RUNS" -gt 0 ]; then
    TOTAL_RUNS=$CUSTOM_RUNS
else
    TOTAL_RUNS=$((TOTAL_TASKS - START_TASK + 1))
fi

# 验证
if [ "$START_TASK" -gt "$TOTAL_TASKS" ]; then
    log_info "所有任务已完成！"
    exit 0
fi

log_info "=========================================="
log_info "Claude Code 自动执行脚本"
log_info "=========================================="
log_info "总任务数: $TOTAL_TASKS"
log_info "起始Task: $START_TASK"
log_info "执行次数: $TOTAL_RUNS"
log_info "日志文件: $LOG_FILE"
log_info "=========================================="

# 写入日志
exec > >(tee -a "$LOG_FILE") 2>&1

# 显示起始任务内容
CURRENT_TASK_CONTENT=$(get_task $START_TASK)
if [ -n "$CURRENT_TASK_CONTENT" ]; then
    log_task "$START_TASK" "起始任务:"
    echo "$CURRENT_TASK_CONTENT"
    echo ""
fi

# Claude Code 命令 - 使用原生命令 + minimax 模型
CLAUDE_CMD="claude -p"

# 记录统计
SUCCESS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

# 循环执行
for ((i=1; i<=TOTAL_RUNS; i++)); do
    CURRENT_TASK=$((START_TASK + i - 1))

    log_progress "$i" "$TOTAL_RUNS"
    log_task "$CURRENT_TASK" ""
    echo ""

    # 保存当前进度
    save_progress $((CURRENT_TASK - 1))

    # 获取任务内容
    TASK_CONTENT=$(get_task $CURRENT_TASK)

    if [ -z "$TASK_CONTENT" ]; then
        log_warning "Task $CURRENT_TASK 不存在，已完成所有任务"
        save_progress $((TOTAL_TASKS))
        break
    fi

    # 构建 prompt - 让 Claude 读取任务文件和设计文档
    TASK_PROMPT="请完成以下任务：

## 当前任务: Task $CURRENT_TASK
$TASK_CONTENT

## 项目架构参考
请先阅读以下文件了解整体架构：
1. 任务列表: .tasks/data_fetch_tasks.md
2. 设计文档: docs/plans/2026-02-24-data-fetch-design.md
3. 当前代码状态: ls -la core/data/ src/

## 工作要求
1. 先理解当前代码状态和架构
2. 按照设计文档实施当前任务
3. 每个子任务完成后进行测试
4. 完成后提交 git commit
5. 告诉我进展和结果

请开始工作。"

    # 调用 Claude Code
    log_info "开始第 $i/$TOTAL_RUNS 次调用 (Task $CURRENT_TASK)..."

    START_TIME=$(date +%s)
    TIMEOUT_SECONDS=${TIMEOUT:-1800}

    # 使用环境变量源文件 + 原生 claude 命令
    # 先写入临时文件避免引号问题
    echo "$TASK_PROMPT" > /tmp/claude_prompt_$$.txt
    if timeout "$TIMEOUT_SECONDS" bash -c "source ~/data2/lyn/minimax.bash && cat /tmp/claude_prompt_$$.txt | $CLAUDE_CMD" 2>&1; then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        log_success "Task $CURRENT_TASK 完成 (耗时: ${DURATION}秒)"
        echo "$i: SUCCESS Task$CURRENT_TASK (${DURATION}s)" >> "$SESSION_FILE"

        # 清理临时文件
        rm -f /tmp/claude_prompt_$$.txt

        # 保存完成进度
        save_progress $CURRENT_TASK
    else
        EXIT_CODE=$?
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))

        if [ $EXIT_CODE -eq 124 ]; then
            log_warning "Task $CURRENT_TASK 超时 (${TIMEOUT_SECONDS}秒)"
            echo "$i: TIMEOUT Task$CURRENT_TASK (${DURATION}s)" >> "$SESSION_FILE"
            rm -f /tmp/claude_prompt_$$.txt
        else
            FAIL_COUNT=$((FAIL_COUNT + 1))
            log_error "Task $CURRENT_TASK 失败 (退出码: $EXIT_CODE)"
            echo "$i: FAILED Task$CURRENT_TASK (exit=$EXIT_CODE)" >> "$SESSION_FILE"
            rm -f /tmp/claude_prompt_$$.txt
        fi
    fi

    echo ""
    echo "-----------------------------------------------------------"
    echo ""
done

# 最终统计
echo ""
log_info "=========================================="
log_info "执行完成"
log_info "=========================================="
log_info "完成进度: Task $CURRENT_TASK / $TOTAL_TASKS"
log_success "成功: $SUCCESS_COUNT"
[ "$FAIL_COUNT" -gt 0 ] && log_error "失败: $FAIL_COUNT"
log_info "日志: $LOG_FILE"
log_info "=========================================="

# 清理临时文件
rm -f /tmp/claude_prompt_*.txt

exit 0
