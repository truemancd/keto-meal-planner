# imports 
import  math 
from cvxopt.modeling import op, dot, variable, min, max, sum
from cvxopt import matrix, solvers


# A data structure representing an individual kind of food.
# All of its values (save the name) are unchanging real physical characteristics of that actual food.
# As such, no value should be changed after being set on initialization!
#
# TODO range checks?
class Food_Type: 
    
    # Constructor! Takes in:
    #   name                # An identifier for the food type
    #   fat_gram_ratio      # how many grams of fat there are for each gram of the food type
    #   protein_gram_ratio  # how many grams of protein there are for each gram of the food type 
    #   carbs_gram_ratio    # how many grams of carbs there are for each gram of the food type
    #   cal_gram_ratio      # how many calories there are for each gram of the food type
    #   ml_gram_ratio       # how many milliliters each gram of the food type takes up 
    def __init__(
                  self              ,
                  name              ,
                  fat_gram_ratio    ,
                  protein_gram_ratio,
                  carbs_gram_ratio  ,
                  cal_gram_ratio    ,
                  ml_gram_ratio     
                ):
        
        self.__name                    = name
        self.__grams_fat_per_gram      = fat_gram_ratio
        self.__grams_protein_per_gram  = protein_gram_ratio
        self.__grams_carbs_per_gram    = carbs_gram_ratio
        self.__calories_per_gram       = cal_gram_ratio
        self.__milliliters_per_gram    = ml_gram_ratio   

    # getter; return the identifier for the food type 
    def get_name(self):
        return self.__name

    # getter; return the fat-by-mass of the food type (grams fat / grams food type)
    def get_fat_gram_ratio(self):
        return self.__grams_fat_per_gram

    # getter; return the protein-by-mass of the food type (grams protein / grams food type)
    def get_protein_gram_ratio(self):
        return self.__grams_protein_per_gram

    # getter; return the carbs-by-mass of the food type (grams carbs / grams food type)
    def get_carbs_gram_ratio(self):
        return self.__grams_carbs_per_gram

    # getter; return the calories-by-mass of the food type (calories / grams food type)
    def get_cal_gram_ratio(self):
        return self.__calories_per_gram

    # getter; return the specific volume of the food type (milliliters food / grams food type)
    def get_ml_gram_ratio(self):
        return self.__milliliters_per_gram


