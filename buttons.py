# buttons.py
from telegram import KeyboardButton, ReplyKeyboardMarkup

# Regular menu (without contact request) - for users who haven't shared contact
regular_menu_keyboard = [
    [
        KeyboardButton("👤 Account"), KeyboardButton("🎮 Play")
    ],
    [
        KeyboardButton("✉️ Invite"), KeyboardButton("👥🏅 Refferal Leaderboard")
    ],
    [
        KeyboardButton("📜Terms & Conditions"), KeyboardButton("⚙️ Settings")
    ]
]

# Initial menu with contact request button and skip option
initial_menu_keyboard = [
    [
        KeyboardButton("📞 Share Contact", request_contact=True)
    ]
]

# Menu after contact is shared (all features unlocked)
unlocked_menu_keyboard = [
    [
        KeyboardButton("👤 Account"), KeyboardButton("🎮 Play")
    ],
    [
        KeyboardButton("✉️ Invite"), KeyboardButton("👥🏅 Leaderboard")
    ],
    [
        KeyboardButton("📜Terms & Conditions"), KeyboardButton("⚙️ Settings")
    ]
]

regular_menu_markup = ReplyKeyboardMarkup(regular_menu_keyboard)
initial_menu_markup = ReplyKeyboardMarkup(initial_menu_keyboard)
unlocked_menu_markup = ReplyKeyboardMarkup(unlocked_menu_keyboard)