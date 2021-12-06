import asyncio
from functools import cache
import json
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from mi import User
from mi.chat import ChatContent
from mi.drive import Drive, File
from mi.emoji import Emoji
from mi.exception import ContentRequired, InvalidParameters, NotExistRequiredParameters
from mi.iterators import InstanceIterator
from mi.note import Note, ReactionContent, Poll
from mi.utils import api, check_multi_arg, get_module_logger, remove_dict_empty, remove_empty_object, str_lower, upper_to_lower


class ConnectionState:
    def __init__(self, dispatch: Callable[..., Any]):
        self.dispatch = dispatch
        self.logger = get_module_logger(__name__)

    async def _parse_channel(self, message: Dict[str, Any]) -> None:
        """parse_channel is a function to parse channel event

        チャンネルタイプのデータを解析後適切なパーサーに移動させます

        Parameters
        ----------
        message : Dict[str, Any]
            Received message
        """
        base_msg = message['body']
        channel_type = str_lower(base_msg.get('type'))
        self.logger.debug(f'ChannelType: {channel_type}')
        await getattr(self, f'_parse_{channel_type}')(base_msg['body'])

    async def _parse_messaging_message(self, message: Dict[str, Any]) -> None:
        """
        チャットが来た際のデータを処理する関数
        """
        await self.dispatch('message', ChatContent(message))

    async def _parse_unread_messaging_message(self, message: Dict[str, Any]) -> None:
        """
        チャットが既読になっていない場合のデータを処理する関数
        """
        await self.dispatch('message', ChatContent(message))

    async def _parse_notification(self, message: Dict[str, Any]) -> None:
        """
        通知イベントを解析する関数
        
        Parameters
        ----------
        message: Dict[str, Any]
            Received message

        Returns
        -------
        None
        """
        notification_type = str_lower(message['type'])
        await getattr(self, f'_parse_{notification_type}')(message)

    async def _parse_unread_notification(self, message: Dict[str, Any]) -> None:
        """
        未読の通知を解析する関数

        Parameters
        ----------
        message : Dict[str, Any]
            Received message
        """
        notification_type = str_lower(message['type'])
        await getattr(self, f'_parse_{notification_type}')(message)

    async def _parse_reaction(self, message: Dict[str, Any]) -> None:
        """
        リアクションに関する情報を解析する関数
        """
        await self.dispatch('reaction', ReactionContent(message))

    async def _parse_note(self, message: Dict[str, Any]) -> None:
        """
        ノートイベントを解析する関数
        """
        await self.dispatch('message', Note(message, self))

    async def on_emoji_add(self, message: dict):
        """
        emojiがインスタンスに追加された際のイベント

        Parameters
        ----------
        message

        Returns
        -------

        """
        await asyncio.create_task(
            self.dispatch("emoji_add", Emoji(
                message['body']['emoji']
            )))

    async def on_message(self, message: Any) -> asyncio.Task:
        """
        タイムラインに来たノートに関するイベントを発生させる関数

        Parameters
        ----------
        message:
            Received message

        Returns
        -------
        task: asyncio.Task
        """
        msg = message.get("body", {}).get("body", {})
        message = Note(
            upper_to_lower(msg,
                           replace_list={"user": "author", "text": "content"})
        )
        await self.dispatch(message.id)
        return asyncio.create_task(self.cls._on_message(message))

    async def on_chat(self, ctx):
        """
        チャットイベント

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        msg = ctx.get("body", {}).get("body", {})
        ctx = ChatContent(
            upper_to_lower(msg,
                           replace_list={"user": "author", "text": "content"})
        )
        return asyncio.create_task(self.dispatch("chat", ctx))

    async def on_notification(self, message: dict):
        """
        通知イベント

        Parameters
        ----------
        message

        Returns
        -------

        """
        pass

    async def on_mention(self, ctx: dict) -> asyncio.Task:
        """
        メンションイベント

        Parameters
        ----------
        ctx : dict

        Returns
        -------
        asyncio.Task
        """

        base_ctx = ctx.get("body", {}).get("body")
        base_ctx["content"] = base_ctx["text"]
        base_ctx["text"] = (
            base_ctx["text"].replace(f"@{config.i.profile.username}",
                                     "").strip(" ")
        )
        return asyncio.create_task(
            self.dispatch("mention", Note(**base_ctx))
        )

    async def on_follow(self, message: dict) -> asyncio.Task:
        """
        フォローイベント

        Parameters
        ----------
        message

        Returns
        -------

        """
        return asyncio.create_task(
            self.dispatch(
                "follow",
                Follow(
                    **upper_to_lower(message.get("body"),
                                     replace_list={"body": "user"})
                ),
            )
        )

    @staticmethod
    def follow_user(user_id: str) -> tuple[bool, Optional[str]]:
        """
        与えられたIDのユーザーをフォローします

        Parameters
        ----------
        user_id : Optional[str] = None
            フォローしたいユーザーのID

        Returns
        -------
        status: bool = False
            成功ならTrue, 失敗ならFalse
        """
        data = {"userId": user_id}
        res = api("/api/following/create", json_data=data, auth=True)
        if res.json().get("error"):
            code = res.json()["error"]["code"]
            status = False
        else:
            code = None
            status = True
        return status, code

    @staticmethod
    def unfollow_user(user_id: str) -> bool:
        """
        Parameters
        ----------
        user_id :
            フォローを解除したいユーザーのID

        Returns
        -------
        status: bool = False
            成功したならTrue, 失敗したならFalse
        """
        data = {"userId": user_id}
        res = api("/api/following/delete", json_data=data, auth=True)
        return bool(res.status_code == 204 or 200)

    async def on_reaction(self, message):
        """
        ノートのリアクションイベント

        Parameters
        ----------
        message:dict

        Returns
        -------
        None
        """

        base_msg = message.get("body", {}).get("body", {})
        base_msg["id"] = message.get("body", {}).get("id", None)
        asyncio.create_task(
            self.dispatch("reaction", Note(upper_to_lower(base_msg)))
        )

    async def on_deleted(self, message):
        """
        ノートの削除イベント

        Parameters
        ----------
        message

        Returns
        -------

        """
        base_msg = message.get("body", {}).get("body", {})
        asyncio.create_task(self.dispatch("deleted", base_msg))

        # TODO: on_erroを実装

    async def on_close(self, web_socket):
        pass

    def _get_i(self):
        res = api("/api/i", auth=True)
        return User(upper_to_lower(json.loads(res.text)), state=self)

    def _get_users(self,
                   limit: int = 10,
                   *,
                   offset: int = 0,
                   sort: Optional[str] = None,
                   state: str = 'all',
                   origin: str = 'local',
                   username: Optional[str] = None,
                   hostname: Optional[str] = None,
                   get_all: bool = False) -> Iterator[User]:
        return InstanceIterator(self).get_users(limit=limit, offset=offset, sort=sort, state=state, origin=origin,
                                                username=username, hostname=hostname, get_all=get_all)

    @staticmethod
    async def _add_reaction(reaction: str, note_id: Optional[str] = None) -> bool:
        """
        指定したnoteに指定したリアクションを付与します（内部用

        Parameters
        ----------
        reaction : Optional[str]
            付与するリアクション名
        note_id : Optional[str]
            付与対象のノートID

        Returns
        -------
        status: bool
            成功したならTrue,失敗ならFalse
        """
        data = remove_dict_empty({"noteId": note_id, "reaction": reaction})
        res = api("/api/notes/reactions/create", json_data=data, auth=True)
        return res.status_code == 204

    @staticmethod
    async def _note_delete(note_id: str) -> tuple[bool, int]:
        data = {"noteId": note_id}
        res = api("/api/notes/delete", json_data=data, auth=True)
        return res.status_code == 204, res.status_code

    @staticmethod
    def _add_file(
            path: str,
            *,
            name: Optional[str] = None,
            force: bool = False,
            is_sensitive: bool = False,
            url: Optional[str] = None
    ) -> Drive:
        """
        ノートにファイルを添付します。

        Parameters
        ----------
        is_sensitive : bool
            この画像がセンシティブな物の場合Trueにする
        field : dict
            ファイル送信用のdict
        force : bool
            Trueの場合同じ名前のファイルがあった場合でも強制的に保存する
        path : str
            そのファイルまでのパスとそのファイル.拡張子(/home/test/test.png)
        name: str
            ファイル名(拡張子があるなら含めて)
        url : str
            URLから画像をアップロードする場合にURLを指定する

        Returns
        -------
        self: Note
        """
        return Drive().upload(path, name, force, is_sensitive, url=url)

    @staticmethod
    def _add_poll(
            item: Optional[str] = None,
            *,
            poll: Optional[dict],
            expires_at: Optional[int] = None,
            expired_after: Optional[int] = None,
            item_list: Optional[List] = None
    ) -> dict:
        """
        アンケートを作成します

        Parameters
        ----------
        poll : Optional[dict]
            既にあるpollを使用する
        item_list : Optional[List]
            アンケート選択肢を配列にしたもの
        item: Optional[str]
            アンケートの選択肢(単体)
        expires_at : Optional[int]
            いつにアンケートを締め切るか 例:2021-09-02T15:00:00.000Z
        expired_after : Optional[int]
            投稿後何秒後にアンケートを締め切るか(秒

        Returns
        -------
        poll: dict
        """
        if poll is None:
            poll = {
                "choices": [],
                "expiresAt": expires_at,
                "expiredAfter": expired_after,
            }
        if item:
            poll["choices"].append(item)
        if item_list:
            poll["choices"].extend(item_list)

        return poll

    @cache
    def _get_user(self, user_id: Optional[str] = None, username: Optional[str] = None,
                  host: Optional[str] = None) -> Dict[str, Tuple[str, List[Any], Dict[str, Any]]]:
        """
        ユーザーのプロフィールを取得します。一度のみサーバーにアクセスしキャッシュをその後は使います。
        fetch_userを使った場合はキャッシュが廃棄され再度サーバーにアクセスします。

        Parameters
        ----------
        user_id : str
            取得したいユーザーのユーザーID
        username : str
            取得したいユーザーのユーザー名
        host : str, default=None
            取得したいユーザーがいるインスタンスのhost

        Returns
        -------
        dict:
            ユーザー情報
        """
        return self._fetch_user(user_id, username, host)

    def _fetch_user(self, user_id: Optional[str] = None, username: Optional[str] = None,
                    host: Optional[str] = None) -> Dict[str, Tuple[str, List[Any], Dict[str, Any]]]:
        """
        サーバーにアクセスし、ユーザーのプロフィールを取得します。基本的には get_userをお使いください。

        Parameters
        ----------
        user_id : str
            取得したいユーザーのユーザーID
        username : str
            取得したいユーザーのユーザー名
        host : str, default=None
            取得したいユーザーがいるインスタンスのhost

        Returns
        -------
        dict:
            ユーザー情報
        """
        if not check_multi_arg(user_id, username):
            raise NotExistRequiredParameters("user_id, usernameどちらかは必須です")

        data = remove_dict_empty(
            {"userId": user_id, "username": username, "host": host})
        self._get_user.cache_clear()
        return User(upper_to_lower(api("/api/users/show", json_data=data, auth=True).json()), state=self)

    def _post_note(self,
            content: str,
            *,
            visibility: str = "public",
            visible_user_ids: Optional[List[str]] = None,
            cw: Optional[str] = None,
            local_only: bool = False,
            no_extract_mentions: bool = False,
            no_extract_hashtags: bool = False,
            no_extract_emojis: bool = False,
            reply_id: List[str] = [],
            renote_id: Optional[str] = None,
            channel_id: Optional[str] = None,
            file_ids: List[File] = [],
            poll: Optional[Poll] = None
            ):
        field = {
            "visibility": visibility,
            "visibleUserIds": visible_user_ids,
            "text": content,
            "cw": cw,
            "localOnly": local_only,
            "noExtractMentions": no_extract_mentions,
            "noExtractHashtags": no_extract_hashtags,
            "noExtractEmojis": no_extract_emojis,
            "replyId": reply_id,
            "renoteId": renote_id,
            "channelId": channel_id
        }
        if poll and len(poll.choices) > 0:
            field["poll"] = poll
        if file_ids:
            field["fileIds"] = file_ids
        field = remove_empty_object(field)
        print(field)
        res = api("/api/notes/create", json_data=field, auth=True)
        res_json = res.json()
        if (
                res_json.get("error")
                and res_json.get("error", {}).get("code") == "CONTENT_REQUIRED"
        ):
            raise ContentRequired(
                "ノートの送信にはtext, file, renote またはpollのいずれか1つが無くてはいけません")
        return Note(
            upper_to_lower(res_json["createdNote"],
                           replace_list={"user": "author"})
        ,state=self)
        
    @staticmethod
    def _get_followers(
            user_id: Optional[str] = None,
            username: Optional[str] = None,
            host: Optional[str] = None,
            since_id: Optional[str] = None,
            until_id: Optional[str] = None,
            limit: int = 10,
            get_all: bool = False,
    ) -> Iterator[Dict[str, Any]]:
        """
        与えられたユーザーのフォロワーを取得します
        Parameters
        ----------
        user_id : str, default=None
            ユーザーのid
        username : str, default=None
            ユーザー名
        host : str, default=None
            ユーザーがいるインスタンスのhost名
        since_id : str, default=None
        until_id : str, default=None
            前回の最後の値を与える(既に実行し取得しきれない場合に使用)
        limit : int, default=10
            取得する情報の最大数 max: 100
        get_all : bool, default=False
            全てのフォロワーを取得する
        Yields
        ------
        dict
            フォロワーの情報
        Raises
        ------
        InvalidParameters
            limit引数が不正な場合
        """
        if not check_multi_arg(user_id, username):
            raise NotExistRequiredParameters("user_id, usernameどちらかは必須です")

        if limit > 100:
            raise InvalidParameters("limit は100以上を受け付けません")

        data = remove_dict_empty(
            {
                "userId": user_id,
                "username": username,
                "host": host,
                "sinceId": since_id,
                "untilId": until_id,
                "limit": limit,
            }
        )
        if get_all:
            loop = True
            while loop:
                get_data = api("/api/users/followers", json_data=data,
                               auth=True).json()
                if len(get_data) > 0:
                    data["untilId"] = get_data[-1]["id"]
                else:
                    break
                yield get_data
        else:
            get_data = api("/api/users/followers", json_data=data,
                           auth=True).json()
            yield get_data