from flask import Flask, request, jsonify, render_template
import pandas as pd
from optimizer import Opti_Meal, Food_Type

app = Flask(__name__)

def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

# Load food data
food_df = pd.read_csv('table_cf.csv')
food_col = 'Food'
fat_col = 'Fat'
prot_col = 'Protein'
carbs_col = 'Carb'
cal_col = 'Calories'

@app.route('/')
def index():
    return render_template('index.html', food_list=food_df[food_col].tolist())

@app.route('/optimize', methods=['POST'])
def optimize_meal():
    try:
        data = request.get_json(silent=True) or {}

        # Ingredients payload
        ingredients_payload = data.get('ingredients') or []
        if not isinstance(ingredients_payload, list) or not ingredients_payload:
            return jsonify({"error": "Please select at least one food"}), 400

        # Calorie bounds
        cal_min = safe_float(data.get('calories_min'))
        cal_max = safe_float(data.get('calories_max'))

        # Ratio max parsing
        ratio_raw = data.get('ratio_max', '').strip()
        try:
            if ':' in ratio_raw:
                num, den = ratio_raw.split(':', 1)
                ratio_max = float(num) / float(den)
            else:
                ratio_max = float(ratio_raw)
        except Exception:
            return jsonify({"error": "Invalid ratio_max; use decimal (e.g. '1.5') or 'x:y' format (e.g. '3:1')"}), 400

        # Initialize optimizer
        meal = Opti_Meal(meal_name="User Meal")
        meal.set_debug(False)

        # Add foods with optional parameters
        for ing in ingredients_payload:
            name = ing.get('name')
            rows = food_df[food_df[food_col] == name]
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
            # Build kwargs
            kwargs = { 'new_opti_ingredient': name }
            if ing.get('grams_minimum') is not None:
                kwargs['grams_minimum'] = safe_float(ing['grams_minimum'])
            if ing.get('grams_maximum') is not None:
                kwargs['grams_maximum'] = safe_float(ing['grams_maximum'])
            if ing.get('use_in_objective_function'):
                kwargs['use_in_objective_function'] = True
            if ing.get('points_per_gram') is not None:
                kwargs['points_per_gram'] = safe_float(ing['points_per_gram'])
            if ing.get('target_grams') is not None:
                kwargs['target_grams'] = safe_float(ing['target_grams'])
            meal.add_opti_ingredient(**kwargs)

        # Apply constraints
        meal.set_calories_minimum(cal_min)
        meal.set_calories_maximum(cal_max)
        meal.set_ratio_maximum(ratio_max)

        # Solve
        success = meal.optimize()
        if not success:
            return jsonify({"error": "No feasible solution under those constraints."}), 400

        # Build response
        ingredients = []
        totals = {"fat": 0.0, "protein": 0.0, "carbs": 0.0, "calories": 0.0}
        for ing_inst in meal._Opti_Meal__opti_ingredients_dict.values():
            g = ing_inst.get_grams()
            f = ing_inst.get_food_type().get_fat_gram_ratio() * g
            p = ing_inst.get_food_type().get_protein_gram_ratio() * g
            c = ing_inst.get_food_type().get_carbs_gram_ratio() * g
            k = ing_inst.get_food_type().get_cal_gram_ratio() * g
            ingredients.append({
                "name": ing_inst.get_name(),
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
