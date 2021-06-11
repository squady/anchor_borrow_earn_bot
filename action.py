from enum import Enum, auto

class TVL_TYPE(Enum):
    MIN = auto()
    TARGET = auto()
    MAX = auto()


class Action(Enum):
    GET_BORROW_INFOS    = auto()
    GET_EARN_INFOS      = auto()
    GET_WALLET_INFOS    = auto()
    FETCH_TVL           = auto()
    CHANGE_TVL          = auto()
    CLAIM_REWARDS       = auto()
    DEPOSIT_AMOUNT      = auto()
