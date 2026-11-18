from typing import List, Dict, Any

# Curated catalog of balanced recipes
# Each ingredient amount is specified PER 1 ADULT PERSON for scaling
RECIPE_CATALOG: List[Dict[str, Any]] = [
    # --- ЗАВТРАКИ ---
    {
        "id": "brk_1",
        "name": "Овсяная каша с ягодами и медом",
        "meal_type": "breakfast",
        "meal_name_ru": "Завтрак",
        "description": "Сытная овсянка долгой варки на молоке со свежими ягодами и натуральным медом.",
        "cooking_time_min": 15,
        "calories": 360,
        "proteins": 12.0,
        "fats": 7.0,
        "carbs": 62.0,
        "tags": ["овсянка", "ягоды", "вегетарианское", "каша"],
        "allergen_tags": ["глютен", "лактоза"],
        "ingredients": [
            {"name": "Овсяные хлопья", "amount": 60, "unit": "г", "category": "бакалея"},
            {"name": "Молоко 3.2%", "amount": 180, "unit": "мл", "category": "молочные"},
            {"name": "Ягоды свежемороженые", "amount": 50, "unit": "г", "category": "заморозка"},
            {"name": "Мед натуральный", "amount": 15, "unit": "г", "category": "бакалея"},
            {"name": "Сливочное масло", "amount": 10, "unit": "г", "category": "молочные"}
        ]
    },
    {
        "id": "brk_2",
        "name": "Пышный омлет с томатами и сыром",
        "meal_type": "breakfast",
        "meal_name_ru": "Завтрак",
        "description": "Классический французский омлет с сочными томатами, сыром сулугуни и свежей зеленью.",
        "cooking_time_min": 12,
        "calories": 390,
        "proteins": 24.0,
        "fats": 28.0,
        "carbs": 6.0,
        "tags": ["яйца", "сыр", "высокобелковое", "без_глютена"],
        "allergen_tags": ["яйца", "лактоза"],
        "ingredients": [
            {"name": "Яйца куриные С0", "amount": 3, "unit": "шт", "category": "яйца"},
            {"name": "Молоко 3.2%", "amount": 50, "unit": "мл", "category": "молочные"},
            {"name": "Сыр полутвердый", "amount": 40, "unit": "г", "category": "сыры"},
            {"name": "Томаты свежие", "amount": 80, "unit": "г", "category": "овощи"},
            {"name": "Масло растительное", "amount": 10, "unit": "мл", "category": "бакалея"}
        ]
    },
    {
        "id": "brk_3",
        "name": "Нежные творожные сырники со сметаной",
        "meal_type": "breakfast",
        "meal_name_ru": "Завтрак",
        "description": "Воздушные румяные сырники из 9% творога с золотистой корочкой.",
        "cooking_time_min": 20,
        "calories": 420,
        "proteins": 28.0,
        "fats": 16.0,
        "carbs": 38.0,
        "tags": ["творог", "высокобелковое", "сырники"],
        "allergen_tags": ["лактоза", "яйца", "глютен"],
        "ingredients": [
            {"name": "Творог 9%", "amount": 180, "unit": "г", "category": "молочные"},
            {"name": "Яйца куриные С0", "amount": 1, "unit": "шт", "category": "яйца"},
            {"name": "Мука пшеничная", "amount": 30, "unit": "г", "category": "бакалея"},
            {"name": "Сахар", "amount": 15, "unit": "г", "category": "бакалея"},
            {"name": "Сметана 15%", "amount": 40, "unit": "г", "category": "молочные"}
        ]
    },
    {
        "id": "brk_4",
        "name": "Тост с авокадо, яйцом пашот и творожным сыром",
        "meal_type": "breakfast",
        "meal_name_ru": "Завтрак",
        "description": "Хрустящий цельнозерновой хлеб со спелым авокадо, нежным творожным сыром и яйцом пашот.",
        "cooking_time_min": 15,
        "calories": 410,
        "proteins": 18.0,
        "fats": 26.0,
        "carbs": 26.0,
        "tags": ["авокадо", "яйца", "полезные_жиры", "тосты"],
        "allergen_tags": ["глютен", "яйца", "лактоза"],
        "ingredients": [
            {"name": "Хлеб цельнозерновой", "amount": 60, "unit": "г", "category": "хлеб"},
            {"name": "Авокадо", "amount": 70, "unit": "г", "category": "овощи"},
            {"name": "Яйца куриные С0", "amount": 2, "unit": "шт", "category": "яйца"},
            {"name": "Творожный сыр", "amount": 30, "unit": "г", "category": "сыры"}
        ]
    },
    {
        "id": "brk_5",
        "name": "Шакшука с болгарским перцем и томатами",
        "meal_type": "breakfast",
        "meal_name_ru": "Завтрак",
        "description": "Яркая пряная восточная яичница в густом соусе из спелых помидоров, перца и трав.",
        "cooking_time_min": 20,
        "calories": 350,
        "proteins": 19.0,
        "fats": 21.0,
        "carbs": 18.0,
        "tags": ["яйца", "овощи", "без_глютена", "без_лактозы"],
        "allergen_tags": ["яйца"],
        "ingredients": [
            {"name": "Яйца куриные С0", "amount": 2, "unit": "шт", "category": "яйца"},
            {"name": "Томаты свежие", "amount": 120, "unit": "г", "category": "овощи"},
            {"name": "Перец болгарский", "amount": 70, "unit": "г", "category": "овощи"},
            {"name": "Лук репчатый", "amount": 30, "unit": "г", "category": "овощи"},
            {"name": "Чеснок", "amount": 5, "unit": "г", "category": "овощи"},
            {"name": "Масло растительное", "amount": 10, "unit": "мл", "category": "бакалея"}
        ]
    },
    {
        "id": "brk_6",
        "name": "Гречневая каша на молоке со сливочным маслом",
        "meal_type": "breakfast",
        "meal_name_ru": "Завтрак",
        "description": "Теплая рассыпчатая гречка, сваренная на фермерском молоке с кусочком сливочного масла.",
        "cooking_time_min": 20,
        "calories": 380,
        "proteins": 14.0,
        "fats": 12.0,
        "carbs": 55.0,
        "tags": ["гречка", "без_глютена", "каша"],
        "allergen_tags": ["лактоза"],
        "ingredients": [
            {"name": "Гречневая крупа", "amount": 70, "unit": "г", "category": "бакалея"},
            {"name": "Молоко 3.2%", "amount": 200, "unit": "мл", "category": "молочные"},
            {"name": "Сливочное масло", "amount": 15, "unit": "г", "category": "молочные"}
        ]
    },

    # --- ОБЕДЫ ---
    {
        "id": "lnc_1",
        "name": "Куриный суп с домашней лапшой и зеленью",
        "meal_type": "lunch",
        "meal_name_ru": "Обед",
        "description": "Прозрачный наваристый бульон из фермерской курочки с яичной лапшой и морковью.",
        "cooking_time_min": 35,
        "calories": 420,
        "proteins": 34.0,
        "fats": 12.0,
        "carbs": 44.0,
        "tags": ["курица", "суп", "птица", "комфортная_еда"],
        "allergen_tags": ["глютен", "яйца"],
        "ingredients": [
            {"name": "Куриное филе", "amount": 150, "unit": "г", "category": "мясо"},
            {"name": "Макаронные изделия (лапша)", "amount": 50, "unit": "г", "category": "бакалея"},
            {"name": "Картофель", "amount": 100, "unit": "г", "category": "овощи"},
            {"name": "Морковь", "amount": 40, "unit": "г", "category": "овощи"},
            {"name": "Лук репчатый", "amount": 30, "unit": "г", "category": "овощи"},
            {"name": "Зелень свежая", "amount": 15, "unit": "г", "category": "овощи"}
        ]
    },
    {
        "id": "lnc_2",
        "name": "Ароматный борщ с говядиной и сметаной",
        "meal_type": "lunch",
        "meal_name_ru": "Обед",
        "description": "Традиционный наваристый борщ со свеклой, сочной говядиной, капустой и ложкой сметаны.",
        "cooking_time_min": 50,
        "calories": 480,
        "proteins": 32.0,
        "fats": 20.0,
        "carbs": 42.0,
        "tags": ["говядина", "суп", "мясо", "без_глютена"],
        "allergen_tags": ["лактоза"],
        "ingredients": [
            {"name": "Говядина бескостная", "amount": 140, "unit": "г", "category": "мясо"},
            {"name": "Свекла", "amount": 80, "unit": "г", "category": "овощи"},
            {"name": "Капуста белокочанная", "amount": 90, "unit": "г", "category": "овощи"},
            {"name": "Картофель", "amount": 80, "unit": "г", "category": "овощи"},
            {"name": "Морковь", "amount": 40, "unit": "г", "category": "овощи"},
            {"name": "Томатная паста", "amount": 25, "unit": "г", "category": "бакалея"},
            {"name": "Сметана 15%", "amount": 30, "unit": "г", "category": "молочные"}
        ]
    },
    {
        "id": "lnc_3",
        "name": "Запеченная куриная грудка с рисом басмати и овощами",
        "meal_type": "lunch",
        "meal_name_ru": "Обед",
        "description": "Сочная запеченная в паприке куриная грудка с рассыпчатым рисом и свежими огурцами.",
        "cooking_time_min": 30,
        "calories": 520,
        "proteins": 45.0,
        "fats": 10.0,
        "carbs": 62.0,
        "tags": ["курица", "рис", "без_глютена", "без_лактозы", "высокобелковое"],
        "allergen_tags": [],
        "ingredients": [
            {"name": "Куриное филе", "amount": 180, "unit": "г", "category": "мясо"},
            {"name": "Рис длиннозерный", "amount": 75, "unit": "г", "category": "бакалея"},
            {"name": "Огурцы свежие", "amount": 90, "unit": "г", "category": "овощи"},
            {"name": "Масло растительное", "amount": 10, "unit": "мл", "category": "бакалея"}
        ]
    },
    {
        "id": "lnc_4",
        "name": "Бефстроганов из говядины с картофельным пюре",
        "meal_type": "lunch",
        "meal_name_ru": "Обед",
        "description": "Нежнейшие полоски говядины в бархатном сливочно-сметанном соусе с мягким пюре.",
        "cooking_time_min": 40,
        "calories": 550,
        "proteins": 38.0,
        "fats": 24.0,
        "carbs": 46.0,
        "tags": ["говядина", "картофель", "мясо"],
        "allergen_tags": ["лактоза"],
        "ingredients": [
            {"name": "Говядина бескостная", "amount": 160, "unit": "г", "category": "мясо"},
            {"name": "Картофель", "amount": 180, "unit": "г", "category": "овощи"},
            {"name": "Сметана 15%", "amount": 40, "unit": "г", "category": "молочные"},
            {"name": "Молоко 3.2%", "amount": 40, "unit": "мл", "category": "молочные"},
            {"name": "Сливочное масло", "amount": 15, "unit": "г", "category": "молочные"},
            {"name": "Лук репчатый", "amount": 30, "unit": "г", "category": "овощи"}
        ]
    },
    {
        "id": "lnc_5",
        "name": "Паста с лососем и сливочным соусом",
        "meal_type": "lunch",
        "meal_name_ru": "Обед",
        "description": "Итальянская паста аль-денте с кусочками свежего лосося, сливками и тертым сыром.",
        "cooking_time_min": 25,
        "calories": 580,
        "proteins": 36.0,
        "fats": 22.0,
        "carbs": 58.0,
        "tags": ["рыба", "лосось", "паста", "морепродукты"],
        "allergen_tags": ["глютен", "рыба", "лактоза"],
        "ingredients": [
            {"name": "Макаронные изделия (спагетти)", "amount": 80, "unit": "г", "category": "бакалея"},
            {"name": "Красная рыба (лосось/форель)", "amount": 140, "unit": "г", "category": "рыба"},
            {"name": "Сливки 20%", "amount": 70, "unit": "мл", "category": "молочные"},
            {"name": "Сыр полутвердый", "amount": 25, "unit": "г", "category": "сыры"}
        ]
    },
    {
        "id": "lnc_6",
        "name": "Индейка запеченная с гречкой и грибами",
        "meal_type": "lunch",
        "meal_name_ru": "Обед",
        "description": "Сочное филе индейки с рассыпчатой гречкой и шампиньонами.",
        "cooking_time_min": 35,
        "calories": 490,
        "proteins": 42.0,
        "fats": 14.0,
        "carbs": 50.0,
        "tags": ["индейка", "гречка", "грибы", "птица", "без_глютена"],
        "allergen_tags": [],
        "ingredients": [
            {"name": "Филе индейки", "amount": 160, "unit": "г", "category": "мясо"},
            {"name": "Гречневая крупа", "amount": 70, "unit": "г", "category": "бакалея"},
            {"name": "Шампиньоны свежие", "amount": 70, "unit": "г", "category": "грибы"},
            {"name": "Лук репчатый", "amount": 30, "unit": "г", "category": "овощи"},
            {"name": "Масло растительное", "amount": 10, "unit": "мл", "category": "бакалея"}
        ]
    },

    # --- УЖИНЫ ---
    {
        "id": "dnr_1",
        "name": "Филе белой рыбы на пару с картофелем и укропом",
        "meal_type": "dinner",
        "meal_name_ru": "Ужин",
        "description": "Легкий диетический ужин: филе трески или минтая с отварным молодым картофелем и зеленью.",
        "cooking_time_min": 25,
        "calories": 390,
        "proteins": 36.0,
        "fats": 8.0,
        "carbs": 42.0,
        "tags": ["рыба", "легкий_ужин", "без_глютена", "без_лактозы"],
        "allergen_tags": ["рыба"],
        "ingredients": [
            {"name": "Филе белой рыбы (минтай/треска)", "amount": 180, "unit": "г", "category": "рыба"},
            {"name": "Картофель", "amount": 150, "unit": "г", "category": "овощи"},
            {"name": "Масло сливочное", "amount": 10, "unit": "г", "category": "молочные"},
            {"name": "Зелень свежая", "amount": 15, "unit": "г", "category": "овощи"}
        ]
    },
    {
        "id": "dnr_2",
        "name": "Куриные котлеты с тушеными кабачками",
        "meal_type": "dinner",
        "meal_name_ru": "Ужин",
        "description": "Нежные рубленые куриные котлетки с тающими во рту тушеными кабачками и чесночком.",
        "cooking_time_min": 30,
        "calories": 430,
        "proteins": 40.0,
        "fats": 16.0,
        "carbs": 24.0,
        "tags": ["курица", "кабачки", "низкоуглеводное"],
        "allergen_tags": ["яйца"],
        "ingredients": [
            {"name": "Куриное филе", "amount": 170, "unit": "г", "category": "мясо"},
            {"name": "Кабачки свежие", "amount": 180, "unit": "г", "category": "овощи"},
            {"name": "Яйца куриные С0", "amount": 1, "unit": "шт", "category": "яйца"},
            {"name": "Масло растительное", "amount": 10, "unit": "мл", "category": "бакалея"}
        ]
    },
    {
        "id": "dnr_3",
        "name": "Стейк из лосося с овощами на гриле",
        "meal_type": "dinner",
        "meal_name_ru": "Ужин",
        "description": "Сочный запеченный лосось с лимоном, сладким болгарским перцем и цукини.",
        "cooking_time_min": 25,
        "calories": 460,
        "proteins": 38.0,
        "fats": 24.0,
        "carbs": 16.0,
        "tags": ["рыба", "лосось", "полезные_жиры", "без_глютена", "без_лактозы"],
        "allergen_tags": ["рыба"],
        "ingredients": [
            {"name": "Красная рыба (лосось/форель)", "amount": 160, "unit": "г", "category": "рыба"},
            {"name": "Перец болгарский", "amount": 80, "unit": "г", "category": "овощи"},
            {"name": "Томаты свежие", "amount": 80, "unit": "г", "category": "овощи"},
            {"name": "Масло растительное", "amount": 10, "unit": "мл", "category": "бакалея"}
        ]
    },
    {
        "id": "dnr_4",
        "name": "Греческий салат с куриным филе на гриле",
        "meal_type": "dinner",
        "meal_name_ru": "Ужин",
        "description": "Средиземноморский свежий салат с хрустящими огурцами, томатами, сыром фета и куриной грудкой.",
        "cooking_time_min": 20,
        "calories": 420,
        "proteins": 36.0,
        "fats": 22.0,
        "carbs": 14.0,
        "tags": ["курица", "салат", "сыр", "без_глютена"],
        "allergen_tags": ["лактоза"],
        "ingredients": [
            {"name": "Куриное филе", "amount": 150, "unit": "г", "category": "мясо"},
            {"name": "Сыр Фета/Брынза", "amount": 50, "unit": "г", "category": "сыры"},
            {"name": "Огурцы свежие", "amount": 80, "unit": "г", "category": "овощи"},
            {"name": "Томаты свежие", "amount": 80, "unit": "г", "category": "овощи"},
            {"name": "Масло растительное", "amount": 15, "unit": "мл", "category": "бакалея"}
        ]
    },
    {
        "id": "dnr_5",
        "name": "Нежные тефтели из индейки в томатном соусе с рисом",
        "meal_type": "dinner",
        "meal_name_ru": "Ужин",
        "description": "Ароматные тефтели из филе индейки в густом натуральном соусе из протертых томатов с рисом.",
        "cooking_time_min": 35,
        "calories": 470,
        "proteins": 35.0,
        "fats": 14.0,
        "carbs": 52.0,
        "tags": ["индейка", "рис", "без_глютена", "без_лактозы"],
        "allergen_tags": ["яйца"],
        "ingredients": [
            {"name": "Филе индейки", "amount": 150, "unit": "г", "category": "мясо"},
            {"name": "Рис длиннозерный", "amount": 60, "unit": "г", "category": "бакалея"},
            {"name": "Томатная паста", "amount": 30, "unit": "г", "category": "бакалея"},
            {"name": "Лук репчатый", "amount": 30, "unit": "г", "category": "овощи"},
            {"name": "Яйца куриные С0", "amount": 1, "unit": "шт", "category": "яйца"}
        ]
    },
    {
        "id": "dnr_6",
        "name": "Теплый вок с говядиной и хрустящими овощами",
        "meal_type": "dinner",
        "meal_name_ru": "Ужин",
        "description": "Тонкие полоски говядины, быстро обжаренные с болгарским перцем, морковью и кунжутом.",
        "cooking_time_min": 25,
        "calories": 440,
        "proteins": 35.0,
        "fats": 18.0,
        "carbs": 28.0,
        "tags": ["говядина", "вок", "без_лактозы", "овощи"],
        "allergen_tags": ["соя"],
        "ingredients": [
            {"name": "Говядина бескостная", "amount": 150, "unit": "г", "category": "мясо"},
            {"name": "Перец болгарский", "amount": 70, "unit": "г", "category": "овощи"},
            {"name": "Морковь", "amount": 50, "unit": "г", "category": "овощи"},
            {"name": "Масло растительное", "amount": 15, "unit": "мл", "category": "бакалея"}
        ]
    }
]

