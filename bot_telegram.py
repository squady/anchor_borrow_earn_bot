from aiogram.types import  force_reply, reply_keyboard
from aiogram.types.chat import ChatActions
from aiogram.types.inline_keyboard import InlineKeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types.message import  ParseMode
from Observable import Observable
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from action import Action, TVL_TYPE
from helper import Helper
from config import Config



BORROW_INFOS="💱 Borrow infos"
EARN_INFOS="💰 Earn infos"
WALLET_INFOS="👛 Wallet infos"
CHANGE_TARGET_TVL="✏️ Target TVL 🟩"
CHANGE_MIN_TVL="✏️ Min TVL 🟧"
CHANGE_MAX_TVL="✏️ Max TVL 🟥"
CLAIM_REWARDS="🎁 Claim rewards"
DEPOSIT_AMOUNT="💵 Deposit Amount"
FETCH_TVL="🎯 Reach the Target TVL"


class Form(StatesGroup):
    change_target_tvl = State()
    change_min_tvl = State()
    change_max_tvl = State()
    reach_tvl = State()
    claim_rewards = State()
    deposit_amount = State()
    confirm = State()


class Event(Observable):
    def __init__(self):
        Observable.__init__(self)
    

bot = Bot(token=Config._telegram_token, parse_mode=ParseMode.HTML)
keyboard_main_menu = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
keyboard_main_menu.add(BORROW_INFOS, EARN_INFOS, WALLET_INFOS)
keyboard_main_menu.add(CHANGE_MIN_TVL, CHANGE_TARGET_TVL, CHANGE_MAX_TVL)
keyboard_main_menu.add(FETCH_TVL, DEPOSIT_AMOUNT, CLAIM_REWARDS)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
events = Event()



@dp.message_handler(commands=['start'])
async def show_start(message: types.Message):
    if (message.chat.id == Config._telegram_chat_id):
        await send_message("Hello")
    else:
        await message.answer("You're not allowed to use this bot")


@dp.message_handler(lambda message: message.text and BORROW_INFOS in message.text and message.chat.id == Config._telegram_chat_id)
async def get_borrow_infos(message: types.Message):
    await events.async_set(Action.GET_BORROW_INFOS)

@dp.message_handler(lambda message: message.text and EARN_INFOS in message.text and message.chat.id == Config._telegram_chat_id)
async def get_earn_infos(message: types.Message):
    await events.async_set(Action.GET_EARN_INFOS)

@dp.message_handler(lambda message: message.text and WALLET_INFOS in message.text and message.chat.id == Config._telegram_chat_id)
async def get_wallet_infos(message: types.Message):
    await events.async_set(Action.GET_WALLET_INFOS)

@dp.message_handler(lambda message: message.text and FETCH_TVL in message.text and message.chat.id == Config._telegram_chat_id)
async def get_wallet_infos(message: types.Message, state: FSMContext):
    await state.set_data({"from":Form.reach_tvl.state})
    await ask_to_confirm(message, state)


@dp.message_handler(lambda message: message.text and CHANGE_TARGET_TVL in message.text and message.chat.id == Config._telegram_chat_id)
async def get_change_target_tvl(message: types.Message, state: FSMContext):
    try:

        await Form.change_target_tvl.set()                
        await state.set_data({"from":Form.change_target_tvl.state, "type_tvl":TVL_TYPE.TARGET})
                
        fr_markeup = force_reply.ForceReply()
        await message.reply("Please set the new value :", reply=True, reply_markup=fr_markeup)

    except Exception as e:
        Config._log.exception(e)

@dp.message_handler(lambda message: message.text and CHANGE_MIN_TVL in message.text and message.chat.id == Config._telegram_chat_id)
async def get_change_min_tvl(message: types.Message, state: FSMContext):
    try:

        await Form.change_min_tvl.set()                
        await state.set_data({"from":Form.change_min_tvl.state, "type_tvl":TVL_TYPE.MIN})
                
        fr_markeup = force_reply.ForceReply()
        await message.reply("Please set the new value :", reply=True, reply_markup=fr_markeup)

    except Exception as e:
        Config._log.exception(e)

@dp.message_handler(lambda message: message.text and CHANGE_MAX_TVL in message.text and message.chat.id == Config._telegram_chat_id)
async def get_change_max_tvl(message: types.Message, state: FSMContext):
    try:

        await Form.change_max_tvl.set()                
        await state.set_data({"from":Form.change_max_tvl.state, "type_tvl":TVL_TYPE.MAX})
                
        fr_markeup = force_reply.ForceReply()
        await message.reply("Please set the new value :", reply=True, reply_markup=fr_markeup)

    except Exception as e:
        Config._log.exception(e)        

