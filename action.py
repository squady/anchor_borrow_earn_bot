from enum import Enum, auto


class LTV_TYPE(Enum):
    MIN = auto()
    TARGET = auto()
    MAX = auto()


class Action(Enum):
    GET_ANCHOR_INFOS = auto()
    GET_WALLET_INFOS = auto()
    FETCH_LTV = auto()
    CHANGE_LTV = auto()
    CLAIM_REWARDS = auto()
    DEPOSIT_AMOUNT = auto()
    WITHDRAW_AMOUNT = auto()
