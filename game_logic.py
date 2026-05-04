import random


class Card:
    SUITS = ['♠', '♥', '♣', '♦']
    RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    WILDCARDS = ['小王', '大王']

    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank

    def is_wildcard(self):
        return self.rank in self.WILDCARDS


class BluffGame:
    def __init__(self):
        self.players = [[], [], [], []]
        self.current_player = 0

        # 当前轮声明的点数
        self.declared_rank = None

        # 公共牌堆，结构为：
        # [(玩家编号, [Card, Card]), ...]
        self.public_pile = []

        # 当前轮胜者
        self.round_winner = None

        # 整局游戏胜者
        self.game_winner = None

        # 最近动作描述
        self.last_action = ""

        # 质疑结果回调：
        # (失败者编号, 是否确实唬牌)
        self.challenge_callback = None

        # 连续过牌次数
        self.pass_count = 0

        # 最后一次成功出牌的玩家
        self.last_play_player = None

        self._deal_cards()

    def _deal_cards(self):
        """初始化并发牌"""
        deck = [Card(suit, rank) for suit in Card.SUITS for rank in Card.RANKS]
        deck += [Card('', '小王'), Card('', '大王')]

        random.shuffle(deck)

        for i, card in enumerate(deck):
            self.players[i % 4].append(card)

        for p in self.players:
            p.sort(
                key=lambda c: (
                    c.is_wildcard(),
                    Card.RANKS.index(c.rank) if not c.is_wildcard() else 99
                )
            )

        self.current_player = random.randint(0, 3)

    def start_round(self, rank):
        """开始一轮叫牌"""
        if self.declared_rank is not None:
            return False

        self.declared_rank = rank
        self.public_pile = []
        self.round_winner = None
        self.pass_count = 0
        self.last_play_player = None
        self.last_action = f"本轮叫牌点数为 {rank}"

        return True

    def play_cards(self, card_indices):
        """
        当前玩家出牌。
        出牌成功后，如果无人获胜，则自动切换到下一位玩家。
        """
        if self.game_winner is not None:
            return False

        player_hand = self.players[self.current_player]

        # 1. 出牌不能为空
        if not card_indices:
            return False

        # 2. 去重并倒序，防止删除手牌时索引错位
        card_indices = sorted(set(card_indices), reverse=True)

        # 3. 校验索引是否合法，防止程序崩溃
        if any(i < 0 or i >= len(player_hand) for i in card_indices):
            return False

        # 4. 取出要出的牌
        cards_to_play = [player_hand[i] for i in card_indices]

        # 5. 从当前玩家手牌中删除
        for i in card_indices:
            del player_hand[i]

        # 6. 放入公共牌堆
        acting_player = self.current_player
        self.public_pile.append((acting_player, cards_to_play))

        # 7. 记录最后出牌玩家
        self.last_play_player = acting_player

        # 8. 只要有人出牌，连续过牌次数清零
        self.pass_count = 0

        self.last_action = f"玩家 {acting_player} 打出了 {len(cards_to_play)} 张牌"

        # 9. 检查当前玩家是否已经出完牌获胜
        self._check_immediate_win()

        # 10. 如果没有人获胜，则自动切换到下一位玩家
        if self.game_winner is None:
            self._next_turn()

        return True

    def challenge(self):
        """当前玩家质疑上一位出牌玩家"""
        if self.game_winner is not None:
            return False

        if not self.public_pile:
            return False

        if self.declared_rank is None:
            return False

        challenger_idx = self.current_player
        last_player_idx, last_cards = self.public_pile[-1]

        is_bluff = False

        for card in last_cards:
            if not card.is_wildcard() and card.rank != self.declared_rank:
                is_bluff = True
                break

        all_cards = []
        for _, cards in self.public_pile:
            all_cards.extend(cards)

        if is_bluff:
            # 质疑成功：上一位出牌玩家拿走公共牌堆
            self.players[last_player_idx].extend(all_cards)
            self._sort_player_hand(last_player_idx)

            self.round_winner = challenger_idx
            self.challenge_callback = (last_player_idx, True)
            self.last_action = f"玩家 {challenger_idx} 质疑成功，玩家 {last_player_idx} 拿走公共牌堆"
        else:
            # 质疑失败：质疑者拿走公共牌堆
            self.players[challenger_idx].extend(all_cards)
            self._sort_player_hand(challenger_idx)

            self.round_winner = last_player_idx
            self.challenge_callback = (challenger_idx, False)
            self.last_action = f"玩家 {challenger_idx} 质疑失败，自己拿走公共牌堆"

        self._end_round()
        return True

    def pass_turn(self):
        """
        当前玩家过牌。

        规则：
        1. 必须已经有人叫牌；
        2. 必须公共牌堆里已经有人出过牌；
        3. 如果一名玩家出牌后，其余 3 名玩家连续过牌，则本轮结束；
        4. 本轮结束后，最后出牌者成为下一轮先手。
        """
        if self.game_winner is not None:
            return False

        if self.declared_rank is None:
            return False

        if not self.public_pile:
            return False

        if self.last_play_player is None:
            return False

        passing_player = self.current_player
        self.pass_count += 1
        self.last_action = f"玩家 {passing_player} 选择过牌"

        # 4人局：最后出牌者之外的其他 3 人都过牌，则本轮结束
        required_passes_to_end_round = len(self.players) - 1

        if self.pass_count >= required_passes_to_end_round:
            self.round_winner = self.last_play_player
            self.last_action = (
                f"连续 {self.pass_count} 人过牌，本轮结束。"
                f"玩家 {self.last_play_player} 成为下一轮先手"
            )
            self._end_round()
            return True

        self._next_turn()
        return True

    def _next_turn(self):
        """切换到下一位玩家"""
        self.current_player = (self.current_player + 1) % 4

    def _end_round(self):
        """
        结束当前轮次。

        结束方式包括：
        1. 质疑后结束；
        2. 连续过牌后结束。
        """
        self.public_pile = []
        self.declared_rank = None
        self.pass_count = 0
        self.last_play_player = None

        if self.round_winner is not None:
            self.current_player = self.round_winner

    def _check_immediate_win(self):
        """检查当前玩家是否已经出完所有手牌"""
        if len(self.players[self.current_player]) == 0:
            self.game_winner = self.current_player

    def _sort_player_hand(self, player_idx):
        """整理指定玩家手牌"""
        self.players[player_idx].sort(
            key=lambda c: (
                c.is_wildcard(),
                Card.RANKS.index(c.rank) if not c.is_wildcard() else 99
            )
        )