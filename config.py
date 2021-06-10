import os
import sys
import logging
import base64
from helper import Helper


class Config:
    _log = logging.getLogger("anchor_borrow")
    formatter = logging.Formatter('%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                                    datefmt='%Y-%m-%d:%H:%M:%S')
    _log.setLevel(logging.INFO)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    _log.addHandler(console_handler)

    _wallet_name = os.environ.get("WALLET_NAME", "Wallet#1")
    _mnemonic = base64.b64decode(os.environ.get("WALLET_MNEMONIC")).decode("utf-8")
    _telegram_token = os.environ.get("TELEGRAM_TOKEN", None)
    _telegram_chat_id = int(os.environ.get("TELEGRAM_CHAT_ID", 0))
    _anchor_mmMarket = os.environ.get("ANCHOR_mmMarket", "terra15dwd5mj8v59wpj0wvt233mf5efdff808c5tkal")
    _target_tvl = float(os.environ.get("TARGET_TVL", 35))
    _min_tvl = float(os.environ.get("MIN_TVL", 30))
    _max_tvl = float(os.environ.get("MAX_TVL", 40))
    _chain_id = os.environ.get("CHAIN_ID", "tequila-0004")
    _chain_url = os.environ.get("CHAIN_URL", "https://tequila-lcd.terra.dev")
    _minimum_ust_amount = int(os.environ.get("UST_MIN_AMOUNT_ALERT", 2))


    _address = {}
    _address["mmMarket"] = os.environ.get("ANCHOR_mmMarket", "terra15dwd5mj8v59wpj0wvt233mf5efdff808c5tkal")
    _address["mantle_endpoint"] = os.environ.get("Mantle_endpoint", "https://tequila-mantle.anchorprotocol.com")

    BLOCKS_PER_YEAR = 4906443
    
    _log.info("===========================================")
    _log.info("wallet_name = {}".format(_wallet_name))
    _log.info("chain_id = {}".format(_chain_id))
    _log.info("chain_url = {}".format(_chain_url))
    _log.info("telegram token = {}".format(_telegram_token))
    _log.info("telegram chat_id = {}".format(_telegram_chat_id))
    _log.info("MIN TVL = {}".format(_min_tvl))
    _log.info("Target TVL = {}".format(_target_tvl))
    _log.info("MAX TVL = {}".format(_max_tvl))
    _log.info("Min UST Alert = {}".format(_minimum_ust_amount))
    _log.info("===========================================")