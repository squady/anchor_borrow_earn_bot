from aiogram.types import force_reply, reply_keyboard
from aiogram.types.chat import ChatActions
from aiogram.types.inline_keyboard import InlineKeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types.message import ParseMode
from Observable import Observable
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from action import Action, LTV_TYPE
from helper import Helper
from config import Config


ANCHOR_INFOS = "💱 Anchor infos"
WALLET_INFOS = "👛 Wallet infos"
CHANGE_TARGET_LTV = "✏️ Target LTV 🟢"
CHANGE_MIN_LTV = "✏️ Min LTV 🟠"
CHANGE_MAX_LTV = "✏️ Max LTV 🔴"
CLAIM_REWARDS = "🎁 Claim rewards"
DEPOSIT_AMOUNT = "⬆️ Deposit Amount"
WITHDRAW_AMOUNT = "⬇️ Withdraw Amount"
FETCH_LTV = "🎯 Reach the Target LTV"


class Form(StatesGroup):
    change_target_ltv = State()
    change_min_ltv = State()
    change_max_ltv = State()
    reach_ltv = State()
    claim_rewards = State()
    deposit_amount = State()
    withdraw_amount = State()
    confirm = State()


class Event(Observable):
    def __init__(self):
        Observable.__init__(self)


bot = Bot(token=Config._telegram_token, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
events = Event()

keyboard_main_menu = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
keyboard_main_menu.add(ANCHOR_INFOS, FETCH_LTV, WALLET_INFOS)
keyboard_main_menu.add(CHANGE_MIN_LTV, CHANGE_TARGET_LTV, CHANGE_MAX_LTV)
keyboard_main_menu.add(DEPOSIT_AMOUNT, WITHDRAW_AMOUNT, CLAIM_REWARDS)


@dp.message_handler(commands=["start"])
async def show_start(message: types.Message):
    if message.chat.id == Config._telegram_chat_id:
        await send_message("Hello")
    else:
        await message.answer("You're not allowed to use this bot")


@dp.message_handler(
    lambda message: message.text
    and ANCHOR_INFOS in message.text
    and message.chat.id == Config._telegram_chat_id
)
async def get_borrow_infos(message: types.Message):
    await events.async_set(Action.GET_ANCHOR_INFOS)



@dp.message_handler(
    lambda message: message.text
    and WALLET_INFOS in message.text
    and message.chat.id == Config._telegram_chat_id
)
async def get_wallet_infos(message: types.Message):
    await events.async_set(Action.GET_WALLET_INFOS)


@dp.message_handler(
    lambda message: message.text
    and FETCH_LTV in message.text
    and message.chat.id == Config._telegram_chat_id
)
async def get_wallet_infos(message: types.Message, state: FSMContext):
    await state.set_data({"from": Form.reach_ltv.state})
    await ask_to_confirm(message, state)


@dp.message_handler(
    lambda message: message.text
    and ( (CHANGE_TARGET_LTV == message.text)
        or (CHANGE_MIN_LTV == message.text)
        or (CHANGE_MAX_LTV == message.text) )
    and message.chat.id == Config._telegram_chat_id
)
async def get_change_ltv(message: types.Message, state: FSMContext):
    try:
        form_state = None
        type_ltv = None
        if (CHANGE_MIN_LTV == message.text):
            form_state = Form.change_min_ltv
            type_ltv = LTV_TYPE.MIN
        elif (CHANGE_TARGET_LTV == message.text):
            form_state = Form.change_target_ltv
            type_ltv = LTV_TYPE.TARGET
        elif (CHANGE_MAX_LTV == message.text):
            form_state = Form.change_max_ltv
            type_ltv = LTV_TYPE.MAX

        if (form_state is not None and type_ltv is not None):
            await form_state.set()
            await state.set_data(
                {"from": form_state.state, "type_ltv": type_ltv}
            )
            await message.reply(
                "Please set the new value :",
                reply=True,
                reply_markup=force_reply.ForceReply(),
            )

    except Exception as e:
        Config._log.exception(e)


@dp.message_handler(state=Form.change_target_ltv)
@dp.message_handler(state=Form.change_min_ltv)
@dp.message_handler(state=Form.change_max_ltv)
async def change_min_ltv_callback(message: types.Message, state: FSMContext):
    try:
        await state.reset_state(with_data=False)
        new_ltv = message.text
        if Helper.is_number(new_ltv) == True:
            new_ltv = float(new_ltv)
            if new_ltv > 0 and new_ltv <= Config.MAX_ALLOWED_LTV:
                await state.update_data({"value": new_ltv})
                await ask_to_confirm(message, state)
            else:
                await message.answer(
                    "Wrong value, please specify a LTV between 0 and {}".format(Config.MAX_ALLOWED_LTV),
                    reply_markup=keyboard_main_menu,
                )

        else:
            await message.answer(
                "Wrong value, try again and set a numeric value",
                reply_markup=keyboard_main_menu,
            )

    except Exception as e:
        Config._log.exception(e)


@dp.message_handler(
    lambda message: message.text
    and DEPOSIT_AMOUNT in message.text
    and message.chat.id == Config._telegram_chat_id
)
async def get_deposit_amount(message: types.Message, state: FSMContext):
    try:

        await Form.deposit_amount.set()
        await message.reply(
            "Please set amount to deposit :",
            reply=True,
            reply_markup=force_reply.ForceReply(),
        )

    except Exception as e:
        Config._log.exception(e)


@dp.message_handler(state=Form.deposit_amount)
async def deposit_amount_callback(message: types.Message, state: FSMContext):
    try:
        await state.finish()
        deposit_amount = message.text
        if Helper.is_number(deposit_amount) == True:
            await state.set_data(
                {"from": Form.deposit_amount.state, "amount": deposit_amount}
            )
            await ask_to_confirm(message, state)
        else:
            await message.answer(
                "Wrong value, try again and set a numeric value",
                reply_markup=keyboard_main_menu,
            )

    except Exception as e:
        Config._log.exception(e)

@dp.message_handler(
    lambda message: message.text
    and WITHDRAW_AMOUNT in message.text
    and message.chat.id == Config._telegram_chat_id
)
async def get_withdraw_amount(message: types.Message, state: FSMContext):
    try:

        await Form.withdraw_amount.set()
        await message.reply(
            "Please set amount to withdraw :",
            reply=True,
            reply_markup=force_reply.ForceReply(),
        )

    except Exception as e:
        Config._log.exception(e)


@dp.message_handler(state=Form.withdraw_amount)
async def withdraw_amount_callback(message: types.Message, state: FSMContext):
    try:
        await state.finish()
        withdraw_amount = message.text
        if Helper.is_number(withdraw_amount) == True:
            await state.set_data(
                {"from": Form.withdraw_amount.state, "amount": withdraw_amount}
            )
            await ask_to_confirm(message, state)
        else:
            await message.answer(
                "Wrong value, try again and set a numeric value",
                reply_markup=keyboard_main_menu,
            )

    except Exception as e:
        Config._log.exception(e)



@dp.message_handler(
    lambda message: message.text
    and CLAIM_REWARDS in message.text
    and message.chat.id == Config._telegram_chat_id
)
async def get_claim_rewards(message: types.Message, state: FSMContext):
    try:

        await Form.claim_rewards.set()
        await state.set_data({"from": Form.claim_rewards.state})
        await ask_to_confirm(message, state)

    except Exception as e:
        Config._log.exception(e)


async def ask_to_confirm(message: types.Message, state: FSMContext):

    try:
        keyboard_markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            selective=True,
        )
        keyboard_markup.add(InlineKeyboardButton("yes"), InlineKeyboardButton("no"))

        await Form.confirm.set()
        await message.answer(text="""Are you sure ?""", reply_markup=keyboard_markup)

    except Exception as e:
        Config._log.exception(e)


