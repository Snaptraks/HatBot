from enum import Enum


# Create an Enum with all the letters of the alphabet as emojis
Alphabet = Enum(
    'Alphabet',
    {
        chr(char): chr(emoji) for char, emoji in zip(
            range(ord('A'), ord('Z') + 1),
            range(0x1F1E6, 0x1F200)  # :regional_indicator_#:
            )
        }
    )


class Numbers(Enum):
    _0 = '\u0030\u20e3'  # :zero:
    _1 = '\u0031\u20e3'  # :one:
    _2 = '\u0032\u20e3'  # :two:
    _3 = '\u0033\u20e3'  # :three:
    _4 = '\u0034\u20e3'  # :four:
    _5 = '\u0035\u20e3'  # :five:
    _6 = '\u0036\u20e3'  # :six:
    _7 = '\u0037\u20e3'  # :seven:
    _8 = '\u0038\u20e3'  # :eight
    _9 = '\u0039\u20e3'  # :nine:
    _10 = '\U0001F51F'  # :keycap_ten:


class Controls(Enum):
    CANCEL = '\U0000274C'  # :x:


class Hangman(Enum):
    BLACK = '\U00002B1B'  # :black_large_square:
    DIZZY_FACE = '\U0001F635'  # :dizzy_face:
    SHIRT = '\U0001F455'  # :shirt:
    POINT_LEFT = '\U0001F448'  # :point_left:
    POINT_RIGHT = '\U0001F449'  # :point_right:
    JEANS = '\U0001F456'  # :jeans:
    SHOE = '\U0001F45E'  # :mans_shoe:
    BLANK = '\U000023F9'  # :stop_button:


class Connect4(Enum):
    BLACK = '\U000026AB'  # :black_circle:
    RED = '\U0001F534'  # :red_cirle:
    BLUE = '\U0001F535'  # :large_blue_circle:
    RED_WIN = '\U00002B55'  # :o:
    BLUE_WIN = '\U0001F518'  # :radio_button:


class Suits(Enum):
    SPADES = '\U00002660'  # :spades:
    CLUBS = '\U00002663'  # :clubs:
    HEARTS = '\U00002665'  # :hearts:
    DIAMONDS = '\U00002666'  # :diamonds:
    JOKER = '\U0001F0CF'  # :black_joker:


class HighLow(Enum):
    HIGH = '\U000023EB'  # :arrow_double_up:
    LOW = '\U000023EC'  # :arrow_double_down:
