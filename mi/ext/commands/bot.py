"""Commands FrameWork用のCore部分"""

import asyncio
import importlib
from mi.exception import CogNameDuplicate, ExtensionAlreadyLoaded, ExtensionFailed, ExtensionNotFound, NoEntryPointError
from mi.ext.commands.context import Context
from mi.ext.commands.core import GroupMixin
from mi.ext.commands.view import StringView
from mi.user import UserAction
import re
import sys
import traceback
from typing import Any, Callable, Coroutine, Dict, Optional

from mi import UserProfile, config, utils
from mi.http import WebSocket

__all__ = ['BotBase', 'Bot']


class BotBase(GroupMixin):
    def __init__(self, command_prefix, **options):
        super().__init__(**options)
        self.command_prefix = command_prefix
        self.extra_events = {}
        self.special_events = {}
        self._check_once = []
        self._checks = []
        self._after_invoke = None
        self.token = None
        self.origin_uri = None
        self.__extensions: Dict[str, Any] = {}
        self.i: UserProfile = None
        self.__cogs: Dict[str] = {}
        self.strip_after_prefix = options.get('strip_after_prefix', False)

    async def can_run(self, ctx, *, call_once=False):
        data = self._check_once if call_once else self._checks

        if len(data) == 0:
            return True

        return await utils.async_all(f(ctx) for f in data)

    async def invoke(self, ctx):
        if ctx.command:
            # await self.dispatch('command', ctx)
            print(await self.can_run(ctx, call_once=True))
            try:
                if await self.can_run(ctx, call_once=True):
                    print(vars(ctx.command))
                    await ctx.command.invoke(ctx)
                else:
                    raise errors.CheckFailure('')
            except CommandError as exc:
                await ctx.command.dispatch_error(ctx, exc)

    async def get_context(self, message, *, cls=Context):
        view = StringView(message.text)
        ctx = cls(bot=self, message=message)
        if view.skip_string(self.command_prefix) is False:  # prefixがテキストに含まれているか確認
            return ctx
        invoker = view.get_word()
        ctx.command = self.all_commands.get(invoker)
        return ctx

    async def process_commands(self, message):
        if message.author.is_bot:
            return

        ctx = await self.get_context(message)
        await self.invoke(ctx)

    async def _on_message(self, message):
        await self.process_commands(message)

    def event(self, name=None):
        def decorator(func):
            self.add_event(func, name)
            return func

        return decorator

    def add_event(self, func, name=None):
        name = func.__name__ if name is None else name
        if not asyncio.iscoroutinefunction(func):
            raise TypeError('Listeners must be coroutines')

        if name in self.extra_events:
            self.special_events[name].append(func)
        else:
            self.special_events[name] = [func]

    def listen(self, name=None):

        def decorator(func):
            self.add_listener(func, name)
            return func

        return decorator

    def add_listener(self, func, name=None):
        name = func.__name__ if name is None else name
        if not asyncio.iscoroutinefunction(func):
            raise TypeError('Listeners must be coroutines')

        if name in self.extra_events:
            self.extra_events[name].append(func)
        else:
            self.extra_events[name] = [func]

    async def event_dispatch(self, event_name, *args, **kwargs):
        ev = 'on_' + event_name
        for event in self.special_events.get(ev, []):
            foo = importlib.import_module(event.__module__)
            coro = getattr(foo, ev)
            await self.schedule_event(coro, event, *args, **kwargs)

    async def dispatch(self, event_name, *args, **kwargs):
        ev = 'on_' + event_name

        for event in self.extra_events.get(ev, []):
            foo = importlib.import_module(event.__module__)
            coro = getattr(foo, ev)
            await self.schedule_event(coro, event, *args, **kwargs)
        coro = getattr(self, ev)
        await self.schedule_event(coro, ev, *args, **kwargs)

    def add_cog(self, cog, override: bool = False) -> None:
        cog_name = cog.__cog_name__
        existing = self.__cogs.get(cog_name)
        if existing is not None:
            if not override:
                raise CogNameDuplicate()
            self.remove_cog(cog_name)  # TODO: 作る

        cog = cog._inject(self)
        self.__cogs[cog_name] = cog

        print(vars(self.__cogs[cog_name]))

    def remove_cog(self, name: str):  # TODO: Optional[Cog]を返すように
        """Cogを削除します"""
        cog = self.__cogs.get(name, None)
        if cog is None:
            return

        cog._eject(self)

        return cog

    def _load_from_module_spec(self, spec: importlib.machinery.ModuleSpec, key: str) -> None:
        lib = importlib.util.module_from_spec(spec)
        sys.modules[key] = lib
        try:
            spec.loader.exec_module(lib)
        except Exception as e:
            del sys.modules[key]
            raise ExtensionFailed(key, e) from e

        try:
            setup = getattr(lib, 'setup')
        except AttributeError:
            del sys.modules[key]
            raise NoEntryPointError(key)

        try:
            setup(self)
        except Exception as e:
            print(e)
            del sys.modules[key]
            # self._remove_module_references(lib.__name__)
            # self._call_module_finalizers(lib, key)
            raise ExtensionFailed(key, e) from e
        else:
            self.__extensions[key] = lib

    def _resolve_name(self, name: str, package: Optional[str]) -> str:
        try:
            return importlib.util.resolve_name(name, package)
        except ImportError:
            raise ExtensionNotFound(name)

    def load_extension(self, name: str, *, package: Optional[str] = None) -> None:
        """拡張をロードする

        Parameters
        ----------
        name : str
            [description]
        package : Optional[str], optional
            [description], by default None
        """
        name = self._resolve_name(name, package)
        if name in self.__extensions:
            raise ExtensionAlreadyLoaded

        spec = importlib.util.find_spec(name)
        self._load_from_module_spec(spec, name)

    async def schedule_event(self, coro: Callable[..., Coroutine[Any, Any, Any]], event_name: str, *args: Any,
                             **kwargs: Any) -> asyncio.Task:
        return asyncio.create_task(self._run_event(coro, event_name, *args, **kwargs), name=f'MI.py: {event_name}')

    async def _run_event(self, coro: Callable[..., Coroutine[Any, Any, Any]], event_name: str, *args: Any,
                         **kwargs: Any) -> None:
        try:
            await coro(*args, **kwargs)
        except asyncio.CancelledError:
            pass
        except Exception:
            try:
                await self.__on_error(event_name, *args, **kwargs)
            except asyncio.CancelledError:
                pass

    async def __on_error(self, event_method: str) -> None:
        print(f'Ignoring exception in {event_method}', file=sys.stderr)
        traceback.print_exc()

    async def on_error(self, err):
        await self.event_dispatch('error', err)

    def run(self, uri: str, token: str) -> None:
        """
        Launch the bot.
        Parameters
        ----------
        uri : str
            websocket url of the Misskey instance to connect to
        token : str
            Misskey account token

        Examples
        --------

        When inheriting from a class: ::

            class MyBot(Bot):
                async def on_message(self, ws, message):
                    pass
            bot = MyBot()
            bot.run(uri, token)

        When using a listener: ::

            bot = Bot()

            @bot.event()
            async def on_message(ws, message):
                pass

            bot.run(uri, token)

        Returns
        -------
        None: None
        """
        self.token = token
        if _origin_uri := re.search(r'wss?://(.*)/streaming', uri):
            origin_uri = _origin_uri.group(0).replace('wss', 'https').replace(
                'ws', 'http').replace('/streaming', '')
        else:
            origin_uri = uri
        self.origin_uri = origin_uri[:-1] if uri[-1] == '/' else origin_uri
        auth_i = {'token': self.token, 'origin_uri': self.origin_uri}
        config.init(**auth_i)
        self.i = UserAction().get_i()
        asyncio.get_event_loop().run_until_complete(WebSocket(self).run(f'{uri}?i={token}'))


class Bot(BotBase):
    pass
