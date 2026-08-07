import unittest

from pybo.japan_schools import load_japan_schools, search_japan_schools


class JapanSchoolSearchTestCase(unittest.TestCase):
    def test_nationwide_dataset_has_all_supported_types(self):
        schools = load_japan_schools()
        self.assertGreater(len(schools), 20_000)
        self.assertEqual({"小学校", "中学校", "高等学校", "大学"}, {item["type"] for item in schools})

    def test_search_finds_representative_schools(self):
        cases = (
            ("札幌", "小学校", "小学校"),
            ("大阪", "中学校", "中学校"),
            ("福岡", "高等学校", "高等学校"),
            ("東京大学", "大学", "東京大学"),
        )
        for keyword, school_type, expected in cases:
            with self.subTest(keyword=keyword, school_type=school_type):
                results = search_japan_schools(keyword, school_type)
                self.assertTrue(results)
                self.assertTrue(any(expected in item["name"] or item["type"] == expected for item in results))

    def test_korean_type_filter_returns_korean_type(self):
        results = search_japan_schools("京都", "대학교")
        self.assertTrue(results)
        self.assertTrue(all(item["type"] == "대학교" for item in results))


if __name__ == "__main__":
    unittest.main()
