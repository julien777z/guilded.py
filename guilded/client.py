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

import asyncio
import logging
import sys
import traceback

import aiohttp

from .errors import NotFound, ClientException
from .embed import Embed
from .gateway import GuildedWebSocket, WebSocketClosure
from .http import HTTPClient
from .presence import Presence
from .status import Game
from .team import Team
from .user import ClientUser, User

log = logging.getLogger(__name__)

def _cancel_tasks(loop):
    try:
        task_retriever = asyncio.Task.all_tasks
    except AttributeError:
        # future proofing for 3.9 I guess
        task_retriever = asyncio.all_tasks

    tasks = {t for t in task_retriever(loop=loop) if not t.done()}

    if not tasks:
        return

    log.info('Cleaning up after %d tasks.', len(tasks))
    for task in tasks:
        task.cancel()

    loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
    log.info('All tasks finished cancelling.')

    for task in tasks:
        if task.cancelled():
            continue
        if task.exception() is not None:
            loop.call_exception_handler({
                'message': 'Unhandled exception during Client.run shutdown.',
                'exception': task.exception(),
                'task': task
            })

def _cleanup_loop(loop):
    try:
        _cancel_tasks(loop)
        if sys.version_info >= (3, 6):
            loop.run_until_complete(loop.shutdown_asyncgens())
    finally:
        log.info('Closing the event loop.')
        loop.close()

