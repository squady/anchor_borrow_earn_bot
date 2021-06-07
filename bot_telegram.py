from typing import Text
from aiogram.types import callback_query, force_reply, reply_keyboard
from aiogram.types.chat import ChatActions
from aiogram.types.inline_keyboard import InlineKeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types.message import Message, ParseMode
from Observable import Observable
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiohttp.helpers import content_disposition_header
from action import Action, TVL_TYPE
from helper import Helper
import logging


BORROW_INFOS="🌔 Borrow infos"
EARN_INFOS="🌜 Earn infos"
WALLET_INFOS="👛 Wallet infos"
CHANGE_TARGET_TVL="✏️ Target TVL 🟩..."
CHANGE_MIN_TVL="✏️ Min TVL 🟧..."
CHANGE_MAX_TVL="✏️ Max TVL 🟥..."
CLAIM_REWARDS="Claim rewards"
DEPOSIT_AMOUNT="Deposit Amount..."
FETCH_TVL="🎯 Fetch TVL"


class Form(StatesGroup):
    change_target_tvl = State()
    change_min_tvl = State()
    change_max_tvl = State()
    fetch_tvl = State()
    claim_rewards = State()
    deposit_amount = State()
    confirm = State()

class bot_telegram(Observable):
    bot = None
    owner_chat_id = None
    keyboard_main_menu = None
    def __init__(self, telegram_token, owner_chat_id):
        Observable.__init__(self)

        try:
            self._log = logging.getLogger("borrow_bot")

            bot_telegram.bot = None
            if (telegram_token is not None):
                bot_telegram.bot = Bot(token=telegram_token, parse_mode=ParseMode.HTML)
                bot_telegram.owner_chat_id = owner_chat_id
                self._storage = MemoryStorage()
                bot_telegram.keyboard_main_menu = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
                bot_telegram.keyboard_main_menu.add(BORROW_INFOS, EARN_INFOS, WALLET_INFOS)
                bot_telegram.keyboard_main_menu.add(CHANGE_MIN_TVL, CHANGE_TARGET_TVL, CHANGE_MAX_TVL)
                bot_telegram.keyboard_main_menu.row(FETCH_TVL, DEPOSIT_AMOUNT, CLAIM_REWARDS)
        except Exception as e:
            self._log.exception(e)


    async def start(self):
        try:
            if (bot_telegram.bot is not None):
                self._disp = Dispatcher(bot=bot_telegram.bot, storage=self._storage)
                self._disp.register_message_handler(self.start_handler, state="*")
                await self._disp.start_polling()
        except Exception as e:
            self._log.exception(e)

    async def stop(self):

        try:
            if (self._disp is not None):
                self._log.info("stop bot")                
                self._disp.stop_polling()
                bot_telegram.bot = None
        except Exception as e:
            self._log.exception(e)

    async def start_handler(self, event: types.Message, state: FSMContext):
        try:
            state_name = await state.get_state()

            if (event.chat.id == bot_telegram.owner_chat_id):
                if (state_name is not None):
                    if (state_name == Form.change_target_tvl.state):
                        await self.change_tvl_callback(event, state)
                    elif (state_name == Form.claim_rewards.state):
                        await self.claim_rewards_callback(event, state)
                    elif (state_name == Form.deposit_amount.state):
                        await self.deposit_amount_callback(event, state)
                    elif (state_name == Form.confirm.state):
                        await self.confirm_callback(event, state)
                elif (event.content_type == "text"):
                    if (event.text == "/start"):
                        return await bot_telegram.send_message("Hello")
                    elif (event.text == BORROW_INFOS):
                        return await self.get_borrow_infos()
                    elif (event.text == EARN_INFOS):
                        return await self.get_earn_infos()
                    elif (event.text == WALLET_INFOS):
                        return await self.get_wallet_infos()
                    elif (event.text == FETCH_TVL):
                        return await self.fetch_tvl(event, state)
                    elif (event.text == CHANGE_TARGET_TVL):
                        return await self.change_tvl(event, state, TVL_TYPE.TARGET, Form.change_target_tvl.state)
                    elif (event.text == CHANGE_MIN_TVL):
                        return await self.change_tvl(event, state, TVL_TYPE.MIN, Form.change_min_tvl.state)
                    elif (event.text == CHANGE_MAX_TVL):
                        return await self.change_tvl(event, state, TVL_TYPE.MAX, Form.change_max_tvl.state)
                    elif (event.text == CLAIM_REWARDS):
                        return await self.claim_rewards(event, state)
                    elif (event.text == DEPOSIT_AMOUNT):
                        return await self.deposit_amount(event, state)
                    else:
                        await event.answer(
                            text="commande inconnue, tapez /start pour commencer", reply_markup=bot_telegram.keyboard_main_menu)
            else:
                await event.answer(
                    text="You're not allowed to use the bot")


        except Exception as e:
            self._log.exception(e)


    async def get_borrow_infos(self):

        await self.async_set(Action.GET_BORROW_INFOS)

    async def get_earn_infos(self):

        await self.async_set(Action.GET_EARN_INFOS)

    async def get_wallet_infos(self):

        await self.async_set(Action.GET_WALLET_INFOS)

    async def fetch_tvl(self,message: types.Message, state: FSMContext):

        await state.set_data({"from":Form.fetch_tvl.state})
        await self.ask_to_confirm(message, state)


    async def change_tvl(self,message: types.Message, state: FSMContext, type_tvl: TVL_TYPE, from_state: str):

        try:

            await Form.change_target_tvl.set()                
            await state.set_data({"from":from_state, "type_tvl":type_tvl})
                    
            fr_markeup = force_reply.ForceReply()
            await message.reply("Please set the new value :", reply=True, reply_markup=fr_markeup)

        except Exception as e:
            self._log.exception(e)


    async def change_tvl_callback(self, message: types.Message, state: FSMContext):
        try:
            await state.reset_state(with_data=False)
            new_tvl = message.text
            if (Helper.is_number(new_tvl) == True):
                new_tvl = float(new_tvl)
                if (new_tvl > 0 and new_tvl <= 45):
                    await state.update_data({"value":new_tvl})
                    await self.ask_to_confirm(message, state)
                else:
                    await message.answer("Wrong value, please specify a TVL between 0 and 45",reply_markup=bot_telegram.keyboard_main_menu)

            else:
                await message.answer("Wrong value, try again and set a numeric value",reply_markup=bot_telegram.keyboard_main_menu)

        except Exception as e:
            self._log.exception(e)

    async def claim_rewards(self,message: types.Message, state: FSMContext):
        try:

            await Form.claim_rewards.set()    
            await state.set_data({"from":Form.claim_rewards.state})
            await self.ask_to_confirm(message, state)

        except Exception as e:
            self._log.exception(e)

    async def deposit_amount(self,message: types.Message, state: FSMContext):
        try:

            await Form.deposit_amount.set()    

            fr_markeup = force_reply.ForceReply()
            await message.reply("Please set amount to deposit :", reply=True, reply_markup=fr_markeup)

        except Exception as e:
            self._log.exception(e)


    async def deposit_amount_callback(self, message: types.Message, state: FSMContext):
        try:
            await state.finish()
            deposit_amount = message.text
            if (Helper.is_number(deposit_amount) == True):
                await state.set_data({"from":Form.deposit_amount.state, "amount": deposit_amount})
                await self.ask_to_confirm(message, state)
            else:
                await message.answer("Wrong value, try again and set a numeric value",reply_markup=bot_telegram.keyboard_main_menu)

        except Exception as e:
            self._log.exception(e)
                 


    async def ask_to_confirm(self, message: types.Message, state: FSMContext):

        try:
            keyboard_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            keyboard_markup.add( InlineKeyboardButton("yes"), InlineKeyboardButton("no"))

            await Form.confirm.set()            
            await message.answer(text="""Are you sure ?""", reply_markup=keyboard_markup)

        except Exception as e:
            self._log.exception(e)


    async def confirm_callback(self, message: types.Message, state: FSMContext):
        try:
            datas = await state.get_data()
            await state.finish()
            if (message.text == "yes"):                
                await bot_telegram.send_message("ok", False)
                form_from = datas.get("from", None)
                if (form_from is not None):
                    # FETCH TVL
                    if (form_from == Form.fetch_tvl.state):
                        await self.async_set(Action.FETCH_TVL)
                    # CHANGE_TVL
                    elif (form_from == Form.change_target_tvl.state or
                            form_from == Form.change_min_tvl.state or
                            form_from == Form.change_max_tvl.state):
                        await self.async_set(Action.CHANGE_TVL, 
                                    new_tvl=datas.get("value", None), 
                                    type_tvl=datas.get("type_tvl", None))
                    # CLAIM REWARDS
                    elif (form_from == Form.claim_rewards.state):
                        await self.async_set(Action.CLAIM_REWARDS)                    
                    # DEPOSIT AMOUNT
                    elif (form_from == Form.deposit_amount.state):
                        await self.async_set(Action.DEPOSIT_AMOUNT, amount=datas.get("amount", 0))
                    else:
                        self._log.error("Error, don't know what was confirmed")
            else:
                await bot_telegram.send_message("canceled")


        except Exception as e:
            self._log.exception(e)
            


    async def send_message(message, show_keyboard=True, show_typing=False):
        if (bot_telegram.bot is not None and 
                bot_telegram.owner_chat_id is not None and
                bot_telegram.keyboard_main_menu is not None):

            if (show_keyboard == True):
                await bot_telegram.bot.send_message(bot_telegram.owner_chat_id, message, reply_markup=bot_telegram.keyboard_main_menu)
            else:
                # bot_telegram.bot.send_message()
                await bot_telegram.bot.send_message(bot_telegram.owner_chat_id, message, reply_markup=reply_keyboard.ReplyKeyboardRemove())

            if (show_typing == True):
                await bot_telegram.show_is_typing()

    async def show_is_typing():
        await bot_telegram.bot.send_chat_action(bot_telegram.owner_chat_id, action=ChatActions.TYPING)