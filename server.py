from flask import Flask, request, jsonify, render_template
import pandas as pd
from optimizer import Opti_Meal, Food_Type

app = Flask(__name__)

def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

food_df = pd.read_csv('table_cf.csv')
food_col = 'Food'
prot_col = 'Protein'
fat_col = 'Fat'
carbs_col = 'Carb'
cal_col = 'Calories'

@app.route('/')
def index():
    return render_template('index.html', food_list=food_df[food_col].tolist())

@app.route('/optimize', methods=['POST'])
def optimize_meal():
    try:
        data = request.get_json(silent=True) or {}
        foods_list = data.get('foods') or []
        if not isinstance(foods_list, list) or not foods_list:
            return jsonify({"error": "Please select at least one food"}), 400

        cal_max = safe_float(data.get('calories_max'))
        prot_max = safe_float(data.get('protein_max'))

        ratio_raw = data.get('ratio_max', '')
        try:
            if ':' in ratio_raw:
                num, den = ratio_raw.split(':', 1)
                ratio_max = float(num) / float(den)
            else:
                ratio_max = float(ratio_raw)
        except:
            return jsonify({"error": "Invalid ratio_max format; use e.g. '1.5' or '3:1'"}), 400

        meal = Opti_Meal(meal_name="User Meal")
        meal.set_debug(False)

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

        meal.set_calories_maximum(cal_max)
        meal.set_protein_grams_maximum(prot_max)
        meal.set_ratio_maximum(ratio_max)

        success = meal.optimize()
        if not success:
            return jsonify({"error": "No feasible solution under those constraints."}), 400

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
    app.run(host='0.0.0.0', port=5050)
