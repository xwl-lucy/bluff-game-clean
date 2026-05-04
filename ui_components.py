from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parent
POKER_DIR = PROJECT_ROOT / "static" / "poker"


def _norm(text) -> str:
    text = str(text or "").lower()
    text = text.replace("♥", "hearts")
    text = text.replace("红桃", "hearts")
    text = text.replace("heart", "hearts")

    text = text.replace("♦", "diamonds")
    text = text.replace("方块", "diamonds")
    text = text.replace("diamond", "diamonds")

    text = text.replace("♣", "clubs")
    text = text.replace("梅花", "clubs")
    text = text.replace("club", "clubs")

    text = text.replace("♠", "spades")
    text = text.replace("黑桃", "spades")
    text = text.replace("spade", "spades")

    return re.sub(r"[^a-z0-9]+", "", text)


def _available_poker_files():
    if not POKER_DIR.exists():
        return []

    return [
        p for p in POKER_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]
    ]


def _file_url(path: Path) -> str:
    return f"/app/static/poker/{path.name}"


def _card_rank(card) -> str:
    return str(getattr(card, "rank", "") or "")


def _card_suit(card) -> str:
    return str(getattr(card, "suit", "") or "")


def _rank_aliases(rank: str) -> list[str]:
    rank = str(rank or "").strip()

    aliases = {
        "A": ["a", "ace", "1"],
        "J": ["j", "jack"],
        "Q": ["q", "queen"],
        "K": ["k", "king"],
        "10": ["10", "t"],
        "小王": ["joker", "smalljoker", "blackjoker", "jokerblack"],
        "大王": ["joker", "bigjoker", "redjoker", "jokerred"],
        "JOKER": ["joker"],
        "joker": ["joker"],
    }

    if rank in aliases:
        return [_norm(x) for x in aliases[rank]]

    return [_norm(rank)]


def _suit_aliases(suit: str) -> list[str]:
    suit = str(suit or "").strip().lower()

    mapping = {
        "hearts": ["hearts", "heart", "h", "red", "hongtao"],
        "heart": ["hearts", "heart", "h", "red", "hongtao"],
        "红桃": ["hearts", "heart", "h", "red", "hongtao"],
        "♥": ["hearts", "heart", "h", "red", "hongtao"],

        "diamonds": ["diamonds", "diamond", "d", "red", "fangkuai"],
        "diamond": ["diamonds", "diamond", "d", "red", "fangkuai"],
        "方块": ["diamonds", "diamond", "d", "red", "fangkuai"],
        "♦": ["diamonds", "diamond", "d", "red", "fangkuai"],

        "clubs": ["clubs", "club", "c", "black", "meihua"],
        "club": ["clubs", "club", "c", "black", "meihua"],
        "梅花": ["clubs", "club", "c", "black", "meihua"],
        "♣": ["clubs", "club", "c", "black", "meihua"],

        "spades": ["spades", "spade", "s", "black", "heitao"],
        "spade": ["spades", "spade", "s", "black", "heitao"],
        "黑桃": ["spades", "spade", "s", "black", "heitao"],
        "♠": ["spades", "spade", "s", "black", "heitao"],
    }

    return [_norm(x) for x in mapping.get(suit, [suit])]


def get_card_path(card) -> str:
    """
    根据 Card 对象返回静态图片路径。

    优先匹配 static/poker/ 里的真实文件名。
    找不到时回退到 pokerback.png，避免前端出现破图。
    """
    files = _available_poker_files()

    if not files:
        return "/app/static/poker/pokerback.png"

    rank = _card_rank(card)
    suit = _card_suit(card)

    rank_norms = _rank_aliases(rank)
    suit_norms = _suit_aliases(suit)

    # 1. 先处理 Joker
    if any("joker" in r for r in rank_norms):
        joker_files = [p for p in files if "joker" in _norm(p.stem)]
        if joker_files:
            # 大王优先 red，小王优先 black
            rank_text = _norm(rank)
            if "big" in rank_text or "red" in rank_text or "大王" in str(rank):
                for p in joker_files:
                    if "red" in _norm(p.stem):
                        return _file_url(p)

            if "small" in rank_text or "black" in rank_text or "小王" in str(rank):
                for p in joker_files:
                    if "black" in _norm(p.stem):
                        return _file_url(p)

            return _file_url(joker_files[0])

    # 2. 精确组合匹配
    candidates = []

    for r in rank_norms:
        for s in suit_norms:
            candidates.extend([
                f"{r}{s}",
                f"{s}{r}",
                f"{r}of{s}",
                f"{r}_{s}",
                f"{s}_{r}",
            ])

    normalized_files = {p: _norm(p.stem) for p in files}

    for p, n in normalized_files.items():
        if n in candidates:
            return _file_url(p)

    # 3. 包含 rank + suit 的宽松匹配
    for p, n in normalized_files.items():
        rank_hit = any(r and r in n for r in rank_norms)
        suit_hit = any(s and s in n for s in suit_norms)

        if rank_hit and suit_hit:
            return _file_url(p)

    # 4. 再宽松：只匹配 rank
    for p, n in normalized_files.items():
        rank_hit = any(r and r in n for r in rank_norms)

        if rank_hit:
            return _file_url(p)

    return "/app/static/poker/pokerback.png"


def get_card_back_path() -> str:
    return "/app/static/poker/pokerback.png"


def get_background_path() -> str:
    return "/app/static/background/back.png"