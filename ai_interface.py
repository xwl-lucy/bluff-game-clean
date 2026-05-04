import random
from game_logic import Card


class StrategicAI:
    def __init__(self, game, player_idx):
        self.game = game
        self.idx = player_idx

        # AI 对各玩家的信用度判断
        # 分数越低，越容易被 AI 质疑
        self.player_credit = {0: 50, 1: 50, 2: 50, 3: 50}

    def get_action(self):
        """
        AI 决策入口。
        只返回动作，不直接修改游戏状态。

        返回格式：
        1. ('declare', rank, card_indices)
        2. ('play', card_indices)
        3. ('challenge',)
        4. ('pass',)
        """
        hand = self.game.players[self.idx]
        game = self.game

        if not hand:
            return ('pass',)

        total_cards_left = sum(len(p) for p in game.players)
        is_late_game = total_cards_left < 20
        is_desperate = len(hand) <= 3

        # 当前没有叫牌点数，说明 AI 需要先叫牌
        if game.declared_rank is None:
            return self._declare_and_play(hand)

        declared_rank = game.declared_rank

        last_player_idx, _ = game.public_pile[-1] if game.public_pile else (None, None)

        valid_cards_idx = [
            i for i, c in enumerate(hand)
            if c.is_wildcard() or c.rank == declared_rank
        ]

        num_valid = len(valid_cards_idx)
        num_hand = len(hand)

        # 手牌很少时，优先尽快出完
        if is_desperate and num_hand > 0:
            if valid_cards_idx:
                play_indices = valid_cards_idx[:min(2, num_valid)]
            else:
                play_indices = random.sample(range(num_hand), min(2, num_hand))
            return ('play', play_indices)

        # 判断是否质疑上一位玩家
        if last_player_idx is not None and self._should_challenge(last_player_idx, len(game.public_pile)):
            return ('challenge',)

        # 有真实可出的牌：优先出真牌
        if num_valid > 0:
            max_play_count = 3 if is_late_game else 2
            num_to_play = min(num_valid, random.randint(1, max_play_count))
            selected = random.sample(valid_cards_idx, num_to_play)
            return ('play', selected)

        # 没有真牌：考虑是否唬牌
        bluff_chance = 0.15

        if is_late_game:
            bluff_chance += 0.15

        if len(game.public_pile) > 3:
            bluff_chance -= 0.1

        if random.random() < bluff_chance and num_hand > 0:
            num_to_play = min(num_hand, random.randint(1, 2))
            selected = random.sample(range(num_hand), num_to_play)
            return ('play', selected)

        return ('pass',)

    def _declare_and_play(self, hand):
        """
        AI 叫牌并选择要出的牌。
        注意：这里只返回动作，不调用 self.game.start_round()。
        """
        rank_strength = {}
        wildcard_count = 0

        for card in hand:
            if card.is_wildcard():
                wildcard_count += 1
            else:
                rank_strength[card.rank] = rank_strength.get(card.rank, 0) + 1

        # 选择自己手里最有优势的点数
        if rank_strength:
            for rank in rank_strength:
                rank_strength[rank] += wildcard_count
            best_rank = max(rank_strength, key=rank_strength.get)
        else:
            best_rank = random.choice(Card.RANKS)

        valid_real_idx = [
            i for i, c in enumerate(hand)
            if not c.is_wildcard() and c.rank == best_rank
        ]

        valid_wild_idx = [
            i for i, c in enumerate(hand)
            if c.is_wildcard()
        ]

        # 叫牌后优先出一张真实牌，其次出王，最后随便出一张
        if valid_real_idx:
            play_idx = valid_real_idx[:1]
        elif valid_wild_idx:
            play_idx = valid_wild_idx[:1]
        else:
            play_idx = [0] if hand else []

        return ('declare', best_rank, play_idx)

    def _should_challenge(self, target_player_idx, pile_size):
        """
        判断是否质疑某个玩家。
        """
        credit = self.player_credit.get(target_player_idx, 50)
        target_hand_size = len(self.game.players[target_player_idx])

        challenge_prob = 0.1

        # 信用度越低，越容易被质疑
        if credit < 30:
            challenge_prob += 0.4
        elif credit < 50:
            challenge_prob += 0.2

        # 对方快出完时，提高质疑概率
        if target_hand_size <= 2:
            challenge_prob += 0.5
        elif target_hand_size <= 4:
            challenge_prob += 0.2

        # 公共牌堆越大，质疑价值越高
        if pile_size > 4:
            challenge_prob += 0.15

        return random.random() < challenge_prob

    def update_credit_after_challenge(self, loser_idx, was_bluffing):
        """
        根据质疑结果更新玩家信用度。
        """
        if was_bluffing:
            self.player_credit[loser_idx] = max(
                0,
                self.player_credit.get(loser_idx, 50) - 30
            )
        else:
            self.player_credit[loser_idx] = min(
                100,
                self.player_credit.get(loser_idx, 50) + 10
            )