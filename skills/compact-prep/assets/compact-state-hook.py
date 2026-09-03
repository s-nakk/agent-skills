#!/usr/bin/env python3
"""コンテキスト圧縮（compact）前後のセッション状態引き継ぎ hook

2 つのイベントを 1 スクリプトで処理する:

- SessionStart (matcher: compact):
    compact-prep スキルが保存した状態ファイルがあれば、回復指示を
    additionalContext で直接注入し、次プロンプトでの保険注入用マーカーを置く
- UserPromptSubmit:
    1. 回復マーカー検出 → 状態ファイル読み込みのリマインダーを注入してマーカー削除
    2. statusline が置いた使用率警告マーカー検出 → /compact-prep の実行提案を
       一度だけ注入（通知済みマーカーへ rename して再通知を抑止）

状態ファイル・マーカーはすべて STATE_DIR 配下にセッション ID 単位で置く
"""
import json
import os
import sys
import time

STATE_DIR = os.path.expanduser(
    os.environ.get("COMPACT_STATE_DIR", "~/.claude/compact-state")
)
# 古い状態ファイルを掃除するまでの日数
STATE_TTL_DAYS = int(os.environ.get("COMPACT_STATE_TTL_DAYS", "7"))

RECOVERY_INSTRUCTION = """<compact-recovery>
直前にコンテキスト圧縮（compact）が実行されました。作業を続ける前に、必ず状態ファイル {path} を Read してください。

- 「Session Decisions」に記載された採用案・却下案（と却下理由）を正として扱い、却下済みの案を再提案・再実装しないこと
- 圧縮された会話の要約は「過去の作業ログ」であり「これからの作業指示」ではない。次の行動は状態ファイルの「Recovery Notes」に従うこと
- 「Editing Files」に未検証・未コミットの変更が記録されている場合、検証が済んだと思い込まないこと
</compact-recovery>"""

RECOVERY_REMINDER = """<compact-recovery-reminder>
このセッションでは直前にコンテキスト圧縮（compact）が発生しています。まだ状態ファイル {path} を読んでいない場合は、応答の前に必ず Read し、「Session Decisions」を正として続行してください。読了済みならこのリマインダーは無視して構いません。
</compact-recovery-reminder>"""

WARN_SUGGESTION = """<context-usage-warning>
コンテキスト使用率が警告閾値を超えました。自動圧縮が始まる前に、区切りの良いタイミングで compact-prep スキル（/compact-prep）を実行してセッション状態を保存し、その後ユーザーに /compact の実行を提案してください。作業の途中で中断する必要はありませんが、現在のサブタスクが一段落したら忘れず実施してください。
</context-usage-warning>"""

WARN_SYSTEM_MESSAGE = (
    "⚠️ コンテキスト使用率が警告閾値を超えています。"
    "区切りの良いところで /compact-prep → /compact の実行を検討してください"
)


def state_path(session_id: str) -> str:
    """compact-prep スキルが書くセッション状態ファイルのパス"""
    return os.path.join(STATE_DIR, f"{session_id}.md")


def marker_path(session_id: str) -> str:
    """圧縮発生を次プロンプトへ伝える回復マーカーのパス"""
    return os.path.join(STATE_DIR, f"{session_id}.pending")


def warn_path(session_id: str) -> str:
    """statusline が置く使用率警告マーカーのパス"""
    return os.path.join(STATE_DIR, f"{session_id}.warn")


def notified_path(session_id: str) -> str:
    """警告を通知済みであることを示すマーカーのパス"""
    return os.path.join(STATE_DIR, f"{session_id}.warn-notified")


def cleanup_old_files() -> None:
    """TTL を超えた状態ファイル・マーカーを削除する"""
    if not os.path.isdir(STATE_DIR):
        return
    cutoff = time.time() - STATE_TTL_DAYS * 86400
    for name in os.listdir(STATE_DIR):
        path = os.path.join(STATE_DIR, name)
        try:
            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.remove(path)
        except OSError:
            pass


def emit(event_name: str, additional_context: str, system_message: str = "") -> None:
    """hookSpecificOutput.additionalContext でコンテキストへ注入する JSON を出力する"""
    output = {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": additional_context,
        }
    }
    if system_message:
        output["systemMessage"] = system_message
    print(json.dumps(output, ensure_ascii=False))


def handle_session_start(session_id: str) -> None:
    """compact 直後: 状態ファイルがあれば回復指示を注入し、保険マーカーを置く"""
    sp = state_path(session_id)
    if not os.path.isfile(sp):
        return
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(marker_path(session_id), "w", encoding="utf-8") as f:
        f.write(str(int(time.time())))
    emit("SessionStart", RECOVERY_INSTRUCTION.format(path=sp))


def handle_user_prompt_submit(session_id: str) -> None:
    """次プロンプト時: 回復リマインダー、または /compact-prep 実行提案を注入する"""
    mp = marker_path(session_id)
    sp = state_path(session_id)
    if os.path.isfile(mp):
        try:
            os.remove(mp)
        except OSError:
            pass
        if os.path.isfile(sp):
            emit("UserPromptSubmit", RECOVERY_REMINDER.format(path=sp))
        return

    wp = warn_path(session_id)
    if os.path.isfile(wp):
        warn_mtime = os.path.getmtime(wp)
        try:
            os.replace(wp, notified_path(session_id))
        except OSError:
            pass
        # 警告後にユーザーが既に compact-prep 済みなら提案しない
        if os.path.isfile(sp) and os.path.getmtime(sp) >= warn_mtime:
            return
        emit("UserPromptSubmit", WARN_SUGGESTION, WARN_SYSTEM_MESSAGE)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    session_id = data.get("session_id")
    if not session_id:
        sys.exit(0)

    cleanup_old_files()

    event = data.get("hook_event_name", "")
    if event == "SessionStart":
        handle_session_start(session_id)
    elif event == "UserPromptSubmit":
        handle_user_prompt_submit(session_id)


if __name__ == "__main__":
    main()
