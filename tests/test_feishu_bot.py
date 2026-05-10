import unittest
from unittest.mock import patch

import feishu_bot


def text_event(text: str, mentions=None):
    return {
        "header": {"event_type": "im.message.receive_v1", "event_id": "evt_1"},
        "event": {
            "sender": {"sender_type": "user"},
            "message": {
                "chat_id": "oc_1",
                "message_id": "om_1",
                "message_type": "text",
                "content": f'{{"text": "{text}"}}',
                "mentions": mentions or [],
            },
        },
    }


class FeishuMentionTests(unittest.TestCase):
    def setUp(self):
        feishu_bot.PROCESSED_EVENTS.clear()

    @patch("feishu_bot.get_tenant_access_token")
    @patch("feishu_bot.load_config")
    def test_group_message_without_at_is_ignored(self, load_config, get_token):
        load_config.return_value = feishu_bot.FeishuConfig("app", "secret")
        get_token.side_effect = AssertionError("should not call Feishu APIs")

        result = feishu_bot.handle_feishu_event(text_event("狂爱粉 测试一下"))

        self.assertEqual(result, {"ok": True, "ignored": "not mentioned"})

    @patch("feishu_bot.get_tenant_access_token")
    @patch("feishu_bot.load_config")
    def test_at_inside_message_is_not_treated_as_bot_mention(self, load_config, get_token):
        load_config.return_value = feishu_bot.FeishuConfig("app", "secret")
        get_token.side_effect = AssertionError("should not call Feishu APIs")

        result = feishu_bot.handle_feishu_event(text_event("狂爱粉 test@example.com"))

        self.assertEqual(result, {"ok": True, "ignored": "not mentioned"})

    @patch("feishu_bot.get_tenant_access_token")
    @patch("feishu_bot.load_config")
    def test_at_other_user_is_ignored(
        self,
        load_config,
        get_token,
    ):
        load_config.return_value = feishu_bot.FeishuConfig("app", "secret", bot_open_id="ou_bot")
        get_token.side_effect = AssertionError("should not call Feishu APIs")

        result = feishu_bot.handle_feishu_event(
            text_event(
                "@_user_1 狂爱粉 测试一下",
                mentions=[{"key": "@_user_1", "id": {"open_id": "ou_other"}}],
            )
        )

        self.assertEqual(result, {"ok": True, "ignored": "not mentioned"})

    @patch("feishu_bot.send_image")
    @patch("feishu_bot.upload_image")
    @patch("feishu_bot.generate_from_text")
    @patch("feishu_bot.get_tenant_access_token")
    @patch("feishu_bot.load_config")
    def test_message_with_bot_at_generates_meme(
        self,
        load_config,
        get_token,
        generate_from_text,
        upload_image,
        send_image,
    ):
        load_config.return_value = feishu_bot.FeishuConfig("app", "secret", bot_open_id="ou_bot")
        get_token.return_value = "tenant-token"
        generate_from_text.return_value.command = "狂爱粉"
        generate_from_text.return_value.extension = "jpg"
        generate_from_text.return_value.buffer.getvalue.return_value = b"image"
        upload_image.return_value = "img_key"

        result = feishu_bot.handle_feishu_event(
            text_event(
                "@_user_1 狂爱粉 测试一下",
                mentions=[{"key": "@_user_1", "id": {"open_id": "ou_bot"}}],
            )
        )

        self.assertEqual(result, {"ok": True})
        generate_from_text.assert_called_once_with("@_user_1 狂爱粉 测试一下")
        send_image.assert_called_once()

    @patch("feishu_bot.send_image")
    @patch("feishu_bot.upload_image")
    @patch("feishu_bot.generate_from_text")
    @patch("feishu_bot.get_tenant_access_token")
    @patch("feishu_bot.load_config")
    def test_message_with_leading_feishu_mention_generates_without_bot_open_id(
        self,
        load_config,
        get_token,
        generate_from_text,
        upload_image,
        send_image,
    ):
        load_config.return_value = feishu_bot.FeishuConfig("app", "secret")
        get_token.return_value = "tenant-token"
        generate_from_text.return_value.command = "狂爱粉"
        generate_from_text.return_value.extension = "jpg"
        generate_from_text.return_value.buffer.getvalue.return_value = b"image"
        upload_image.return_value = "img_key"

        result = feishu_bot.handle_feishu_event(
            text_event(
                "@_user_1 狂爱粉 测试一下",
                mentions=[{"key": "@_user_1", "id": {"open_id": "ou_any"}}],
            )
        )

        self.assertEqual(result, {"ok": True})
        generate_from_text.assert_called_once_with("@_user_1 狂爱粉 测试一下")
        send_image.assert_called_once()


if __name__ == "__main__":
    unittest.main()
