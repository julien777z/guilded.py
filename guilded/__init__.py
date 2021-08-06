__copyright__ = 'shay 2020-present'
__version__ = '2.0.0a'

import logging

from . import abc
from .asset import Asset
from .channel import ChannelType, ChatChannel, VoiceChannel, Thread
from .client import Client
from .colour import Color, Colour
from .embed import Embed, EmbedProxy, EmptyEmbed
from .emoji import Emoji
from .errors import (
    BadRequest,
    ClientException,
    Forbidden,
    GuildedException,
    GuildedServerError,
    HTTPException,
    NotFound,
    TooManyRequests,
)
from .message import ChatMessage, Message
from .team import SocialInfo, Team, TeamTimezone
from .user import ClientUser, Member, User

logging.getLogger(__name__).addHandler(logging.NullHandler())
