from enum import Enum, auto

class TVL_TYPE(Enum):
    MIN = auto()
    TARGET = auto()
    MAX = auto()

    @staticmethod
    def get_type_from_string(string):
        if (str.lower(string) == "min"):
            return TVL_TYPE.MIN
        elif (str.lower(string) == "max"):
            return TVL_TYPE.MAX
        elif (str.lower(string) == "target"):
            return TVL_TYPE.TARGET

class Action(Enum):
    GET_BORROW_INFOS = auto()
    GET_EARN_INFOS = auto()
    GET_WALLET_INFOS = auto()
    FETCH_TVL = auto()
    CHANGE_TVL = auto()
    CLAIM_REWARDS = auto()
    DEPOSIT_AMOUNT = auto()
    TVL_TOO_LOW = auto()
    TVL_TOO_HIGH = auto()
