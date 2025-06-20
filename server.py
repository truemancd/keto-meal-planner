# server.py
from flask import Flask, request, jsonify, render_template
import pandas as pd
from optimizer import Opti_Meal, Food_Type

app = Flask(__name__)

def safe_float(val, default=0.0):
    try:
        return float(val)
    except:
        return default

def none_or_float(val):
    try:
        return float(val)
    except:
        return None

# Load your nutritional CSV
food_df = pd.read_csv('table_cf.csv')

@app.route('/')
def index():
    return render_template('index.html', food_list=food_df['Food'].tolist())

@app.route('/optimize', methods=['POST'])
def optimize_meal():
    data = request.get_json(force=True) or {}
    ingredients = data.get('ingredients', [])
    if not ingredients:
        return jsonify({"error": "Select at least one food"}), 400

    # Parse bounds
    cal_min = none_or_float(data.get('calories_min')) or 0.0
    cal_max = none_or_float(data.get('calories_max'))
    prot_min = none_or_float(data.get('protein_min'))
    prot_max = none_or_float(data.get('protein_max'))
    fat_min = none_or_float(data.get('fat_min'))
    fat_max = none_or_float(data.get('fat_max'))
    carb_min = none_or_float(data.get('carb_min'))
    carb_max = none_or_float(data.get('carb_max'))

    # Parse ratio_max (decimal or “3:1”)
    ratio_raw = (data.get('ratio_max') or '').strip()
    ratio_max = None
    if ratio_raw:
        if ':' in ratio_raw:
            num, den = ratio_raw.split(':', 1)
            ratio_max = float(num) / float(den)
        else:
            ratio_max = float(ratio_raw)

    # Build optimizer
    meal = Opti_Meal(meal_name=data.get('meal_name', 'User Meal'))
    meal.set_debug(False)

    # Add each selected food
    for ing in ingredients:
        name = ing.get('name')
        row = food_df[food_df['Food'] == name]
        if row.empty:
            continue
        r = row.iloc[0]
        ft = Food_Type(
            name=name,
            fat_gram_ratio=safe_float(r['Fat']) / 100.0,
            protein_gram_ratio=safe_float(r['Protein']) / 100.0,
            carbs_gram_ratio=safe_float(r['Carb']) / 100.0,
            cal_gram_ratio=safe_float(r['Calories']) / 100.0,
            ml_gram_ratio=1.0
        )
        meal.add_opti_ingredient(ft)

    # Apply all bounds if provided
    meal.set_calories_minimum(cal_min)
    if cal_max is not None: meal.set_calories_maximum(cal_max)
    if prot_min is not None: meal.set_protein_grams_minimum(prot_min)
    if prot_max is not None: meal.set_protein_grams_maximum(prot_max)
    if fat_min is not None: meal.set_fat_grams_minimum(fat_min)
    if fat_max is not None: meal.set_fat_grams_maximum(fat_max)
    if carb_min is not None: meal.set_carbs_grams_minimum(carb_min)
    if carb_max is not None: meal.set_carbs_grams_maximum(carb_max)
    if ratio_max is not None: meal.set_ratio_maximum(ratio_max)

    # Run optimization
    try:
        meal.optimize()
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    # Return the plan string and the totals
    return jsonify({
        "meal_plan": str(meal),
        "totals": meal.get_totals()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