class Client:
    """The basic client class for interfacing with Guilded.

    Parameters
    ----------
    bot_id: :class:`str`
        The ID if this bot, copied from the "Bots" menu. This could be
        thought of as the equivalent of a "Client ID" in Discord bots. This is
        used for internal owner checking and will likely be removed come full
        API release.
    max_messages: Optional[:class:`int`]
        The maximum number of messages to store in the internal message cache.
        This defaults to ``1000``. Passing in ``None`` disables the message cache.
    loop: Optional[:class:`asyncio.AbstractEventLoop`]
        The :class:`asyncio.AbstractEventLoop` to use for asynchronous operations.
        Defaults to ``None``, in which case the default event loop is used via
        :func:`asyncio.get_event_loop()`.
    disable_team_websockets: Optional[:class:`bool`]
        Whether to prevent the library from opening team-specific websocket
        connections.
    presence: Optional[:class:`.Presence`]
        A presence to use upon logging in.
    status: Optional[:class:`.Status`]
        A status (game) to use upon logging in.
    cache_on_startup: Optional[:class:`dict`]
        A mapping of types of objects to a :class:`bool` (whether to
        cache the type on startup). Currently accepts ``members`` and
        ``channels``. By default, both are enabled.

    Attributes
    -----------
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop that the client uses for HTTP requests and websocket
        operations.
    user: :class:`ClientUser`
        The currently logged-in user.
    ws: Optional[:class:`GuildedWebsocket`]
        The websocket gateway the client is currently connected to. Could be
        ``None``.
    """
    def __init__(self, bot_id, **options):
        self.loop = options.pop('loop', asyncio.get_event_loop())
        self.max_messages = options.pop('max_messages', 1000)

        # state
        self.http = HTTPClient(
            session=aiohttp.ClientSession(loop=self.loop),
            bot_id=bot_id,
            max_messages=self.max_messages
        )
        self._closed = False
        self._ready = asyncio.Event()

        # internal
        self.user = ClientUser(data={'id': bot_id}, state=self.http)
        self.disable_team_websockets = options.pop('disable_team_websockets', False)
        self._login_presence = options.pop('presence', None)
        self._login_status = options.pop('status', None)
        self._listeners = {}

        cache_on_startup = options.pop('cache_on_startup', {})
        self.cache_on_startup = {
            'members': cache_on_startup.get('members') or True,
            'channels': cache_on_startup.get('channels') or True
        }

    @property
    def cached_messages(self):
        return list(self.http._messages.values())

    @property
    def emojis(self):
        return list(self.http._emojis.values())

    @property
    def teams(self):
        return list(self.http._teams.values())

    @property
    def users(self):
        return list(self.http._users.values())

    @property
    def members(self):
        return list(self.http._team_members.values())

    @property
    def dm_channels(self):
        """List[:class:`.DMChannel`]: The private/dm channels that the connected client can see."""
        return list(self.http._dm_channels.values())

    @property
    def private_channels(self):
        """List[:class:`.DMChannel`]: |dpyattr|

        This is an alias of :attr:`.dm_channels`.
        """
        return self.dm_channels

    @property
    def team_channels(self):
        """List[:class:`.TeamChannel`]: The team channels that the connected client can see."""
        return list(self.http._team_channels.values())

    @property
    def channels(self):
        """List[Union[:class:`.TeamChannel`, :class:`.DMChannel`]]: The channels (Team and DM included) that the connected client can see."""
        return [*self.dm_channels, *self.team_channels]

    @property
    def guilds(self):
        """List[:class:`.Team`]: |dpyattr|

        This is an alias of :attr:`.teams`.
        """
        return self.teams

    @property
    def latency(self):
        return float('nan') if self.ws is None else self.ws.latency

    @property
    def closed(self):
        return self._closed

    def is_ready(self):
        return self._ready.is_set()

    async def wait_until_ready(self):
        await self._ready.wait()

    async def _run_event(self, coro, event_name, *args, **kwargs):
        try:
            await coro(*args, **kwargs)
        except asyncio.CancelledError:
            pass
        except Exception:
            try:
                await self.on_error(event_name, *args, **kwargs)
            except asyncio.CancelledError:
                pass

    def _schedule_event(self, coro, event_name, *args, **kwargs):
        wrapped = self._run_event(coro, event_name, *args, **kwargs)
        # Schedules the task
        return asyncio.create_task(wrapped, name=f'guilded.py: {event_name}')

    def event(self, coro):
        """A decorator to register an event for the library to automatically dispatch when appropriate.

        The events must be a :ref:`coroutine <coroutine>`, if not, :exc:`TypeError` is raised.

        Example
        ---------

        .. code-block:: python3

            @client.event
            async def on_ready():
                print('Ready!')

        Raises
        --------
        TypeError
            The function passed is not actually a coroutine.
        """
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError('Event must be a coroutine.')

        setattr(self, coro.__name__, coro)
        self._listeners[coro.__name__] = coro
        return coro

    def dispatch(self, event_name, *args, **kwargs):
        coro = self._listeners.get(f'on_{event_name}')
        if not coro:
            return
        self.loop.create_task(coro(*args, **kwargs))

    async def connect(self, token=None, *, reconnect=True):
        self.http.token = token or self.http.token
        if not self.http.token:
            raise ClientException(
                'You must provide a token to this method explicitly, or have '
                'it already set in this Client\'s HTTPClient beforehand.'
            )

        while not self.closed:
            ws_build = GuildedWebSocket.build(self, loop=self.loop)
            gws = await asyncio.wait_for(ws_build, timeout=60)
            if type(gws) != GuildedWebSocket:
                self.dispatch('error', gws)
                return

            self.ws = gws
            self.http.ws = self.ws
            self.dispatch('connect')

            async def listen_socks(ws):
                next_backoff_time = 5
                while True and ws is not None:
                    try:
                        await ws.poll_event()
                    except WebSocketClosure as exc:
                        code = ws._close_code or ws.socket.close_code

                        if reconnect is False:
                            log.warning('Websocket closed with code %s. Last message ID was %s', code, ws._last_message_id)
                            await self.close()
                            break

                        log.warning('Websocket closed with code %s, attempting to reconnect in %s seconds with last message ID %s', code, next_backoff_time, ws._last_message_id)
                        self.dispatch('disconnect')
                        await asyncio.sleep(next_backoff_time)

                        build = GuildedWebSocket.build(self, loop=self.loop)
                        try:
                            ws = await asyncio.wait_for(build, timeout=60)
                        except asyncio.TimeoutError:
                            log.warning('Timed out trying to reconnect.')
                            next_backoff_time += 5
                    else:
                        next_backoff_time = 5

            self._ready.set()
            self.dispatch('ready')
            await listen_socks(self.ws)

    async def close(self):
        """|coro|

        Close the current connection.
        """
        if self._closed: return

        try:
            await ws.close(code=1000)
        except Exception:
            # it's probably already closed, but catch all anyway
            pass

        self._closed = True
        self._ready.clear()

    def run(self, token: str, *, reconnect=True):
        """Connect to Guilded's gateway and start the event loop. This is a
        blocking call; nothing after it will be called until the bot has been
        closed.

        Parameters
        ------------
        token: :class:`str`
            The bot's auth token,
        reconnect: Optional[:class:`bool`]
            Whether to reconnect on loss/interruption of gateway connection.
        """
        try:
            self.loop.create_task(self.connect(token, reconnect=reconnect))
            self.loop.run_forever()
        except KeyboardInterrupt:
            exit()

    def get_message(self, id: str):
        """Get a message from your :attr:`.cached_messages`. 
        As messages are often frequently going in and out of cache, you should
        not rely on this method, and instead use :meth:`abc.Messageable.fetch_message`.
        
        Parameters
        ------------
        id: :class:`str`
            the id of the message

        Returns
        ---------
        Optional[:class:`Message`]
            The message from the ID
        """
        return self.http._get_message(id)

    def get_team(self, id: str):
        """Get a team from your :attr:`.teams`.

        Parameters
        ------------
        id: :class:`str`
            the id of the team

        Returns
        ---------
        Optional[:class:`Team`]
            The team from the ID
        """
        return self.http._get_team(id)

    def get_user(self, id: str):
        """Get a user from your :attr:`.users`.

        Parameters
        ------------
        id: :class:`str`
            the id of the user

        Returns
        ---------
        Optional[:class:`User`]
            The user from the ID
        """
        return self.http._get_user(id)

    def get_channel(self, id: str):
        """Get a channel from your :attr:`.channels`.

        Parameters
        ------------
        id: :class:`str`
            the id of the team or dm channel

        Returns
        ---------
        Optional[:class:`abc.Messageable.TeamChannel`]
            The channel from the ID
        """
        return self.http._get_global_team_channel(id) or self.http._get_dm_channel(id)

    async def on_error(self, event_method, *args, **kwargs):
        print(f'Ignoring exception in {event_method}:', file=sys.stderr)
        traceback.print_exc()

    async def fetch_user(self, id: str):
        """|coro|

        Fetch a user from the API.

        Returns
        ---------
        :class:`User`
            The user from the ID
        """
        user = await self.http.get_user(id)
        return User(state=self.http, data=user)

    async def getch_user(self, id: str):
        """|coro|

        Try to get a user from internal cache, and if not found, try to fetch from the API.
        
        Returns
        ---------
        :class:`User`
            The user from the ID
        """
        return self.get_user(id) or await self.fetch_user(id)
