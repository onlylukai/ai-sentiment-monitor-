#!/usr/bin/env bash
# 密钥写入脚本：把 LLM_API_KEY 写进 .env（.env 在 .gitignore 里，不会进 git）
#
# 为什么需要这个脚本：
#   通过聊天把密钥发过来会被渠道自动脱敏——中间段替换成省略号（U+2026），
#   密钥到这里已经残缺，认证必然失败。必须在本地直接写。
#
# 用法（优先级从高到低）：
#   1) 第一个参数：   bash setup_key.sh 'sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
#   2) 环境变量：     LLM_KEY_FROM_ENV='sk-xxx' bash setup_key.sh
#   3) stdin：        printf 'sk-xxx' | bash setup_key.sh
#   4) 交互输入：     bash setup_key.sh          （提示粘贴，不回显）
set -euo pipefail

ENV_PATH="$(cd "$(dirname "$0")" && pwd)/.env"
[ -f "$ENV_PATH" ] || { echo "❌ 找不到 $ENV_PATH"; exit 1; }

VAL=""
if [ "${1:-}" != "" ]; then
  VAL="$1"
elif [ -n "${LLM_KEY_FROM_ENV:-}" ]; then
  VAL="$LLM_KEY_FROM_ENV"
elif [ ! -t 0 ]; then
  VAL="$(cat)"
else
  read -r -s -p "粘贴密钥（输入后回车，不会显示）: " VAL
  echo
fi

# 清理：去掉回车符和首尾空白（不删内部空格，内部有空格属于异常，留给下面的校验报错）
VAL="${VAL%$'\r'}"
VAL="${VAL#$'\t'}"
VAL="${VAL%$'\t'}"
VAL="${VAL# }"
VAL="${VAL% }"

# ---- 校验 ----
[ -n "$VAL" ] || { echo "❌ 没拿到密钥，请重新输入"; exit 1; }
if [ ${#VAL} -lt 20 ]; then
  echo "❌ 密钥只有 ${#VAL} 字符，太短了。"
  echo "   正常应为 32 字符以上。这么短通常是被截断或粘贴不完整。"
  exit 1
fi
case "$VAL" in
  *"…"*)
    echo "❌ 密钥里混入了省略号 '…' —— 说明是被渠道脱敏过的残缺值。"
    echo "   请重新复制完整的原始密钥再试。"
    exit 1;;
esac
case "$VAL" in
  *[[:space:]]*)
    echo "❌ 密钥里含空白字符（空格/制表符），复制时多粘了东西。"
    exit 1;;
esac
case "$VAL" in
  *[![:print:]]*)
    echo "❌ 密钥里含非 ASCII 字符，可能混入了空格或特殊符号。"
    exit 1;;
esac

# ---- 写入 .env（覆盖旧值，其它配置原样保留）----
tmp="$(mktemp)"
awk -v k="LLM_API_KEY" -v v="$VAL" '
  BEGIN { seen = 0 }
  {
    if ($0 ~ "^" k "=") { print k "=" v; seen = 1 }
    else print
  }
  END { if (!seen) print k "=" v }
' "$ENV_PATH" > "$tmp"
mv "$tmp" "$ENV_PATH"
chmod 600 "$ENV_PATH"

printf '\n✅ 已写入 %s\n   长度: %d 字符\n   权限: 600（仅本人可读）\n' "$ENV_PATH" "${#VAL}"
