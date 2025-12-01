from telegram import KeyboardButton, ReplyKeyboardMarkup

# Regular menu (without contact request)
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

# Initial menu with contact request button
initial_menu_keyboard = [
    [
        KeyboardButton("📞 Share Contact", request_contact=True)
    ]
]

# Menu after contact is shared (games unlocked)
unlocked_menu_keyboard = [
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

regular_menu_markup = ReplyKeyboardMarkup(regular_menu_keyboard, resize_keyboard=True)
initial_menu_markup = ReplyKeyboardMarkup(initial_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
unlocked_menu_markup = ReplyKeyboardMarkup(unlocked_menu_keyboard, resize_keyboard=True)