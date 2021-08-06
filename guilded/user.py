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

import guilded.abc

from .utils import ISO8601
from .file import File, MediaType


class User(guilded.abc.User, guilded.abc.Messageable):
    """Represents a Guilded user."""
    async def send(self, *args, **kwargs):
        """|coro|

        Send a message to this user.

        Takes the same parameters as :class:`abc.Messageable.send`, from which
        this inherits.

        Parameters
        ------------
        content: :class:`str`
            The text content to send.
        """
        return await super().send(*args, **kwargs)

class Member(User):
    """Represents a member of a team.

    Attributes
    ------------
    team: :class:`Team`
        The team this member is from.
    xp: :class:`int`
        This member's XP. Could be negative.
    joined_at: :class:`datetime.datetime`
        When this user joined their team.
    display_name: :class:`str`
        This member's display name (``nick`` if present, else ``name``)
    colour: Optional[:class:`int`]
        The color that this member's name displays with. There is an alias for 
        this called ``color``.
    nick: Optional[:class:`str`]
        This member's nickname, if any.
    """
    def __init__(self, *, state, data, **extra):
        super().__init__(state=state, data=data)
        self.team = extra.get('team') or data.get('team')
        self.team_id = data.get('teamId') or (self.team.id if self.team else None)
        self.nick = data.get('nickname')
        self.xp = data.get('teamXp')
        self.joined_at = ISO8601(data.get('joinDate'))
        self.colour = data.get('colour') or data.get('color')

    def __repr__(self):
        return f'<Member id={self.id} name={self.name} team={repr(self.team)}>'

    @property
    def color(self):
        return self.colour

    @property
    def display_name(self):
        return self.nick or self.name

    async def edit(self, **kwargs):
        """|coro|

        Edit this member.

        Parameters
        ------------
        nick: Optional[:class:`str`]
            A new nickname. Use ``None`` to reset.
        xp: Optional[:class:`int`]
            A new XP value.
        """
        try:
            nick = kwargs.pop('nick')
        except KeyError:
            pass
        else:
            if nick is None:
                await self._state.reset_team_member_nickname(self.team.id, self.id)
            else:
                await self._state.change_team_member_nickname(self.team.id, self.id, nick)
            self.nick = nick

        try:
            xp = kwargs.pop('xp')
        except KeyError:
            pass
        else:
            await self._state.set_team_member_xp(self.team.id, self.id, xp)
            self.xp = xp

class ClientUser(guilded.abc.User):
    """Represents the current bot for this :class:`Client`.

    Attributes
    ------------
    id: :class:`str`
        This bot's ID as provided while constructing the :class:`Client`.
    """
    #def __init__(self, *, state, data):
    #    super().__init__(state=state, data=data)

    def __repr__(self):
        return f'<ClientUser id={repr(self.id)} name={repr(self.name)}>'
