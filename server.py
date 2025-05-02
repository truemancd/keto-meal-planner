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

# Load your food table (ensure table_cf.csv is in the same directory)
food_df = pd.read_csv('table_cf.csv')

# Column names matching your CSV header
food_col = 'Food'
prot_col = 'Protein'
fat_col = 'Fat'
carbs_col = 'Carb'
cal_col = 'Calories'

@app.route('/')
def index():
    """
    Serve the main index page.
    Make sure your index.html is located in a 'templates/' folder.
    """
    return render_template('index.html', food_list=food_df[food_col].tolist())

@app.route('/optimize', methods=['POST'])
def optimize_meal():
    """
    Optimize a keto meal based on user inputs:
    - foods: list of food names
    - calories_min: minimum total calories
    - protein_min: minimum total protein (g)
    - ratio_min: minimum fat-to-protein ratio
    - objective_function_type: integer index for optimization objective
    """
    data = request.get_json(silent=True) or {}
    foods_list = data.get('foods') or []
    if not isinstance(foods_list, list):
        return jsonify({"error": "`foods` must be an array"}), 400
    if len(foods_list) == 0:
        return jsonify({"error": "Please select at least one food"}), 400

    try:
        # Initialize optimizer
        meal = Opti_Meal(meal_name="User Meal")
        meal.set_debug(False)

        # Add each selected food
        for fname in foods_list:
            rows = food_df[food_df[food_col] == fname]
            if rows.empty:
                continue
            r = rows.iloc[0]
            # Create a Food_Type with per-gram nutrient ratios
            ft = Food_Type(
                name=r[food_col],
                fat_gram_ratio=safe_float(r[fat_col]) / 100.0,
                protein_gram_ratio=safe_float(r[prot_col]) / 100.0,
                carbs_gram_ratio=safe_float(r[carbs_col]) / 100.0,
                cal_gram_ratio=safe_float(r[cal_col]) / 100.0,
                ml_gram_ratio=1.0  # default volume ratio
            )
            meal.add_food_type(ft)
            meal.add_opti_ingredient(new_opti_ingredient=ft.get_name())

        # Apply nutritional constraints
        meal.set_calories_minimum(safe_float(data.get('calories_min')))
        meal.set_protein_grams_minimum(safe_float(data.get('protein_min')))
        meal.set_ratio_minimum(safe_float(data.get('ratio_min')))

        # Solve optimization
        success = meal.optimize()
        if not success:
            return jsonify({"error": "No feasible solution found under those constraints."}), 400

        # Build response
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
        # Return any unexpected errors as JSON
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    # Start the Flask app on port 5050
    app.run(host='0.0.0.0', port=5050)