@dp.message_handler(state=Form.confirm)
async def confirm_callback(message: types.Message, state: FSMContext):
    try:
        datas = await state.get_data()
        await state.finish()
        if message.text == "yes":
            await send_message("ok", False)
            form_from = datas.get("from", None)
            if form_from is not None:
                # FETCH LTV
                if form_from == Form.reach_ltv.state:
                    await events.async_set(Action.FETCH_LTV)
                # CHANGE_LTV
                elif (
                    form_from == Form.change_target_ltv.state
                    or form_from == Form.change_min_ltv.state
                    or form_from == Form.change_max_ltv.state
                ):
                    await events.async_set(
                        Action.CHANGE_LTV,
                        new_ltv=datas.get("value", None),
                        type_ltv=datas.get("type_ltv", None),
                    )
                # CLAIM REWARDS
                elif form_from == Form.claim_rewards.state:
                    await events.async_set(Action.CLAIM_REWARDS)
                # DEPOSIT AMOUNT
                elif form_from == Form.deposit_amount.state:
                    await events.async_set(
                        Action.DEPOSIT_AMOUNT, amount=datas.get("amount", 0)
                    )
                elif form_from == Form.withdraw_amount.state:
                    await events.async_set(
                        Action.WITHDRAW_AMOUNT, amount=datas.get("amount", 0)
                    )
                else:
                    Config._log.error("Error, don't know what was confirmed")
        else:
            await send_message("canceled")

    except Exception as e:
        Config._log.exception(e)


async def start():
    await dp.start_polling()


async def stop():
    if dp.is_polling():
        dp.stop_polling()
    await dp.wait_closed()


async def send_message(message, show_keyboard=True, show_typing=False):
    if Config._telegram_chat_id is not None:
        keyboard = keyboard_main_menu
        if show_keyboard == False:
            keyboard = reply_keyboard.ReplyKeyboardRemove()

        await bot.send_message(Config._telegram_chat_id, message, reply_markup=keyboard)
        if show_typing == True:
            await show_is_typing()


async def show_is_typing():
    if Config._telegram_chat_id is not None:
        await bot.send_chat_action(Config._telegram_chat_id, action=ChatActions.TYPING)
