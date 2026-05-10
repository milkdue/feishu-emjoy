# 飞书表情包机器人

一个可以在飞书群聊里生成表情包的机器人。群里 `@机器人` 后发送指令和文字，机器人会生成图片或 GIF 并发回当前群聊。

## 使用方式

必须先 `@机器人`，否则机器人会忽略消息，避免群聊里普通聊天误触发表情包生成。

```text
@机器人 狂爱粉 测试一下
@机器人 可达鸭 左边|右边
@机器人 喜报 今天可以摸鱼
@机器人 王境泽 我就是饿死|死外边 从这里跳下去|不会吃你们一点东西|真香
```

多段文字建议用 `|` 分隔，也支持换行。完整指令见 [MEME_COMMANDS.md](MEME_COMMANDS.md)。

## 图片效果

### 狂爱粉

![狂爱粉效果](docs/images/fanatic.jpg)

### 喜报

![喜报效果](docs/images/goodnews.png)

### 可达鸭

![可达鸭效果](docs/images/psyduck.gif)

## 部署

部署到 Vercel 后，把飞书事件订阅回调 URL 设置为：

```text
https://你的域名.vercel.app/api/feishu
```

需要配置环境变量：

```text
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_VERIFICATION_TOKEN=xxx
FEISHU_BOT_OPEN_ID=ou_xxx
```

`FEISHU_BOT_OPEN_ID` 可选。配置后机器人会只响应明确 @ 到自己的消息；不配置时，服务会通过飞书 `/bot/v3/info` 获取并缓存机器人 `open_id`。

更详细的飞书开放平台和 Vercel 配置见 [FEISHU_BOT_DEPLOY.md](FEISHU_BOT_DEPLOY.md)。

## 本地验证

```bash
.venv/bin/python -m unittest
```
