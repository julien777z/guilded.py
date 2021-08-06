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

import abc

try: import discord
except ModuleNotFoundError: discord_compat = False
else: discord_compat = True

from .activity import Activity
from .asset import Asset
from .embed import _EmptyEmbed, Embed
from .file import MediaType, FileType, File
from .message import Message
from .presence import Presence
from .utils import ISO8601

class Messageable(metaclass=abc.ABCMeta):
    def __init__(self, *, state, data):
        self._state = state
        self.id = data.get('id')
        self._channel_id = data.get('id')
        self.type = None

    async def send(self, content: str):
        """|coro|

        Send a message to a Guilded channel.

        Parameters
        ------------
        content: :class:`str`
            The text content to send.
        """
        coro = self._state.create_channel_message(self._channel_id, content=content)
        response = await coro
        message = self._state.create_message(data=response['message'])
        return message

    async def fetch_messages(self):
        """|coro|

        Fetch the last 50 messages sent in this channel.
        """
        history = await self._state.get_channel_messages(self._channel_id)
        messages = []
        for message in history.get('messages', []):
            try:
                messages.append(self._state.create_message(channel=self, data=message))
            except:
                pass

        return messages

    async def fetch_message(self, id: str):
        message = await self._state.get_channel_message(self._channel_id, id)
        return message

class User(metaclass=abc.ABCMeta):
    def __init__(self, *, state, data, **extra):
        self._state = state
        data = data.get('user', data)

        self.type = None
        self.id = data.get('id')
        self.name = data.get('name')
        self.subdomain = data.get('subdomain')
        self.email = data.get('email')
        self.service_email = data.get('serviceEmail')
        self.games = data.get('aliases', [])
        self.bio = (data.get('aboutInfo') or {}).get('bio') or ''
        self.tagline = (data.get('aboutInfo') or {}).get('tagLine') or ''
        self.presence = Presence.from_value(data.get('userPresenceStatus', 5))
        status = data.get('userStatus', {})
        if status.get('content'):
            self.status = Activity.build(status['content'])
        else:
            self.status = None

        self.blocked_at = ISO8601(data.get('blockedDate'))
        self.online_at = ISO8601(data.get('lastOnline'))
        self.created_at = ISO8601(data.get('createdAt') or data.get('joinDate'))
        # in profilev3, createdAt is returned instead of joinDate

        self.avatar_url = Asset('profilePicture', state=self._state, data=data)
        self.banner_url = Asset('profileBanner', state=self._state, data=data)

        self.moderation_status = data.get('moderationStatus')
        self.badges = data.get('badges', [])

        self.bot = extra.get('bot', False)

        self.friend_status = extra.get('friend_status')
        self.friend_requested_at = ISO8601(extra.get('friend_created_at'))

    def __str__(self):
        return f'{self.name}#{self.id}'

    def __eq__(self, other):
        try:
            return self.id == other.id
        except:
            return False

    def __repr__(self):
        return f'<{self.__class__.__name__} id={repr(self.id)} name={repr(self.name)}>'

    @property
    def slug(self):
        return self.subdomain

    @property
    def url(self):
        return self.subdomain

    @property
    def profile_url(self):
        return f'https://guilded.gg/profile/{self.id}'

    @property
    def vanity_url(self):
        if self.subdomain:
            return f'https://guilded.gg/{self.subdomain}'
        else:
            return None

    @property
    def mention(self):
        return f'<@{self.id}>'

    async def create_dm(self):
        dm = await self._state.create_dm(self.id)
        self._channel_id = dm._channel_id
        return Messageable(state=self._state, data=dm)

class TeamChannel(Messageable):
    def __init__(self, *, state, group, data, **extra):
        super().__init__(state=state, data=data)
        #self._state = state
        data = data.get('data') or data.get('channel') or data
        self.group = group
        self.group_id = data.get('groupId') or getattr(self.group, 'id', None)

        self.team = extra.get('team') or getattr(group, 'team', None) or self._state._get_team(data.get('teamId'))
        self.team_id = self.team.id if self.team else data.get('teamId')

        self.name = data.get('name')
        self.position = data.get('priority')
        self.description = data.get('description')
        self.slug = data.get('slug')
        self.roles_synced = data.get('isRoleSynced')
        self.public = data.get('isPublic', False)
        self.settings = data.get('settings')  # no clue

        self.created_at = ISO8601(data.get('createdAt'))
        self.updated_at = ISO8601(data.get('updatedAt'))
        self.added_at = ISO8601(data.get('addedAt'))  # i have no idea what this is
        self.archived_at = ISO8601(data.get('archivedAt'))
        self.auto_archive_at = ISO8601(data.get('autoArchiveAt'))
        created_by = extra.get('created_by') or self._state._get_team_member(self.team_id, extra.get('createdBy'))
        if created_by is None:
            if data.get('createdByInfo'):
                self.created_by = self._state.create_member(data=data.get('createdByInfo'))
        else:
            self.created_by = created_by
        self.archived_by = extra.get('archived_by') or self._state._get_team_member(self.team_id, extra.get('archivedBy'))
        self.created_by_webhook_id = data.get('createdByWebhookId')
        self.archived_by_webhook_id = data.get('archivedByWebhookId')

        self.parent_id = data.get('parentChannelId') or data.get('originatingChannelId')
        # latter is probably only on threads
        if self.parent_id is not None:
            self.parent = self._state._get_team_channel(self.team_id, self.parent_id)
        else:
            self.parent = None

    @property
    def topic(self):
        return self.description

    @property
    def vanity_url(self):
        if self.slug and self.team.vanity_url:
            return f'{self.team.vanity_url}/blog/{self.slug}'
        return None

    @property
    def mention(self):
        return f'<#{self.id}>'

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<{self.__class__.__name__} id={repr(self.id)} name={repr(self.name)} team={repr(self.team)}>'

    def __eq__(self, other):
        try:
            return self.id == other.id
        except:
            return False

    async def delete(self):
        return await self._state.delete_team_channel(self.team_id, self.group_id, self.id)
