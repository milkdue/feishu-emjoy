# 飞书表情包机器人部署说明

## Vercel 回调地址

部署到 Vercel 后，飞书事件订阅回调 URL 填：

```text
https://你的域名.vercel.app/api/feishu
```

`GET /api/feishu` 会返回健康检查 JSON；`POST /api/feishu` 用于接收飞书事件。

## 飞书开放平台配置

1. 创建飞书企业自建应用。
2. 添加机器人能力，并把机器人加入目标群。
3. 开启事件订阅。
4. 订阅消息事件：`im.message.receive_v1`。
5. 在权限管理里开启发送消息、上传图片、接收群聊消息相关权限，并发布/重新发布应用。
6. 事件订阅里的 Encrypt Key 先不要开启；当前代码只处理明文事件。

## Vercel 环境变量

在 Vercel Project Settings -> Environment Variables 添加：

```text
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_VERIFICATION_TOKEN=xxx
```

`FEISHU_VERIFICATION_TOKEN` 可选，但建议填写，用来校验飞书事件来源。

## 用户使用方式

群里 @机器人 后发送：

```text
@机器人 狂爱粉 测试一下
@机器人 可达鸭 左边|右边
@机器人 王境泽 我就是饿死|死外边 从这里跳下去|不会吃你们一点东西|真香
```

多段参数建议用 `|` 分隔；也支持每段参数单独换行。完整指令见 `MEME_COMMANDS.md`。

## 当前实现链路

1. Vercel 接收飞书 `im.message.receive_v1` 事件。
2. 解析文本消息，去掉 @ 提及。
3. 用 `meme_router.py` 匹配指令并生成图片 buffer。
4. 调用飞书上传图片接口获取 `image_key`。
5. 调用飞书发消息接口，把图片发回原群。

## 注意事项

- GIF 模板生成可能比静态图慢，`vercel.json` 已把函数超时时间设为 30 秒。
- Vercel 部署时不要上传 `.venv`；`.vercelignore` 已排除本地虚拟环境和缓存。
- 如果飞书后台开启事件加密，需要额外实现 Encrypt Key 解密逻辑。
- 如果收到“未知指令”或“需要 N 段文字”，机器人会在群里回复文本提示。
