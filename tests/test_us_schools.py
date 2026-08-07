import unittest

from pybo.us_schools import load_us_schools, search_us_schools


class UsSchoolSearchTestCase(unittest.TestCase):
    def test_nationwide_dataset_has_all_supported_types(self):
        schools = load_us_schools()
        self.assertGreater(len(schools), 90_000)
        self.assertEqual(
            {"Elementary School", "Middle School", "High School", "University"},
            {item["type"] for item in schools},
        )
        states = {item["state"] for item in schools}
        self.assertTrue({"AK", "CA", "NY", "RI", "TX"}.issubset(states))

    def test_representative_school_searches(self):
        cases = (
            ("Palo Alto", "Elementary School"),
            ("Albertville", "Middle School"),
            ("Stuyvesant", "High School"),
            ("Harvard", "University"),
        )
        for keyword, school_type in cases:
            with self.subTest(keyword=keyword, school_type=school_type):
                self.assertTrue(search_us_schools(keyword, school_type))

    def test_korean_type_filter_returns_korean_type(self):
        results = search_us_schools("Stanford", "대학교")
        self.assertTrue(results)
        self.assertTrue(all(item["type"] == "대학교" for item in results))


if __name__ == "__main__":
    unittest.main()