@dp.message_handler(state=Form.change_target_tvl)
@dp.message_handler(state=Form.change_min_tvl)
@dp.message_handler(state=Form.change_max_tvl)
async def change_min_tvl_callback(message: types.Message, state: FSMContext):
    try:
        await state.reset_state(with_data=False)
        new_tvl = message.text
        if (Helper.is_number(new_tvl) == True):
            new_tvl = float(new_tvl)
            if (new_tvl > 0 and new_tvl <= 45):
                await state.update_data({"value":new_tvl})
                await ask_to_confirm(message, state)
            else:
                await message.answer("Wrong value, please specify a TVL between 0 and 45",reply_markup=keyboard_main_menu)

        else:
            await message.answer("Wrong value, try again and set a numeric value",reply_markup=keyboard_main_menu)

    except Exception as e:
        Config._log.exception(e)



@dp.message_handler(lambda message: message.text and DEPOSIT_AMOUNT in message.text and message.chat.id == Config._telegram_chat_id)
async def get_deposit_amount(message: types.Message, state: FSMContext):
    try:

        await Form.deposit_amount.set()    

        fr_markeup = force_reply.ForceReply()
        await message.reply("Please set amount to deposit :", reply=True, reply_markup=fr_markeup)

    except Exception as e:
        Config._log.exception(e)    
    
    
@dp.message_handler(state=Form.deposit_amount)
async def deposit_amount_callback(message: types.Message, state: FSMContext):    
    try:
        await state.finish()
        deposit_amount = message.text
        if (Helper.is_number(deposit_amount) == True):
            await state.set_data({"from":Form.deposit_amount.state, "amount": deposit_amount})
            await ask_to_confirm(message, state)
        else:
            await message.answer("Wrong value, try again and set a numeric value",reply_markup=keyboard_main_menu)

    except Exception as e:
        Config._log.exception(e)          

@dp.message_handler(lambda message: message.text and CLAIM_REWARDS in message.text and message.chat.id == Config._telegram_chat_id)
async def get_claim_rewards(message: types.Message, state: FSMContext):
    try:

        await Form.claim_rewards.set()    
        await state.set_data({"from":Form.claim_rewards.state})
        await ask_to_confirm(message, state)

    except Exception as e:
        Config._log.exception(e)





async def ask_to_confirm(message: types.Message, state: FSMContext):

    try:
        keyboard_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
        keyboard_markup.add( InlineKeyboardButton("yes"), InlineKeyboardButton("no"))

        await Form.confirm.set()            
        await message.answer(text="""Are you sure ?""", reply_markup=keyboard_markup)

    except Exception as e:
        Config._log.exception(e)

@dp.message_handler(state=Form.confirm)
async def confirm_callback(message: types.Message, state: FSMContext):
    try:
        datas = await state.get_data()
        await state.finish()
        if (message.text == "yes"):                
            await send_message("ok", False)
            form_from = datas.get("from", None)
            if (form_from is not None):
                # FETCH TVL
                if (form_from == Form.reach_tvl.state):
                    await events.async_set(Action.FETCH_TVL)
                # CHANGE_TVL
                elif (form_from == Form.change_target_tvl.state or
                        form_from == Form.change_min_tvl.state or
                        form_from == Form.change_max_tvl.state):
                    await events.async_set(Action.CHANGE_TVL, 
                                new_tvl=datas.get("value", None), 
                                type_tvl=datas.get("type_tvl", None))
                # CLAIM REWARDS
                elif (form_from == Form.claim_rewards.state):
                    await events.async_set(Action.CLAIM_REWARDS)                    
                # DEPOSIT AMOUNT
                elif (form_from == Form.deposit_amount.state):
                    await events.async_set(Action.DEPOSIT_AMOUNT, amount=datas.get("amount", 0))
                else:
                    Config._log.error("Error, don't know what was confirmed")
        else:
            await send_message("canceled")

    except Exception as e:
        Config._log.exception(e)

async def start():
    await dp.start_polling()

async def stop():
    if (dp.is_polling()):
        dp.stop_polling()
    await dp.wait_closed()


async def send_message(message, show_keyboard=True, show_typing=False):
    if (Config._telegram_chat_id is not None):
        keyboard = keyboard_main_menu
        if (show_keyboard == False):
            keyboard = reply_keyboard.ReplyKeyboardRemove()

        await bot.send_message(Config._telegram_chat_id, message, reply_markup=keyboard)
        if (show_typing == True):
            await show_is_typing()


async def show_is_typing():
    if (Config._telegram_chat_id is not None):
        await bot.send_chat_action(Config._telegram_chat_id, action=ChatActions.TYPING)


