"""
MIT License

Copyright (c) 2020-present shay (shayypy)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

------------------------------------------------------------------------------

This project includes code from https://github.com/Rapptz/discord.py, which is
available under the MIT license:

The MIT License (MIT)

Copyright (c) 2015-present Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

import datetime
from enum import Enum
from typing import Optional

from .embed import Embed
from .file import MediaType, Attachment
from .utils import ISO8601


class ChatMessage:
    """A message in Guilded.

    .. container:: operations

        .. describe:: x == y

            Checks if two messages are equal.

        .. describe:: x != y

            Checks if two messages are not equal.

    Attributes
    ------------
    id: :class:`str`
        The message's ID.
    channel: Optional[:class:`abc.TeamChannel`]
        The channel this message was sent in.
    created_at: :class:`datetime.datetime`
        A timezone-aware :class:`datetime.datetime` in UTC of when the
        message was sent.
    updated_at: Optional[:class:`datetime.datetime`]
        A timezone-aware :class:`datetime.datetime` in UTC of when the
        message was last updated. There is an alias for this called
        :attr:`edited_at`.
    edited_at: Optional[:class:`datetime.datetime`]
        Alias of :attr:`updated_at`.
    deleted_at: Optional[:class:`datetime.datetime`]
        A timezone-aware :class:`datetime.datetime` in UTC of when the
        message was deleted. This should only be available through the
        :func:`on_message_delete` event.
    author: Optional[Union[:class:`User`, :class:`Member`]]
        The user or team member who sent this message.
    team: Optional[:class:`Team`]
        The team this message was sent in. ``None`` if the message was sent
        in a DM.
    webhook_id: Optional[:class:`str`]
        The webhook's ID that sent the message, if applicable.
    bot_id: Optional[:class:`str`]
        The bot's ID that sent the message, if applicable.
    channel_id: :class:`str`
        The channel's ID that this message was sent in. This attribute is
        mostly for internal purposes but it has been documented due to lack of
        useful cachable data in the early access API.
    author_id: :class:`str`
        The user or team member's ID who sent this message. In the case that
        :attr:`bot_id` or :attr:`webhook_id` is present, this is that value
        instead. This attribute is mostly for internal purposes but it has
        been documented due to lack of useful cachable data in the early
        access API.
    team_id: Optional[:class:`str`]
        The team's ID that this message was sent in. This attribute is
        mostly for internal purposes but it has been documented due to lack of
        useful cachable data in the early access API.
    """
    def __init__(self, *, state, channel, data, **extra):
        self._state = state

        message = data.get('message', data)
        self.id = message['id']
        self.channel = channel
        self.channel_id = message['channelId']
        self.team = extra.get('team') or getattr(channel, 'team', None)
        self.team_id = message.get('teamId')

        self.created_at = ISO8601(data.get('createdAt'))
        self.updated_at = ISO8601(message.get('updatedAt'))
        self.deleted_at = ISO8601(message.get('deletedAt'))

        self.webhook_id = message.get('createdByWebhookId')
        self.bot_id = message.get('createdByBotId')
        self.author = extra.get('author')
        self.author_id = self.webhook_id or self.bot_id or message['createdBy']
        if self.author is None:
            if data.get('channelType', '').lower() == 'team' and self.team is not None:
                self.author = self._state._get_team_member(self.team_id, self.author_id)
            elif data.get('channelType', '').lower() == 'dm' or self.team is None:
                self.author = self._state._get_user(self.author_id)
            elif data.get('createdByInfo'):
                self.author = self._state.create_user(data=data['createdByInfo'])

        if self.author is not None:
            self.author.bot = self.created_by_bot

        self.content = message.get('content', '')

    def __str__(self):
        return self.content

    def __eq__(self, other):
        try:
            return self.id == other.id
        except:
            return False

    def __repr__(self):
        return f'<Message id={repr(self.id)} author={repr(self.author)} channel={repr(self.channel)}>'

    @property
    def edited_at(self):
        return self.updated_at

    @property
    def created_by_bot(self):
        return self.author.bot if self.author else (self.webhook_id is not None or self.bot_id is not None)

    @property
    def jump_url(self):
        return f'https://guilded.gg/channels/{self.channel.id}/chat?messageId={self.id}'

    @property
    def guild(self):
        return self.team

    async def delete(self):
        """|coro|

        Delete this message.
        """
        return await self._state.delete_channel_message(self.channel_id, self.id)

    async def update(self, *, content: str):
        """|coro|

        Update this message.

        There is an alias for this called ``edit``.

        Parameters
        ------------
        content: :class:`str`
            The content to update this message with.
        """
        response = await self._state.update_message(self.channel_id, self.id, content=content)
        self.content = content
        self.updated_at = ISO8601(response.get('updatedAt')) or datetime.datetime.now(datetime.timezone.utc)
        return self

    def edit(self, *args, **kwargs):
        return self.update(*args, **kwargs)

    async def add_reaction(self, emoji: int):
        """|coro|

        Add a reaction to this message. Planned to take type :class:`Emoji`,
        but currently takes an :class:`int` (the emoji's ID).

        Parameters
        ------------
        emoji: :class:`int`
            The emoji to add.
        """
        return await self._state.add_reaction_emote(self.channel_id, self.id, emoji)

Message = ChatMessage
