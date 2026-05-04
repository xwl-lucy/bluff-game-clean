import os
import streamlit.components.v1 as components


_component_path = os.path.join(os.path.dirname(__file__), "frontend")

_card_board_component = components.declare_component(
    "card_board_component",
    path=_component_path,
)


def card_board(
    *,
    players_counts,
    current_player,
    declared_rank,
    public_count,
    logs,
    human_cards,
    selected_cards,
    player_info,
    human_turn,
    available_ranks,
    key=None,
):
    """
    渲染可点击牌桌组件。

    返回示例：
    1) 点击牌：
       {
         "event": "card_click",
         "index": 0,
         "token": "..."
       }

    2) 点击动作按钮：
       {
         "event": "action",
         "action": "play" / "challenge" / "pass" / "restart",
         "rank": "7",   # 仅首轮 play 时会带
         "token": "..."
       }
    """
    return _card_board_component(
        players_counts=players_counts,
        current_player=current_player,
        declared_rank=declared_rank,
        public_count=public_count,
        logs=logs,
        human_cards=human_cards,
        selected_cards=list(selected_cards),
        player_info=player_info,
        human_turn=human_turn,
        available_ranks=available_ranks,
        key=key,
        default=None,
    )