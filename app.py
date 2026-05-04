import time
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from game_logic import BluffGame, Card
from ai_interface import StrategicAI
from ui_components import get_card_path


# ==============================
# 页面基础配置
# ==============================
st.set_page_config(
    page_title="唬牌游戏",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        margin: 0;
        padding: 0;
        background: #e9e2d2;
        overflow-x: hidden;
        font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
    }

    [data-testid="stHeader"] {
        background: transparent;
        height: 0;
    }

    [data-testid="stToolbar"] {
        display: none;
    }

    .block-container {
        padding-top: 0.2rem !important;
        padding-bottom: 0 !important;
        max-width: 100% !important;
    }

    [data-testid="stVerticalBlock"] {
        gap: 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================
# 自定义组件
# ==============================
COMPONENT_DIR = Path(__file__).parent / "components" / "card_board" / "frontend"
card_board_component = components.declare_component(
    "card_board",
    path=str(COMPONENT_DIR),
)


# ==============================
# 常量
# ==============================
PLAYER_INFO = [
    {"name": "我自己", "avatar": "👧"},
    {"name": "上家AI", "avatar": "🤖"},
    {"name": "对家AI", "avatar": "🤖"},
    {"name": "下家AI", "avatar": "🤖"},
]

HUMAN_IDX = 0


# ==============================
# 初始化
# ==============================
def init_game_state(force: bool = False) -> None:
    if force or "game" not in st.session_state:
        st.session_state.game = BluffGame()
        st.session_state.ais = [
            StrategicAI(st.session_state.game, i)
            for i in range(4)
        ]
        st.session_state.logs = ["🎮 游戏正式开始！"]
        st.session_state.message = ""

    if "last_component_event_token" not in st.session_state:
        st.session_state.last_component_event_token = None

    if "component_instance_id" not in st.session_state:
        st.session_state.component_instance_id = 0


init_game_state()


# ==============================
# 工具函数
# ==============================
def add_log(msg: str) -> None:
    st.session_state.logs.append(f"{time.strftime('%H:%M:%S')} {msg}")


def restart_game() -> None:
    old_token = st.session_state.get("last_component_event_token")

    st.session_state.game = BluffGame()
    st.session_state.ais = [
        StrategicAI(st.session_state.game, i)
        for i in range(4)
    ]
    st.session_state.logs = ["🎮 游戏正式开始！"]
    st.session_state.message = ""

    # 只有重开局才换组件 key，用于清空前端本地选牌状态。
    st.session_state.component_instance_id += 1

    # 保留旧 token，避免 restart 事件被重复消费。
    st.session_state.last_component_event_token = old_token


def is_new_component_event(event_data) -> bool:
    if not isinstance(event_data, dict):
        return False

    token = event_data.get("token")
    if not token:
        return False

    if st.session_state.last_component_event_token == token:
        return False

    st.session_state.last_component_event_token = token
    return True


def public_pile_count(game: BluffGame) -> int:
    return sum(len(cards) for _, cards in game.public_pile)


def get_available_ranks() -> list[str]:
    if hasattr(Card, "RANKS"):
        return list(Card.RANKS)

    return ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]


def normalize_indices(indices, hand_len: int) -> list[int]:
    if not indices:
        return []

    safe_indices = set()

    for idx in indices:
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            continue

        if 0 <= idx < hand_len:
            safe_indices.add(idx)

    return sorted(safe_indices)


def advance_turn_after_play_if_needed(before_player: int) -> None:
    game = st.session_state.game

    if game.game_winner is not None:
        return

    if game.current_player == before_player and hasattr(game, "_next_turn"):
        game._next_turn()


def update_ai_credit_after_challenge() -> None:
    game = st.session_state.game

    if hasattr(game, "challenge_callback") and game.challenge_callback:
        loser_id, was_bluffing = game.challenge_callback

        for ai in st.session_state.ais:
            if hasattr(ai, "update_credit_after_challenge"):
                ai.update_credit_after_challenge(loser_id, was_bluffing)

        game.challenge_callback = None


def build_human_cards_payload() -> list[dict]:
    game = st.session_state.game
    payload = []

    for idx, card in enumerate(game.players[HUMAN_IDX]):
        payload.append(
            {
                "index": idx,
                "rank": card.rank,
                "suit": card.suit,
                "img": get_card_path(card),
            }
        )

    return payload


def render_card_board():
    game = st.session_state.game

    return card_board_component(
        player_info=PLAYER_INFO,
        players_counts=[len(p) for p in game.players],
        current_player=game.current_player,
        declared_rank=game.declared_rank,
        public_count=public_pile_count(game),
        logs=st.session_state.logs,
        human_cards=build_human_cards_payload(),
        selected_cards=[],
        human_turn=game.current_player == HUMAN_IDX and game.game_winner is None,
        ai_turn=game.current_player != HUMAN_IDX and game.game_winner is None,
        available_ranks=get_available_ranks(),
        key=f"card_board_{st.session_state.component_instance_id}",
        default=None,
    )


