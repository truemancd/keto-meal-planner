from flask import Flask, request, jsonify, render_template
import pandas as pd
from optimizer import Opti_Meal, Food_Type

app = Flask(__name__)

def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

# Load your food table
food_df = pd.read_csv('table_cf.csv')

# Assuming first six columns are: Food Name, Fat(g), Protein(g), Carbs(g), Calories(kcal), Volume(ml)
cols = list(food_df.columns)
food_col, fat_col, prot_col, carbs_col, cal_col, vol_col = cols[:6]

# Master list of food names
food_options = food_df[food_col].tolist()

@app.route('/')
def serve_index():
    return render_template('index.html', food_list=food_options)

@app.route('/optimize', methods=['POST'])
def optimize_meal():
    data = request.get_json()
    meal = Opti_Meal(meal_name="User Meal")
    meal.set_debug(False)

    for fname in data.get('foods', []):
        row = food_df[food_df[food_col] == fname]
        if row.empty:
            continue
        r = row.iloc[0]
        # Adjust because table is per-100g
        ft = Food_Type(
            name=r[food_col],
            fat_gram_ratio=safe_float(r[fat_col]) * 0.01,
            protein_gram_ratio=safe_float(r[prot_col])* 0.01,
            carbs_gram_ratio=safe_float(r[carbs_col]) * 0.01,
            cal_gram_ratio=safe_float(r[cal_col]) * 0.01,
            ml_gram_ratio=safe_float(r[vol_col]) * 0.01
        )
        meal.add_food_type(ft)
        meal.add_opti_ingredient(new_opti_ingredient=ft.get_name())

    meal.set_calories_minimum(safe_float(data.get('calories_min')))
    meal.set_protein_grams_minimum(safe_float(data.get('protein_min')))
    meal.set_ratio_minimum(safe_float(data.get('ratio_min')))

    try:
        meal.set_objective_function_type(0)
        if not meal.optimize():
            return jsonify({"error": "No feasible solution. Try loosening constraints or adding more foods."}), 400

        meal.set_objective_function_type(int(data.get('objective_function_type', 1)))
        if not meal.optimize():
            return jsonify({"error": "Feasible but failed under chosen objective."}), 400

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

        return jsonify({"meal_plan": str(meal), "ingredients": ingredients, "totals": totals})

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
