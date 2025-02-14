# Mi.py

[![CodeFactor](https://www.codefactor.io/repository/github/yupix/mi.py/badge)](https://www.codefactor.io/repository/github/yupix/mi.py)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/f5acd9da804d4a11b031d36dbd398067)](https://www.codacy.com/gh/yupix/Mi.py/dashboard?utm_source=github.com&utm_medium=referral&utm_content=yupix/Mi.py&utm_campaign=Badge_Grade)
[![buddy pipeline](https://app.buddy.works/yupi0982/mi-py/pipelines/pipeline/345007/badge.svg?token=b304dd68d3eeb7917d453a2d2102621123ae4f05e0b659dde59cad486e2984b3 "buddy pipeline")](https://app.buddy.works/yupi0982/mi-py/pipelines/pipeline/345007)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fyupix%2FMi.py.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2Fyupix%2FMi.py?ref=badge_shield)
[![Build Status](https://ci.akarinext.org/api/badges/yupix/Mi.py/status.svg)](https://ci.akarinext.org/yupix/Mi.py)

## 概要

Mi.py は[Discord.py](https://github.com/Rapptz/discord.py)
ライクな書き方ができるように作っている MisskeyApi wrapper です

# サポートしているMisskey

- [Misskey Official v12](https://github.com/misskey-dev/misskey)
- [Ayuskey latest](https://gtihub.com/teamblackcrystal/misskey)

## 使い方

様々な使い方を書くにあたって README から変更しました。[こちら](examples)からご覧ください。 その他のメソッドなどについては[ドキュメント](https://yupix.github.io/Mi.py) をご覧ください

## 注意点

グローバルタイムラインに接続したりする際に使う以下の様なコードがあるとホームタイムラインとグローバルタイムラインの 2 つを受信したことになり on_message が 2 回動作します。 これは接続するチャンネルを増やすごとに増えていく形になります

```python
await Router(ws).connect_channel(['home', 'global'])
```

### Collaborators

<table>
    <tr>
        <td><img src="https://avatars.githubusercontent.com/u/50538210?s=120&v=4"></img></td>
    </tr>
    <tr>
        <td align="center"><a href="https://github.com/yupix">Author | @yupix</a></td>
    </tr>
</table>

### SpecialThanks

開発を手伝ってくれている方々です。

<table>
    <tr>
        <td><img src="https://avatars.githubusercontent.com/u/26793720?s=120&v=4"></img></td>
    </tr>
    <tr>
        <td align="center"><a href="https://github.com/Uraking-Github">Adviser | @Uraking</a></td>
    </tr>
        <tr>
        <td><img src="https://s3.akarinext.org/misskey/*/thumbnail-64775133-569b-4ec8-b7aa-ca3766d3d583.png", height=124px></img></td>
    </tr>
    <tr>
        <td align="center"><a href="https://github.com/sousuke0422">Document | @sousuke0422</a></td>
    </tr>
</table>

### Libraries

- [Discord.py](https://github.com/Rapptz/discord.py)
  - 一部や仕組みを参考にさせてもらっています。実際にコードも利用しています

最後にこのプロジェクトを作るきっかけになり、一部のコードを使用させていただいている Discord.py が Archived になりました。 作者である Danny さんや全てのコラボレーターに最大限の感謝申し上げます。

# LICENSE

[Mi.py](https://github.com/yupix/Mi.py/blob/master/LICENSE.md)  
[Credit](https://github.com/yupix/Mi.py/blob/master/COPYING.md)  
[Third party](https://github.com/yupix/Mi.py/blob/master/LICENSE/ThirdPartyLicense.md)

[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fyupix%2FMi.py.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fyupix%2FMi.py?ref=badge_large)