# ==============================
# 玩家动作
# ==============================
def handle_human_play(event_data: dict) -> None:
    game = st.session_state.game

    if game.game_winner is not None:
        return

    if game.current_player != HUMAN_IDX:
        st.session_state.message = "当前不是你的回合。"
        return

    hand = game.players[HUMAN_IDX]
    selected_indices = normalize_indices(
        event_data.get("selected_cards", []),
        len(hand),
    )

    if not selected_indices:
        st.session_state.message = "请先点击选择要出的牌。"
        return

    before_player = game.current_player

    if game.declared_rank is None:
        selected_rank = event_data.get("rank")

        if selected_rank not in get_available_ranks():
            selected_rank = "A"

        started = game.start_round(selected_rank)
        if not started:
            st.session_state.message = "本轮已经叫过牌，不能重复叫牌。"
            return

        played = game.play_cards(selected_indices)

        if played:
            add_log(f"你叫了【{selected_rank}】，并打出了{len(selected_indices)}张牌")
            advance_turn_after_play_if_needed(before_player)
            st.session_state.message = ""
            st.rerun()

        st.session_state.message = "出牌失败，请重新选择。"
        return

    played = game.play_cards(selected_indices)

    if played:
        add_log(f"你打出了{len(selected_indices)}张牌")
        advance_turn_after_play_if_needed(before_player)
        st.session_state.message = ""
        st.rerun()

    st.session_state.message = "出牌失败，请重新选择。"


def handle_human_challenge() -> None:
    game = st.session_state.game

    if game.game_winner is not None:
        return

    if game.current_player != HUMAN_IDX:
        st.session_state.message = "当前不是你的回合。"
        return

    if not game.public_pile:
        st.session_state.message = "当前公共牌堆为空，不能质疑。"
        return

    ok = game.challenge()

    if ok:
        add_log("你发起了质疑")
        update_ai_credit_after_challenge()
        st.session_state.message = ""
        st.rerun()

    st.session_state.message = "质疑失败。"


def handle_human_pass() -> None:
    game = st.session_state.game

    if game.game_winner is not None:
        return

    if game.current_player != HUMAN_IDX:
        st.session_state.message = "当前不是你的回合。"
        return

    if game.declared_rank is None:
        st.session_state.message = "首轮必须先叫牌并出牌，不能直接过牌。"
        return

    ok = game.pass_turn()

    if ok:
        add_log("你选择过牌")
        st.session_state.message = ""
        st.rerun()

    st.session_state.message = "过牌失败。"


# ==============================
# AI 单步动作
# ==============================
def execute_single_ai_turn() -> bool:
    game = st.session_state.game

    if game.game_winner is not None:
        return False

    if game.current_player == HUMAN_IDX:
        return False

    current_idx = game.current_player
    current_ai = st.session_state.ais[current_idx]

    update_ai_credit_after_challenge()

    ai_action = current_ai.get_action()

    if not ai_action:
        ok = game.pass_turn()
        if ok:
            add_log(f"{PLAYER_INFO[current_idx]['name']} 选择过牌")
            return True
        return False

    action_type = ai_action[0]
    log_msg = ""

    if action_type == "declare":
        declare_rank = ai_action[1]
        before_player = game.current_player

        game.start_round(declare_rank)

        ai_hand = game.players[current_idx]
        valid_indices = [
            i for i, c in enumerate(ai_hand)
            if c.is_wildcard() or c.rank == declare_rank
        ]

        play_indices = valid_indices[:1] if valid_indices else [0]
        play_indices = normalize_indices(play_indices, len(ai_hand))

        if play_indices:
            game.play_cards(play_indices)
            advance_turn_after_play_if_needed(before_player)
            log_msg = f"{PLAYER_INFO[current_idx]['name']} 叫了【{declare_rank}】，并打出了{len(play_indices)}张牌"
        else:
            game.pass_turn()
            log_msg = f"{PLAYER_INFO[current_idx]['name']} 选择过牌"

    elif action_type == "play":
        before_player = game.current_player
        ai_hand = game.players[current_idx]
        play_indices = normalize_indices(ai_action[1], len(ai_hand))

        if play_indices:
            game.play_cards(play_indices)
            advance_turn_after_play_if_needed(before_player)
            log_msg = f"{PLAYER_INFO[current_idx]['name']} 打出了{len(play_indices)}张牌"
        else:
            game.pass_turn()
            log_msg = f"{PLAYER_INFO[current_idx]['name']} 选择过牌"

    elif action_type == "challenge":
        if game.public_pile:
            game.challenge()
            update_ai_credit_after_challenge()
            log_msg = f"{PLAYER_INFO[current_idx]['name']} 发起了质疑"
        else:
            game.pass_turn()
            log_msg = f"{PLAYER_INFO[current_idx]['name']} 无法质疑，选择过牌"

    elif action_type == "pass":
        game.pass_turn()
        log_msg = f"{PLAYER_INFO[current_idx]['name']} 选择过牌"

    else:
        game.pass_turn()
        log_msg = f"{PLAYER_INFO[current_idx]['name']} 选择过牌"

    if log_msg:
        add_log(log_msg)
        return True

    return False


# ==============================
# 组件事件处理
# ==============================
def handle_component_event(event_data) -> None:
    if not is_new_component_event(event_data):
        return

    event_type = event_data.get("event")

    if event_type == "ai_tick":
        game = st.session_state.game

        if game.game_winner is None and game.current_player != HUMAN_IDX:
            did_action = execute_single_ai_turn()
            if did_action:
                st.rerun()

        return

    if event_type != "action":
        return

    action = event_data.get("action")

    if action == "restart":
        restart_game()
        st.rerun()

    elif action == "play":
        handle_human_play(event_data)

    elif action == "challenge":
        handle_human_challenge()

    elif action == "pass":
        handle_human_pass()


# ==============================
# 主流程
# ==============================
event_data = render_card_board()
handle_component_event(event_data)

if st.session_state.message:
    st.warning(st.session_state.message)

game = st.session_state.game

if game.game_winner is not None:
    winner_name = PLAYER_INFO[game.game_winner]["name"]

    if game.game_winner == HUMAN_IDX:
        st.success("🎉 恭喜你！你赢得了本局游戏！")
    else:
        st.error(f"😔 {winner_name} 赢得了本局游戏。")

    if st.button("🔄 再来一局", type="primary"):
        restart_game()
        st.rerun()