# A data structure representing a piece of a meal to be optimized. Associates a specific food's physical characteristics (a Food_Type)
# with ingredient-specific optimization features (minimum and maximum grams, actual amount, inclusion in objective function calculation, etc.)
#
# TODO range checking? making sure no one submits a value above __OPTIMIZER_MAX?
class Opti_Ingredient:

    # the optimizer complains if we just use the float max
    __OPTIMIZER_MAX = 1e8
    
    # Constructor! Takes in: 
    #   food_type                       # a Food_Type object representing what food this ingredient is
    #   debug                           # detailed issue reporting flag 
    #   grams_minimum                   # lower limit for mass of ingredient present in the optimized meal 
    #   grams_maximum                   # upper limit for mass of ingredient present in the optimized meal 
    #   included_in_objective_function  # boolean representing whether the objective function will care about this ingredient at all 
    #   points_per_gram                 # subjective "value" of the ingredient, for alternative optimization
    #   target_grams                    # the centerline from which the final amount of this ingredient is to be measured
    #   name                            # An identifier for the ingredient 
    def __init__(
                  self                                                  ,
                  food_type                                             ,
                  debug                             = False             ,   
                  grams_minimum                     = 0.0               ,   # default to the logical physical minimum
                  grams_maximum                     = __OPTIMIZER_MAX   ,   # default to effectively no maximum
                  included_in_objective_function    = True              ,   # include everything in the objective calc by default
                  points_per_gram                   = 0.0               ,   # no point default 
                  target_grams                      = 0.0               ,   # compare everything against zero by default 
                  name                              = "Default"             # the name will default to the Food_Type name unless otherwise specified 
                ):

        # these shouldn't change after initialization
        self.__debug                        = debug

        # if you didn't get a valid Food_Type object, complain and create a default one 
        if not isinstance(food_type, Food_Type):
            if self.__debug:
                print("\nERROR: tried to create an Opti_Ingredient without a food type. Creating empty food instead...")
            food_type = Food_Type(
                                      name                  = "ERROR RESULT EMPTY FOOD" ,
                                      fat_gram_ratio        = 0.0                       ,
                                      protein_gram_ratio    = 0.0                       ,
                                      carbs_gram_ratio      = 0.0                       ,
                                      cal_gram_ratio        = 0.0                       ,
                                      ml_gram_ratio         = 0.0
                                 )
            
        self.__food_type                    = food_type                   

        if name == "Default":
            self.__name                     = self.__food_type.get_name()
        else:
            self.__name                     = name

        # pre-set max to allow the min range-checking to happen cleanly 
        self.__grams_maximum                = self.__OPTIMIZER_MAX
        
        # use the setters for these to be clean for potential future checking 
        self.set_grams_minimum(grams_minimum)
        self.set_grams_maximum(grams_maximum)    
        self.set_use_in_objective_function(included_in_objective_function)
        self.set_points_per_gram(points_per_gram)
        self.set_target_grams(target_grams)

        # this is just a storage space that will eventually hold the optimal answer, for cleanliness 
        self.set_grams(0.0)  


    # setter; pick the lower grams limit for the optimized value of this ingredient. Complains on nonphyscial (i.e. negative) values and ignores.
    # if the upper grams limit is exceeded, complains, then sets maximum to match. 
    def set_grams_minimum(self, new_grams_minimum):
        if new_grams_minimum < 0.0 and self.__debug: 
            print("\nWARNING: tried to set nonphysical minimum", new_grams_minimum, "for Opti_Ingredient", self.__name, ". Ignoring!")
        elif new_grams_minimum > self.__grams_maximum:
            if self.__debug:
                print("\nWARNING: set minimum exceeding maximum for Opti_Ingredient", self.__name, ". Setting maximum to match!")
            self.__grams_minimum = new_grams_minimum
            self.set_grams_maximum(new_grams_minimum)
        else:
            self.__grams_minimum = new_grams_minimum

    # setter; pick the upper grams limit for the optimized value of this ingredient. Complains on nonphyscial (i.e. negative) values and ignores.
    # if the lower grams limit is undercut, complains, then sets minimum to match. 
    def set_grams_maximum(self, new_grams_maximum):
        if new_grams_maximum < 0.0 and self.__debug: 
            print("\nWARNING: tried to set nonphysical maximum", new_grams_maximum, "for Opti_Ingredient", self.__name, ". Ignoring!")
        elif new_grams_maximum < self.__grams_minimum:
            if self.__debug:
                print("\nWARNING: set maximum undercutting minimum for Opti_Ingredient", self.__name, ". Setting minimum to match!")
            self.__grams_maximum = new_grams_maximum
            self.set_grams_minimum(new_grams_maximum)
        else:
            self.__grams_maximum = new_grams_maximum

    # setter; mark this ingredient as to whether it should be included in the objective function calculation or not  
    def set_use_in_objective_function(self, new_use_in_objective_function):
        self.__use_in_objective_function = new_use_in_objective_function

    # setter; choose arbitary reward value for grams of this ingredient
    # TODO are negative points allowed? are those useful?
    def set_points_per_gram(self, new_points_per_gram):
        self.__points_per_gram = new_points_per_gram

    # setter; choose baseline from which to calculate differences for this ingredient. Complains on nonphyscial (i.e. negative) values and ignores.
    # (e.g., the objective function will minimize the difference between the optimized grams of this ingredient and this number)
    def set_target_grams(self, new_target_grams):
        if new_target_grams < 0.0 and self.__debug: 
            print("\nWARNING: tried to set nonphysical target", new_target_grams, "for Opti_Ingredient", self.__name, ". Ignoring!")
        else:
            self.__target_grams = new_target_grams

    # setter; pick how many grams of this ingredient are actually present in the final meal.
    # A post-facto storage space for the optimizer to make things clean, not a pre-facto value that actually affects the optimization.
    # turns nonphysical values into zero (assuming rounding issues) 
    def set_grams(self, new_grams):
        if new_grams < 0.0 : 
            self.__grams = 0.0
        else:
            self.__grams = new_grams

    # getter; return the underlying Food_Type object 
    def get_food_type(self):
        return self.__food_type

    # getter; return the lower bounds for the mass of this ingredient 
    def get_grams_minimum(self):
        return self.__grams_minimum

    # getter; return the upper bounds for the mass of this ingredient 
    def get_grams_maximum(self):
        return self.__grams_maximum

    # getter; return whether the objective function should care about this ingredient 
    def get_use_in_objective_function(self):
        return self.__use_in_objective_function

    # getter; return the arbitrary reward rate for this ingredient 
    def get_points_per_gram(self):
        return self.__points_per_gram
    
    # getter; return the mass baseline for this ingredient 
    def get_target_grams(self):
        return self.__target_grams
                
    # getter; return the identifier for this ingredient 
    def get_name(self):
        return self.__name

    # getter; return the current actual amount of this ingredient  
    def get_grams(self):
        return self.__grams


