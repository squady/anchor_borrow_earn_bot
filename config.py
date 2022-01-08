import os
import sys
import logging
import base64
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")


class Config:
    VERSION = "2.0.7"
    _log = logging.getLogger("anchor_borrow")
    formatter = logging.Formatter(
        "%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d:%H:%M:%S",
    )
    _log.setLevel(logging.INFO)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    _log.addHandler(console_handler)

    _wallet_name = os.environ.get("WALLET_NAME", "Wallet#1")
    _mnemonic = base64.b64decode(os.environ.get("WALLET_MNEMONIC")).decode("utf-8")
    _telegram_token = os.environ.get("TELEGRAM_TOKEN", None)
    _telegram_chat_id = int(os.environ.get("TELEGRAM_CHAT_ID", 0))
    _target_ltv = float(os.environ.get("TARGET_TVL", 35))
    _min_ltv = float(os.environ.get("MIN_TVL", 30))
    _max_ltv = float(os.environ.get("MAX_TVL", 40))
    _chain_id = os.environ.get("CHAIN_ID", "bombay-12")
    _chain_url = os.environ.get("CHAIN_URL", "https://bombay-lcd.terra.dev")
    _minimum_ust_amount = int(os.environ.get("UST_MIN_AMOUNT_ALERT", 2))
    _maximum_ltv_allowed = 100/60
    _address = {}
    _address["mmCustody"] = os.environ.get(
        "ANCHOR_mmCustody",
        "terra1ltnkx0mv7lf2rca9f8w740ashu93ujughy4s7p",
    )    
    _address["mantle_endpoint"] = os.environ.get(
        "Mantle_endpoint",
        "https://bombay-mantle.terra.dev",
    )

    BLOCKS_PER_YEAR = 4656810
    CLAIM_FEES = 0.762
    FORCED_FEES = 1
    MAX_ALLOWED_LTV = 60
    _finder_base_url = "https://finder.terra.money"

    _log.info("===========================================")
    _log.info("wallet_name = {}".format(_wallet_name))
    _log.info("chain_id = {}".format(_chain_id))
    _log.info("chain_url = {}".format(_chain_url))
    _log.info("telegram token = {}".format(_telegram_token))
    _log.info("telegram chat_id = {}".format(_telegram_chat_id))
    _log.info("MIN LTV = {}".format(_min_ltv))
    _log.info("Target LTV = {}".format(_target_ltv))
    _log.info("MAX LTV = {}".format(_max_ltv))
    _log.info("Min UST Alert = {}".format(_minimum_ust_amount))
    _log.info("===========================================")
