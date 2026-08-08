import unittest

from pybo.i18n import translate


class InterfaceTranslationTests(unittest.TestCase):
    def test_dynamic_dialog_messages_have_english_translations(self):
        self.assertEqual(translate("메시지를 삭제할까요?", "en"), "Delete messages?")
        self.assertEqual(translate("아바타 선택", "en"), "Choose avatar")
        self.assertEqual(translate("모두 읽음", "en"), "Delete selected")

    def test_dynamic_dialog_messages_have_japanese_translations(self):
        self.assertEqual(translate("메시지를 삭제할까요?", "ja"), "メッセージを削除しますか？")
        self.assertEqual(translate("아바타 선택", "ja"), "アバター選択")
        self.assertEqual(translate("모두 읽음", "ja"), "選択削除")


if __name__ == "__main__":
    unittest.main()