# A data structure representing a meal to be optimized (and in what way) for a large set of given conditions and constraints 
class Opti_Meal:

    # the optimizer complains if we just use the float max
    __OPTIMIZER_MAX = 1e8
    
    # Constructor! Takes in: 
    #   meal_name                                   # a name to use to refer to the meal
    #   debug                                       # control for error and status printouts
    #   food_type_filename                          # a file containing CSV represented food types TODO NO-OP
    #   starting_opti_ingredients                   # a list of Opti_Ingredient objects to be included in the meal 
    #   objective_function_type                     # 0 == nothing, 1 == minimize, 2 == maximize, 3 == minimize the maximum (min-max), 4 == maximize the minimum (max-min)
    #   fat_grams_minimum                           # constraint controlling how low total fat can go, in grams  
    #   fat_grams_maximum                           # constraint controlling how high total fat can go, in grams
    #   protein_grams_minimum                       # constraint controlling how low total protein can go, in grams  
    #   protein_grams_maximum                       # constraint controlling how high total protein can go, in grams 
    #   carbs_grams_minimum                         # constraint controlling how low total carbs can go, in grams 
    #   carbs_grams_maximum                         # constraint controlling how high total carbs can go, in grams  
    #   calories_minimum                            # constraint controlling how low total calories can go, in calories
    #   calories_maximum                            # constraint controlling how high total calories can go, in calories
    #   milliliters_minimum                         # constraint controlling how low total volume can go, in milliliters 
    #   milliliters_maximum                         # constraint controlling how high total volume can go, in milliliters 
    #   ratio_minimum                               # constraint controlling how low the nutrient ratio can go
    #   ratio_maximum                               # constraint controlling how high the nutrient ratio can go
    #   rounding_digits                             # how many decimal places to show in the final gram values 
    #   use_points_in_objective_function            # controls whether to evaluate ingredients by grams or by user-defined points 
    #   use_total_fat_in_objective_function         # controls whether to include total fat amount (in grams) in the objective function
    #   use_total_protein_in_objective_function     # controls whether to include total protein amount (in grams) in the objective function
    #   use_total_carbs_in_objective_function       # controls whether to include total carbs amount (in grams) in the objective function
    #   use_total_calories_in_objective_function    # controls whether to include total calorie amount (in calories) in the objective function
    #   use_total_volume_in_objective_function      # controls whether to include total volume (in milliliters) in the objective function
    #   use_ratio_in_objective_function             # controls whether to include the value of the nutrient ratio in the objective function        
    def __init__(
                    self                                                            ,
                    meal_name                                   = "Default"         ,
                    debug                                       = False             ,
                    food_type_filename                          = ""                ,
                    starting_opti_ingredients                   = None              ,
                    objective_function_type                     = 0                 ,  
                    fat_grams_minimum                           = 0.0               ,   
                    fat_grams_maximum                           = __OPTIMIZER_MAX   ,  
                    protein_grams_minimum                       = 0.0               ,   
                    protein_grams_maximum                       = __OPTIMIZER_MAX   ,  
                    carbs_grams_minimum                         = 0.0               ,   
                    carbs_grams_maximum                         = __OPTIMIZER_MAX   ,  
                    calories_minimum                            = 0.0               ,  
                    calories_maximum                            = __OPTIMIZER_MAX   ,  
                    milliliters_minimum                         = 0.0               ,   
                    milliliters_maximum                         = __OPTIMIZER_MAX   ,   
                    ratio_minimum                               = 0.0               ,  
                    ratio_maximum                               = __OPTIMIZER_MAX   ,   
                    rounding_digits                             = 2                 ,   # what the online keto calc currently can take
                    use_points_in_objective_function            = False             ,
                    use_total_fat_in_objective_function         = False             ,
                    use_total_protein_in_objective_function     = False             ,
                    use_total_carbs_in_objective_function       = False             ,
                    use_total_calories_in_objective_function    = False             ,
                    use_total_volume_in_objective_function      = False             ,
                    use_ratio_in_objective_function             = False             
                ):
        
        self.__name                     = meal_name

        self.set_debug(debug)

        self.__food_type_dict           = {}

        if food_type_filename != "":
            self.load_food_type_file(food_type_filename)

        self.__opti_ingredients_dict    = {}
        if starting_opti_ingredients != None:
            for ingredient in starting_opti_ingredients:
                add_opti_ingredient(ingredient)

        # range checking for the objective function types; could be more elegant 
        self.__NUM_OBJECTIVE_FUNCTION_TYPES = 5 
    
        # pre-set max to allow the min range-checking to happen cleanly 
        self.__fat_grams_maximum        = self.__OPTIMIZER_MAX
        self.__protein_grams_maximum    = self.__OPTIMIZER_MAX
        self.__carbs_grams_maximum      = self.__OPTIMIZER_MAX
        self.__calories_maximum         = self.__OPTIMIZER_MAX
        self.__milliliters_maximum      = self.__OPTIMIZER_MAX     
        self.__ratio_maximum            = self.__OPTIMIZER_MAX

        # use our own methods to set everything!
        self.set_objective_function_type(objective_function_type)
        self.set_fat_grams_minimum(fat_grams_minimum) 
        self.set_fat_grams_maximum(fat_grams_maximum)
        self.set_protein_grams_minimum(protein_grams_minimum)
        self.set_protein_grams_maximum(protein_grams_maximum)
        self.set_carbs_grams_minimum(carbs_grams_minimum) 
        self.set_carbs_grams_maximum(carbs_grams_maximum)
        self.set_calories_minimum(calories_minimum)
        self.set_calories_maximum(calories_maximum)
        self.set_milliliters_minimum(milliliters_minimum)
        self.set_milliliters_maximum(milliliters_maximum)       
        self.set_ratio_minimum(ratio_minimum) 
        self.set_ratio_maximum(ratio_maximum)       
        self.set_rounding_digits(rounding_digits)          
        self.set_use_points_in_objective_function(use_points_in_objective_function)
        self.set_use_total_fat_in_objective_function(use_total_fat_in_objective_function)
        self.set_use_total_protein_in_objective_function(use_total_protein_in_objective_function)
        self.set_use_total_carbs_in_objective_function(use_total_carbs_in_objective_function)
        self.set_use_total_calories_in_objective_function(use_total_calories_in_objective_function)
        self.set_use_total_volume_in_objective_function(use_total_volume_in_objective_function)
        self.set_use_ratio_in_objective_function(use_ratio_in_objective_function)


    # TODO TODO def load_food_type_file() 

    # Include a new ingredient in the meal to be optimized TODO more comments TODO also, like, finish it I guess 
    def add_opti_ingredient(
                                self                                    ,
                                new_opti_ingredient                     ,
                                grams_minimum                     = None,   
                                grams_maximum                     = None,   
                                use_in_objective_function         = None,   
                                points_per_gram                   = None,   
                                target_grams                      = None                  
                           ):

        # if we got passed a string, assume it's a known Food Type  
        if isinstance(new_opti_ingredient, str):
            # if this food type isn't new(i.e, if we found it) use it 
            if self.__food_type_dict.get(new_opti_ingredient) != None:
                new_opti_ingredient = self.__food_type_dict.get(new_opti_ingredient)    
            elif self.__debug:
                print("\nWARNING: unknown Food_Type name", new_opti_ingredient ,"referenced. Ignoring!")

        # if we got passed a Food_Type (or looked one up), add it to our dict if we didn't already have it, then make it into a new ingredient  
        if isinstance(new_opti_ingredient, Food_Type):
            # add it if its new
            if self.__food_type_dict.get(new_opti_ingredient.get_name()) == None:
                self.add_food_type(new_opti_ingredient)
            # simple initialization to get the defaults set
            new_opti_ingredient = Opti_Ingredient(new_opti_ingredient, self.__debug) 

        # if we got passed an Opti_Ingredient (or just made one) check redundancy, then use it 
        if isinstance(new_opti_ingredient, Opti_Ingredient):
            # if this Opti_Ingredient is new
            if self.__opti_ingredients_dict.get(new_opti_ingredient.get_name()) == None:           
                # set specifics if there are any 
                if grams_minimum                != None:
                    new_opti_ingredient.set_grams_minimum(grams_minimum)
                if grams_maximum                != None:
                    new_opti_ingredient.set_grams_maximum(grams_maximum)
                if use_in_objective_function    != None:
                    new_opti_ingredient.set_use_in_objective_function(use_in_objective_function)
                if points_per_gram              != None:
                    new_opti_ingredient.set_points_per_gram(points_per_gram)
                if target_grams                 != None:
                    new_opti_ingredient.set_target_grams(target_grams)
                # add it!
                self.__opti_ingredients_dict[(new_opti_ingredient.get_name())] = new_opti_ingredient
            # if someone's tried to make an already-existing ingredient 
            elif self.__debug:
                print("\nWARNING: tried to add ingredient", new_opti_ingredient.get_name() ,"that was already added. Ignoring!")
        elif self.__debug:
            print("\nWARNING: tried to add non-compatible type as an Opti_Ingredient. Ignoring!")

    # Include food-physical-characteristics object (Food_Type) to this meal's internal dictionary of possible foods.
    # Complain and ignore if the Food_Type isn't actually new (as decided by its name) 
    def add_food_type(self, new_food_type):
        if isinstance(new_food_type, Food_Type): 
            # if this Food_Type is new 
            if self.__food_type_dict.get(new_food_type.get_name()) == None:       
                self.__food_type_dict[(new_food_type.get_name())] = new_food_type
            # otherwise, complain
            elif self.__debug:
                print("\nWARNING: tried to add food type", new_food_type.get_name() ,"that was already added. Ignoring!")
        elif self.__debug:
            print("\nWARNING: tried to add non-compatible type as a Food_Type. Ignoring!")
        
    # Setter; choose which objective function to use 
    def set_objective_function_type(self, new_objective_function_type):
        if ( ( ( new_objective_function_type < 0 ) or ( self.__NUM_OBJECTIVE_FUNCTION_TYPES <= new_objective_function_type ) ) and
            self.__debug ):                                          
            print("\nWARNING: tried pick a nonexistant objective_function_type. Ignoring!")
        else:
            self.__objective_function_type          = new_objective_function_type

    # setter; pick the lower fat grams limit for the optimized value of this meal. Complains on nonphysical (i.e. negative) values and ignores.
    # if the upper fat grams limit is exceeded, complains, then sets maximum to match. 
    def set_fat_grams_minimum(self, new_fat_grams_minimum):
        if new_fat_grams_minimum < 0.0 and self.__debug: 
            print("\nWARNING: tried to set nonphysical fat grams minimum", new_fat_grams_minimum, ". Ignoring!")
        elif new_fat_grams_minimum > self.__fat_grams_maximum:
            if self.__debug:
                print("\nWARNING: set fat grams minimum exceeding maximum; setting maximum to match!")
            self.__fat_grams_minimum = new_fat_grams_minimum
            self.set_fat_grams_maximum(new_fat_grams_minimum)
        else:
            self.__fat_grams_minimum = new_fat_grams_minimum

    # setter; pick the upper fat grams limit for the optimized value of this ingredient. Complains on nonphysical (i.e. negative) values and ignores.
    # if the lower fat grams limit is undercut, complains, then sets minimum to match. 
    def set_fat_grams_maximum(self, new_fat_grams_maximum):
        if new_fat_grams_maximum < 0.0 and self.__debug: 
            print("\nWARNING: tried to set nonphysical fat grams maximum", new_fat_grams_maximum, ". Ignoring!")
        elif new_fat_grams_maximum < self.__fat_grams_minimum:
            if self.__debug:
                print("\nWARNING: set fat grams maximum undercutting minimum; setting minimum to match!")
            self.__fat_grams_maximum = new_fat_grams_maximum
            self.set_fat_grams_minimum(new_fat_grams_maximum)
        else:
            self.__fat_grams_maximum = new_fat_grams_maximum

    # setter; pick the lower protein grams limit for the optimized value of this meal. Complains on nonphysical (i.e. negative) values and ignores.
    # if the upper protein grams limit is exceeded, complains, then sets maximum to match. 
    def set_protein_grams_minimum(self, new_protein_grams_minimum):
        if new_protein_grams_minimum < 0.0 and self.__debug: 
            print("\nWARNING: tried to set nonphysical protein grams minimum", new_protein_grams_minimum, ". Ignoring!")
        elif new_protein_grams_minimum > self.__protein_grams_maximum:
            if self.__debug:
                print("\nWARNING: set protein grams minimum exceeding maximum; setting maximum to match!")
            self.__protein_grams_minimum = new_protein_grams_minimum
            self.set_protein_grams_maximum(new_protein_grams_minimum)
        else:
            self.__protein_grams_minimum = new_protein_grams_minimum

    # setter; pick the upper protein grams limit for the optimized value of this ingredient. Complains on nonphysical (i.e. negative) values and ignores.
    # if the lower protein grams limit is undercut, complains, then sets minimum to match. 
    def set_protein_grams_maximum(self, new_protein_grams_maximum):
        if new_protein_grams_maximum < 0.0 and self.__debug: 
            print("\nWARNING: tried to set nonphysical protein grams maximum", new_protein_grams_maximum, ". Ignoring!")
        elif new_protein_grams_maximum < self.__protein_grams_minimum:
            if self.__debug:
                print("\nWARNING: set protein grams maximum undercutting minimum; setting minimum to match!")
            self.__protein_grams_maximum = new_protein_grams_maximum
            self.set_protein_grams_minimum(new_protein_grams_maximum)
        else:
            self.__protein_grams_maximum = new_protein_grams_maximum

    # setter; pick the lower carbs grams limit for the optimized value of this meal. Complains on nonphysical (i.e. negative) values and ignores.
    # if the upper carbs grams limit is exceeded, complains, then sets maximum to match. 
    def set_carbs_grams_minimum(self, new_carbs_grams_minimum):
        if new_carbs_grams_minimum < 0.0 and self.__debug: 
            print("\nWARNING: tried to set nonphysical carbs grams minimum", new_carbs_grams_minimum, ". Ignoring!")
        elif new_carbs_grams_minimum > self.__carbs_grams_maximum:
            if self.__debug:
                print("\nWARNING: set carbs grams minimum exceeding maximum; setting maximum to match!")
            self.__carbs_grams_minimum = new_carbs_grams_minimum
            self.set_carbs_grams_maximum(new_carbs_grams_minimum)
        else:
            self.__carbs_grams_minimum = new_carbs_grams_minimum

    # setter; pick the upper carbs grams limit for the optimized value of this ingredient. Complains on nonphysical (i.e. negative) values and ignores.
    # if the lower carbs grams limit is undercut, complains, then sets minimum to match. 
    def set_carbs_grams_maximum(self, new_carbs_grams_maximum):
        if new_carbs_grams_maximum < 0.0 and self.__debug: 
            print("\nWARNING: tried to set nonphysical carbs grams maximum", new_carbs_grams_maximum, ". Ignoring!")
        elif new_carbs_grams_maximum < self.__carbs_grams_minimum:
            if self.__debug:
                print("\nWARNING: set carbs grams maximum undercutting minimum; setting minimum to match!")
            self.__carbs_grams_maximum = new_carbs_grams_maximum
            self.set_carbs_grams_minimum(new_carbs_grams_maximum)
        else:
            self.__carbs_grams_maximum = new_carbs_grams_maximum

    # setter; pick the lower calories limit for the optimized value of this meal. Complains on nonphysical (i.e. negative) values and ignores.
    # if the upper carbs grams limit is exceeded, complains, then sets maximum to match. 
    def set_calories_minimum(self, new_calories_minimum):
        if new_calories_minimum < 0.0 and self.__debug: 
            print("\nWARNING: tried to set nonphysical calories minimum", new_calories_minimum, ". Ignoring!")
        elif new_calories_minimum > self.__calories_maximum:
            if self.__debug:
                print("\nWARNING: set calories minimum exceeding maximum; setting maximum to match!")
            self.__calories_minimum = new_calories_minimum
            self.set_calories_maximum(new_calories_minimum)
        else:
            self.__calories_minimum = new_calories_minimum

    # setter; pick the upper calories limit for the optimized value of this ingredient. Complains on nonphysical (i.e. negative) values and ignores.
    # if the lower carbs grams limit is undercut, complains, then sets minimum to match. 
    def set_calories_maximum(self, new_calories_maximum):
        if new_calories_maximum < 0.0 and self.__debug: 
            print("\nWARNING: tried to set nonphysical calories maximum", new_calories_maximum, ". Ignoring!")
        elif new_calories_maximum < self.__calories_minimum:
            if self.__debug:
                print("\nWARNING: set calories maximum undercutting minimum; setting minimum to match!")
            self.__calories_maximum = new_calories_maximum
            self.set_calories_minimum(new_calories_maximum)
        else:
            self.__calories_maximum = new_calories_maximum
            
    # setter; pick the lower milliliters limit for the optimized value of this meal. Complains on nonphysical (i.e. negative) values and ignores.
    # if the upper carbs grams limit is exceeded, complains, then sets maximum to match. 
    def set_milliliters_minimum(self, new_milliliters_minimum):
        if new_milliliters_minimum < 0.0 and self.__debug: 
            print("\nWARNING: tried to set nonphysical milliliters minimum", new_milliliters_minimum, ". Ignoring!")
        elif new_milliliters_minimum > self.__milliliters_maximum:
            if self.__debug:
                print("\nWARNING: set milliliters minimum exceeding maximum; setting maximum to match!")
            self.__milliliters_minimum = new_milliliters_minimum
            self.set_milliliters_maximum(new_milliliters_minimum)
        else:
            self.__milliliters_minimum = new_milliliters_minimum

    # setter; pick the upper milliliters limit for the optimized value of this ingredient. Complains on nonphysical (i.e. negative) values and ignores.
    # if the lower carbs grams limit is undercut, complains, then sets minimum to match. 
    def set_milliliters_maximum(self, new_milliliters_maximum):
        if new_milliliters_maximum < 0.0 and self.__debug: 
            print("\nWARNING: tried to set nonphysical milliliters maximum", new_milliliters_maximum, ". Ignoring!")
        elif new_milliliters_maximum < self.__milliliters_minimum:
            if self.__debug:
                print("\nWARNING: set milliliters maximum undercutting minimum; setting minimum to match!")
            self.__milliliters_maximum = new_milliliters_maximum
            self.set_milliliters_minimum(new_milliliters_maximum)
        else:
            self.__milliliters_maximum = new_milliliters_maximum
            
    # setter; pick the lower ratio limit for the optimized value of this meal. Complains on nonphysical (i.e. negative) values and ignores.
    # if the upper carbs grams limit is exceeded, complains, then sets maximum to match. 
    def set_ratio_minimum(self, new_ratio_minimum):
        if new_ratio_minimum < 0.0 and self.__debug: 
            print("\nWARNING: tried to set nonphysical ratio minimum", new_ratio_minimum, ". Ignoring!")
        elif new_ratio_minimum > self.__ratio_maximum:
            if self.__debug:
                print("\nWARNING: set ratio minimum exceeding maximum; setting maximum to match!")
            self.__ratio_minimum = new_ratio_minimum
            self.set_ratio_maximum(new_ratio_minimum)
        else:
            self.__ratio_minimum = new_ratio_minimum

    # setter; pick the upper ratio limit for the optimized value of this ingredient. Complains on nonphysical (i.e. negative) values and ignores.
    # if the lower carbs grams limit is undercut, complains, then sets minimum to match. 
    def set_ratio_maximum(self, new_ratio_maximum):
        if new_ratio_maximum < 0.0 and self.__debug: 
            print("\nWARNING: tried to set nonphysical ratio maximum", new_ratio_maximum, ". Ignoring!")
        elif new_ratio_maximum < self.__ratio_minimum:
            if self.__debug:
                print("\nWARNING: set ratio maximum undercutting minimum; setting minimum to match!")
            self.__ratio_maximum = new_ratio_maximum
            self.set_ratio_minimum(new_ratio_maximum)
        else:
            self.__ratio_maximum = new_ratio_maximum

    # Setter; choose how many digits post decimal point to display in prints
    def set_rounding_digits(self, new_rounding_digits):
        # TODO range checking but I'm too lazy rn 
        self.__rounding_digits          = new_rounding_digits

    # Setter; choose debug mode
    def set_debug(self, new_debug):
        if new_debug:
            self.__debug = True
        else:
            self.__debug = False
        
    # Setter; choose whether optimization items are factored into the objective function by grams or by user-assigned points 
    def set_use_points_in_objective_function(self, new_use_points_in_objective_function):
        if new_use_points_in_objective_function:
            self.__use_points_in_objective_function = True
        else:
            self.__use_points_in_objective_function = False

    # Setter; choose whether total fat is also considered in the computation of the objective function 
    def set_use_total_fat_in_objective_function(self, new_use_total_fat_in_objective_function):
        if new_use_total_fat_in_objective_function:
            self.__use_total_fat_in_objective_function = True
        else:
            self.__use_total_fat_in_objective_function = False
            
    # Setter; choose whether total protein is also considered in the computation of the objective function 
    def set_use_total_protein_in_objective_function(self, new_use_total_protein_in_objective_function):
        if new_use_total_protein_in_objective_function:
            self.__use_total_protein_in_objective_function = True
        else:
            self.__use_total_protein_in_objective_function = False

    # Setter; choose whether total carbs are also considered in the computation of the objective function 
    def set_use_total_carbs_in_objective_function(self, new_use_total_carbs_in_objective_function):
        if new_use_total_carbs_in_objective_function:
            self.__use_total_carbs_in_objective_function = True
        else:
            self.__use_total_carbs_in_objective_function = False

    # Setter; choose whether total calories are also considered in the computation of the objective function 
    def set_use_total_calories_in_objective_function(self, new_use_total_calories_in_objective_function):
        if new_use_total_calories_in_objective_function:
            self.__use_total_calories_in_objective_function = True
        else:
            self.__use_total_calories_in_objective_function = False

    # Setter; choose whether total volume is also considered in the computation of the objective function 
    def set_use_total_volume_in_objective_function(self, new_use_total_volume_in_objective_function):
        if new_use_total_volume_in_objective_function:
            self.__use_total_volume_in_objective_function = True
        else:
            self.__use_total_volume_in_objective_function = False

    # Setter; choose whether the nutrient ratio is also considered in the computation of the objective function 
    def set_use_ratio_in_objective_function(self, new_use_ratio_in_objective_function):
        if new_use_ratio_in_objective_function:
            self.__use_ratio_in_objective_function = True
        else:
            self.__use_ratio_in_objective_function = False
            
    # Optimize ingredient amounts via convex optimization to satisfy all given 
    # constraints and "score" as highly on the chosen objective function as possible.
    # Returns a boolean indicating success
    def optimize(self):

        # start by initializating our optimization 
        optimization = op()

        # create our variables - the number of grams of each ingredient 
        opt_food_grams = variable(len(self.__opti_ingredients_dict)) 

        # make lists to organize values  
        ingredient_minima               = []
        ingredient_maxima               = []
        gram_targets                    = []
        points_per_gram                 = []
        use_in_objective_function_flags = []
                                             
        fat_gram_ratios                 = []
        protein_gram_ratios             = []
        carbs_gram_ratios               = []
        cal_gram_ratios                 = []
        ml_gram_ratios                  = []

        # build all the relevant matricies in one for loop  
        for ingredient in self.__opti_ingredients_dict.values():
            ingredient_minima.append                        ( ingredient.get_grams_minimum()                            )
            ingredient_maxima.append                        ( ingredient.get_grams_maximum()                            ) 
            gram_targets.append                             ( ingredient.get_target_grams()                             )
            points_per_gram.append                          ( ingredient.get_points_per_gram()                          )                                             
            if ingredient.get_use_in_objective_function():
                use_in_objective_function_flags.append      ( 1.0                                                       )
            else:
                use_in_objective_function_flags.append      ( 0.0                                                       )
                                             
            fat_gram_ratios.append                          ( ingredient.get_food_type().get_fat_gram_ratio()           )
            protein_gram_ratios.append                      ( ingredient.get_food_type().get_protein_gram_ratio()       )
            carbs_gram_ratios.append                        ( ingredient.get_food_type().get_carbs_gram_ratio()         )
            cal_gram_ratios.append                          ( ingredient.get_food_type().get_cal_gram_ratio()           )
            ml_gram_ratios.append                           ( ingredient.get_food_type().get_ml_gram_ratio()            )
                                             
        # add physicality constraint (i.e. non-negative constraint) 
        optimization.addconstraint( opt_food_grams >= 0 )

        # add ingredient-wise minimum amount constraint 
        optimization.addconstraint( matrix(ingredient_minima) <= opt_food_grams )

        # add ingredient-wise maximum amount constraint
        optimization.addconstraint( opt_food_grams <= matrix(ingredient_maxima) )

        # add total fat minimum constraint 
        optimization.addconstraint( self.__fat_grams_minimum <= dot(matrix(fat_gram_ratios), opt_food_grams)  )

        # add total fat maximum constraint 
        optimization.addconstraint( dot(matrix(fat_gram_ratios), opt_food_grams) <= self.__fat_grams_maximum )                                             

        # add total protein minimum constraint
        optimization.addconstraint( self.__protein_grams_minimum <= dot(matrix(protein_gram_ratios), opt_food_grams)  )

        # add total protein maximum constraint 
        optimization.addconstraint( dot(matrix(protein_gram_ratios), opt_food_grams) <= self.__protein_grams_maximum ) 

        # add total carbs minimum constraint 
        optimization.addconstraint( self.__carbs_grams_minimum <= dot(matrix(carbs_gram_ratios), opt_food_grams)  )

        # add total carbs maximum constraint 
        optimization.addconstraint( dot(matrix(carbs_gram_ratios), opt_food_grams) <= self.__carbs_grams_maximum )
                                             
        # add total calories minimum constraint 
        optimization.addconstraint( self.__calories_minimum <= dot(matrix(cal_gram_ratios), opt_food_grams)  )

        # add total calories maximum constraint 
        optimization.addconstraint( dot(matrix(cal_gram_ratios), opt_food_grams) <= self.__calories_maximum )

        # add total volume minimum constraint 
        optimization.addconstraint( self.__milliliters_minimum <= dot(matrix(ml_gram_ratios), opt_food_grams)  )

        # add total volume maximum constraint 
        optimization.addconstraint( dot(matrix(ml_gram_ratios), opt_food_grams) <= self.__milliliters_maximum )

        # add minimum nutrient ratio constraint 
        optimization.addconstraint(
                                    ( dot(matrix(protein_gram_ratios), opt_food_grams) + dot(matrix(carbs_gram_ratios), opt_food_grams) ) *
                                    self.__ratio_minimum                                                                                    <=
                                    dot(matrix(fat_gram_ratios), opt_food_grams) 
                                  )

        # add maximum nutrient ratio constraint 
        optimization.addconstraint(
                                    dot(matrix(fat_gram_ratios), opt_food_grams) <=
                                    ( dot(matrix(protein_gram_ratios), opt_food_grams) + dot(matrix(carbs_gram_ratios), opt_food_grams)) *
                                    self.__ratio_maximum                                                                                    
                                  )

        #
        # start building the objective function
        #

        # start with nothing           
        objective_function = [0.0]

        # append in special values if relevant, non-food-amount components of the objective function 
        if self.__use_total_fat_in_objective_function:
            objective_function.append( dot(matrix(fat_gram_ratios), opt_food_grams) )
        if self.__use_total_protein_in_objective_function:
            objective_function.append( dot(matrix(protein_gram_ratios), opt_food_grams) )
        if self.__use_total_carbs_in_objective_function:
            objective_function.append( dot(matrix(carbs_gram_ratios), opt_food_grams) )
        if self.__use_total_calories_in_objective_function:
            objective_function.append( dot(matrix(cal_gram_ratios), opt_food_grams) )
        if self.__use_total_volume_in_objective_function:
            objective_function.append( dot(matrix(ml_gram_ratios), opt_food_grams) )
        if self.__use_ratio_in_objective_function:
            objective_function.append( dot(matrix(fat_gram_ratios), opt_food_grams) )
            objective_function.append( -1* ( dot(matrix(protein_gram_ratios), opt_food_grams) + dot(matrix(carbs_gram_ratios), opt_food_grams) ) )
                                     
        # append in all the food amount components of the objective function (with respect to if we're using them, what we're comparing them to,
        # whether we're in "points mode", etc) 
        for gram_value, flag, gram_target, point_gram_ratio in zip(opt_food_grams, use_in_objective_function_flags, gram_targets, points_per_gram):
            # as long as we're using this component 
            if flag:

                # get the absolute difference between the optimized value and what we want it to be (its target)
                temp_val = abs(gram_target - gram_value)

                # implement using points, if we're doing that 
                if self.__use_points_in_objective_function:
                    temp_val *= point_gram_ratio

                # include the result in the objective function list we're building 
                objective_function.append(temp_val)

        # implement the overall objective function type from the list we've built,
        # reducing the list to a single value
        #
        # NB: Remember, the library always drives to minimize the objective function as a base case
        # NB: we hack a "maximization" by still trying to minimize, but just setting everything negative! 
        if self.__objective_function_type   == 1:                       # minimize
            objective_function = sum(objective_function     )
        elif self.__objective_function_type == 2:                       # maximize (minimizing the negative)
            objective_function = sum(-1 * objective_function)
        elif self.__objective_function_type == 3:                       # min-max (shrink the single largest value as much as possible)
            objective_function = max(objective_function     )
        elif self.__objective_function_type == 4:                       # max-min (grow the smallest value as much as possible; minimize the negative of the smallest)  
            objective_function = -1 * min(objective_function)                               

        # add the objective function to the optimization 
        if self.__objective_function_type == 0:
            optimization.objective = 0
        else: 
            optimization.objective = objective_function
            
        # solver silencing 
        if self.__debug:
            # just some nice formatting for the solver output 
            print("\n")
        else:
            # silence the solver output to clean up the display 
            solvers.options['show_progress'] = False
        
        # optimize the system in a try-catch for cleanliness
        try:
           optimization.solve() 
           # After solving, check if solution exists
           if opt_food_grams.value is None:
                if self.__debug:
                    print("Optimization failed: no feasible solution found.")
                    return False
        except Exception as e: 
            print("\nERROR: Optimizer complained! \"" + str(e) +"\"")
            return False
                
        # adjust all the food totals
        # TODO check state of optimization, since failed optimization DOESN'T always throw an error 
        for ingredient, new_amount in zip(self.__opti_ingredients_dict.values(), opt_food_grams.value):
            ingredient.set_grams(new_amount)

        # we did i!
        return True

    # pretty print method! overrides normal print behavior!   
    # lists all the ingredients and their amounts, as well as the major
    # overall details of the meal (total fat, ratio, ingredient volume, etc.)
    def __repr__(self):
        return_string           = ""
        fat_gram_total          = 0.0
        protein_gram_total      = 0.0
        carbs_gram_total        = 0.0
        calorie_total           = 0.0
        volume_total            = 0.0

        format_spaces           = 0
        for ingredient in self.__opti_ingredients_dict.values():
            if format_spaces < len( str( ingredient.get_name() ) ):
                format_spaces = len( str( ingredient.get_name() ) )
        
        return_string += ("\nMeal:\n\t" + str(self.__name))
        return_string += ("\n\n\t\tIngredients:\n")

        for ingredient in self.__opti_ingredients_dict.values():
            return_string += ( "\n\t\t\t" + str(ingredient.get_name())                      + 
                               (format_spaces - len(str(ingredient.get_name()))) * " "      +
                               " : " + 
                               str(round(ingredient.get_grams(), self.__rounding_digits))   + 
                               "g\n" 
                             )
            fat_gram_total      += ingredient.get_food_type().get_fat_gram_ratio()      * ingredient.get_grams()
            protein_gram_total  += ingredient.get_food_type().get_protein_gram_ratio()  * ingredient.get_grams()
            carbs_gram_total    += ingredient.get_food_type().get_carbs_gram_ratio()    * ingredient.get_grams()
            calorie_total       += ingredient.get_food_type().get_cal_gram_ratio()      * ingredient.get_grams()
            volume_total        += ingredient.get_food_type().get_ml_gram_ratio()       * ingredient.get_grams()
            
        
        # print out the fat content details 
        return_string += ("\n\n\t\tCurrent meal fat content              :\t"       + 
                          str(round(fat_gram_total, self.__rounding_digits))        + 
                          "g"
                         )    
                         
        # print out the protein content details 
        return_string += ("\n\n\t\tCurrent meal protein content          :\t"       + 
                          str(round(protein_gram_total, self.__rounding_digits))    + 
                          "g"
                         )    
           
        # print out the carbs content details   
        return_string += ("\n\n\t\tCurrent meal carbs content            :\t"       + 
                          str(round(carbs_gram_total, self.__rounding_digits))      + 
                          "g"
                         )

        # print out the calorie details 
        return_string += ("\n\n\t\tCurrent meal calorie content          :\t"       + 
                          str(round(calorie_total, self.__rounding_digits))         + 
                          "cal"
                         )  

        # print out the volume details 
        return_string += ("\n\n\t\tCurrent meal volume                   :\t"       + 
                          str(round(volume_total, self.__rounding_digits))          + 
                          "ml"
                         )  

        # print out the ratio details
        if math.isclose(protein_gram_total + fat_gram_total, 0.0):
            return_string += ("\n\n\t\tCurrent meal macronutrient ratio      :\tN/A")
        else:
            return_string += ("\n\n\t\tCurrent meal macronutrient ratio      :\t"      + 
                              str(round(fat_gram_total/(protein_gram_total + carbs_gram_total), self.__rounding_digits))
                             )    

        return return_string
        

    def get_totals(self):
        """Return a dict of totals from the last optimization."""
        fat_total = sum(
            ing.get_food_type().get_fat_gram_ratio() * ing.get_grams()
            for ing in self.__opti_ingredients_dict.values()
        )
        protein_total = sum(
            ing.get_food_type().get_protein_gram_ratio() * ing.get_grams()
            for ing in self.__opti_ingredients_dict.values()
        )
        carbs_total = sum(
            ing.get_food_type().get_carbs_gram_ratio() * ing.get_grams()
            for ing in self.__opti_ingredients_dict.values()
        )
        cal_total = sum(
            ing.get_food_type().get_cal_gram_ratio() * ing.get_grams()
            for ing in self.__opti_ingredients_dict.values()
        )
        return {
            "fat": round(fat_total, self.__rounding_digits),
            "protein": round(protein_total, self.__rounding_digits),
            "carbs": round(carbs_total, self.__rounding_digits),
            "calories": round(cal_total, self.__rounding_digits),
        }