# Baseline prices in Pyaterochka, Magnit, and Lenta per retail unit
# Used for calculation and seeded into the DB
BASELINE_STORE_PRICES: List[Dict[str, Any]] = [
    {"name": "Куриное филе", "category": "мясо", "unit": "кг", "pyaterochka": 389.0, "magnit": 379.0, "lenta": 399.0},
    {"name": "Говядина бескостная", "category": "мясо", "unit": "кг", "pyaterochka": 699.0, "magnit": 720.0, "lenta": 680.0},
    {"name": "Филе индейки", "category": "мясо", "unit": "кг", "pyaterochka": 490.0, "magnit": 475.0, "lenta": 485.0},
    {"name": "Красная рыба (лосось/форель)", "category": "рыба", "unit": "кг", "pyaterochka": 1390.0, "magnit": 1420.0, "lenta": 1290.0},
    {"name": "Филе белой рыбы (минтай/треска)", "category": "рыба", "unit": "кг", "pyaterochka": 340.0, "magnit": 329.0, "lenta": 355.0},
    {"name": "Яйца куриные С0", "category": "яйца", "unit": "дес", "pyaterochka": 119.0, "magnit": 114.0, "lenta": 124.0},
    {"name": "Молоко 3.2%", "category": "молочные", "unit": "л", "pyaterochka": 85.0, "magnit": 79.0, "lenta": 84.0},
    {"name": "Творог 9%", "category": "молочные", "unit": "кг", "pyaterochka": 410.0, "magnit": 395.0, "lenta": 420.0},
    {"name": "Сметана 15%", "category": "молочные", "unit": "кг", "pyaterochka": 260.0, "magnit": 250.0, "lenta": 275.0},
    {"name": "Сливочное масло", "category": "молочные", "unit": "кг", "pyaterochka": 980.0, "magnit": 950.0, "lenta": 990.0},
    {"name": "Сливки 20%", "category": "молочные", "unit": "л", "pyaterochka": 340.0, "magnit": 330.0, "lenta": 360.0},
    {"name": "Сыр полутвердый", "category": "сыры", "unit": "кг", "pyaterochka": 790.0, "magnit": 760.0, "lenta": 810.0},
    {"name": "Творожный сыр", "category": "сыры", "unit": "кг", "pyaterochka": 690.0, "magnit": 710.0, "lenta": 680.0},
    {"name": "Сыр Фета/Брынза", "category": "сыры", "unit": "кг", "pyaterochka": 650.0, "magnit": 630.0, "lenta": 640.0},
    {"name": "Рис длиннозерный", "category": "бакалея", "unit": "кг", "pyaterochka": 125.0, "magnit": 119.0, "lenta": 129.0},
    {"name": "Гречневая крупа", "category": "бакалея", "unit": "кг", "pyaterochka": 89.0, "magnit": 82.0, "lenta": 85.0},
    {"name": "Овсяные хлопья", "category": "бакалея", "unit": "кг", "pyaterochka": 95.0, "magnit": 89.0, "lenta": 99.0},
    {"name": "Макаронные изделия (спагетти)", "category": "бакалея", "unit": "кг", "pyaterochka": 110.0, "magnit": 105.0, "lenta": 115.0},
    {"name": "Макаронные изделия (лапша)", "category": "бакалея", "unit": "кг", "pyaterochka": 115.0, "magnit": 108.0, "lenta": 120.0},
    {"name": "Мука пшеничная", "category": "бакалея", "unit": "кг", "pyaterochka": 65.0, "magnit": 59.0, "lenta": 62.0},
    {"name": "Сахар", "category": "бакалея", "unit": "кг", "pyaterochka": 68.0, "magnit": 66.0, "lenta": 69.0},
    {"name": "Масло растительное", "category": "бакалея", "unit": "л", "pyaterochka": 129.0, "magnit": 124.0, "lenta": 132.0},
    {"name": "Томатная паста", "category": "бакалея", "unit": "кг", "pyaterochka": 290.0, "magnit": 280.0, "lenta": 310.0},
    {"name": "Мед натуральный", "category": "бакалея", "unit": "кг", "pyaterochka": 550.0, "magnit": 520.0, "lenta": 540.0},
    {"name": "Картофель", "category": "овощи", "unit": "кг", "pyaterochka": 38.0, "magnit": 36.0, "lenta": 42.0},
    {"name": "Морковь", "category": "овощи", "unit": "кг", "pyaterochka": 42.0, "magnit": 39.0, "lenta": 45.0},
    {"name": "Лук репчатый", "category": "овощи", "unit": "кг", "pyaterochka": 35.0, "magnit": 32.0, "lenta": 37.0},
    {"name": "Свекла", "category": "овощи", "unit": "кг", "pyaterochka": 39.0, "magnit": 37.0, "lenta": 42.0},
    {"name": "Капуста белокочанная", "category": "овощи", "unit": "кг", "pyaterochka": 34.0, "magnit": 31.0, "lenta": 36.0},
    {"name": "Томаты свежие", "category": "овощи", "unit": "кг", "pyaterochka": 220.0, "magnit": 210.0, "lenta": 235.0},
    {"name": "Огурцы свежие", "category": "овощи", "unit": "кг", "pyaterochka": 180.0, "magnit": 175.0, "lenta": 195.0},
    {"name": "Перец болгарский", "category": "овощи", "unit": "кг", "pyaterochka": 280.0, "magnit": 269.0, "lenta": 299.0},
    {"name": "Кабачки свежие", "category": "овощи", "unit": "кг", "pyaterochka": 140.0, "magnit": 135.0, "lenta": 150.0},
    {"name": "Авокадо", "category": "овощи", "unit": "кг", "pyaterochka": 590.0, "magnit": 560.0, "lenta": 580.0},
    {"name": "Чеснок", "category": "овощи", "unit": "кг", "pyaterochka": 310.0, "magnit": 290.0, "lenta": 330.0},
    {"name": "Зелень свежая", "category": "овощи", "unit": "кг", "pyaterochka": 450.0, "magnit": 430.0, "lenta": 470.0},
    {"name": "Шампиньоны свежие", "category": "грибы", "unit": "кг", "pyaterochka": 320.0, "magnit": 310.0, "lenta": 335.0},
    {"name": "Ягоды свежемороженые", "category": "заморозка", "unit": "кг", "pyaterochka": 420.0, "magnit": 399.0, "lenta": 410.0},
    {"name": "Хлеб цельнозерновой", "category": "хлеб", "unit": "шт", "pyaterochka": 58.0, "magnit": 54.0, "lenta": 62.0}
]
