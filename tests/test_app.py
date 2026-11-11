import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def test_demo_and_filters(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
        self.assertEqual(len(app.exception), 0)
        app.checkbox[0].check().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[0].value, '60')
        self.assertEqual(app.slider[0].value, 25)
        before = app.dataframe[1].value['No. of contacts: named team in last 12 months'].sum()
        app.slider[0].set_value(100).run()
        self.assertEqual(len(app.exception), 0)
        after = app.dataframe[1].value['No. of contacts: named team in last 12 months'].sum()
        self.assertGreater(after, before)
        self.assertEqual(len(app.dataframe), 2)
        app.number_input[0].set_value(100).run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any('No patients match' in item.value for item in app.info))


if __name__ == '__main__':
    unittest.main()
