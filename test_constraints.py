import unittest
import pandas as pd
from server import app

class ConstraintTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        df = pd.read_csv('table_cf.csv')
        self.first_food = df['Food'].iloc[0]

    def test_nutrient_bounds(self):
        payload = {
            "ingredients": [{"name": self.first_food}],
            "calories_min": 0,
            "calories_max": 10000,
            "fat_min": 0,
            "fat_max": 10000,
            "protein_min": 0,
            "protein_max": 10000,
            "carb_min": 0,
            "carb_max": 10000,
            "ratio_max": "10:1",
            "meal_name": "Test Meal"
        }
        response = self.client.post('/optimize', json=payload)
        self.assertEqual(response.status_code, 200, msg=response.get_json())
        data = response.get_json()
        totals = data.get('totals', {})
        for nutr in ['calories', 'fat', 'protein', 'carbs']:
            min_key = f"{nutr}_min"
            max_key = f"{nutr}_max"
            self.assertIn(nutr, totals)
            self.assertGreaterEqual(totals[nutr], payload[min_key])
            self.assertLessEqual(totals[nutr], payload[max_key])

if __name__ == '__main__':
    unittest.main()