from flask import Flask, request, jsonify, render_template
import pandas as pd
from optimizer import Opti_Meal, Food_Type

app = Flask(__name__)

def safe_float(val, default=0.0):
    """
    Safely convert a value to float; return default on failure.
    """
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

# Load your food data
food_df = pd.read_csv('table_cf.csv')

# CSV column mappings
food_col = 'Food'
fat_col = 'Fat'
prot_col = 'Protein'
carbs_col = 'Carb'
cal_col = 'Calories'

@app.route('/')
def index():
    """
    Serve the main UI.
    Ensure index.html lives under 'templates/' with Jinja support.
    """
    return render_template('index.html', food_list=food_df[food_col].tolist())

@app.route('/optimize', methods=['POST'])
def optimize_meal():
    """
    Handle meal optimization with:
      - calories_min
      - calories_max
      - ratio_max (decimal or 'x:y')
    """
    try:
        data = request.get_json(silent=True) or {}

        # Validate selected foods
        foods_list = data.get('foods') or []
        if not isinstance(foods_list, list) or not foods_list:
            return jsonify({"error": "Please select at least one food"}), 400

        # Calorie bounds
        cal_min = safe_float(data.get('calories_min'))
        cal_max = safe_float(data.get('calories_max'))

        # Ratio max parsing (decimal or colon syntax)
        ratio_raw = data.get('ratio_max', '').strip()
        try:
            if ':' in ratio_raw:
                num, den = ratio_raw.split(':', 1)
                ratio_max = float(num) / float(den)
            else:
                ratio_max = float(ratio_raw)
        except Exception:
            return jsonify({
                "error": "Invalid ratio_max; use decimal (e.g. '1.5') or 'x:y' format (e.g. '3:1')"
            }), 400

        # Initialize optimizer
        meal = Opti_Meal(meal_name="User Meal")
        meal.set_debug(False)

        # Add each food type
        for fname in foods_list:
            rows = food_df[food_df[food_col] == fname]
            if rows.empty:
                continue
            r = rows.iloc[0]
            ft = Food_Type(
                name=r[food_col],
                fat_gram_ratio=safe_float(r[fat_col]) / 100.0,
                protein_gram_ratio=safe_float(r[prot_col]) / 100.0,
                carbs_gram_ratio=safe_float(r[carbs_col]) / 100.0,
                cal_gram_ratio=safe_float(r[cal_col]) / 100.0,
                ml_gram_ratio=1.0
            )
            meal.add_food_type(ft)
            meal.add_opti_ingredient(new_opti_ingredient=ft.get_name())

        # Apply constraints
        meal.set_calories_minimum(cal_min)
        meal.set_calories_maximum(cal_max)
        meal.set_ratio_maximum(ratio_max)

        # Solve optimization
        success = meal.optimize()
        if not success:
            return jsonify({"error": "No feasible solution under those constraints."}), 400

        # Build response payload
        ingredients = []
        totals = {"fat": 0.0, "protein": 0.0, "carbs": 0.0, "calories": 0.0}
        for ing in meal._Opti_Meal__opti_ingredients_dict.values():
            g = ing.get_grams()
            f = ing.get_food_type().get_fat_gram_ratio() * g
            p = ing.get_food_type().get_protein_gram_ratio() * g
            c = ing.get_food_type().get_carbs_gram_ratio() * g
            k = ing.get_food_type().get_cal_gram_ratio() * g

            ingredients.append({
                "name": ing.get_name(),
                "grams": g,
                "fat": f,
                "protein": p,
                "carbs": c,
                "calories": k
            })
            totals["fat"] += f
            totals["protein"] += p
            totals["carbs"] += c
            totals["calories"] += k

        return jsonify({
            "meal_plan": str(meal),
            "ingredients": ingredients,
            "totals": totals
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
