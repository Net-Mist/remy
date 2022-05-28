import argparse
import re
import time
from pathlib import Path

from selenium import webdriver

RECIPE_CATEGORIES = {1: "entrées", 2: "plats", 3: "desserts"}

CHROME_OPTIONS = ("--no-sandbox", "--headless", "--hide-scrollbars", "--disable-extensions", "--disable-infobars")

GET_INGREDIENT_LIST_JS = """
var xpath = "//div[text()='Ingrédients']";
var e = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
var ingList = e.parentElement.parentElement.parentElement.children[2].children[0].children[0].children[0].children[1]
return Array.from(ingList.children).map(c => c.innerText)
"""

GET_STEP_LIST_JS = """
var xpath = "//h3[text()='Étape 1']";
var e = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
var stepList = e.parentElement.parentElement.parentElement
return Array.from(stepList.children).map(c => c.innerText)
"""


SPLIT_WORDS = [" de ", " d'"]

UNSPLITABLE_WORDS = ["huile d'olive", "herbes de provence"]

UNITS = [
    "g",
    "cl",
]


def process_marmiton(url: str) -> tuple[list[str], list[str]]:
    options = webdriver.ChromeOptions()
    for option in CHROME_OPTIONS:
        options.add_argument(option)
    driver = webdriver.Chrome(executable_path="chromedriver", chrome_options=options)
    driver.get(url)
    time.sleep(10)
    ingredients = driver.execute_script(GET_INGREDIENT_LIST_JS)
    steps = driver.execute_script(GET_STEP_LIST_JS)
    ingredients = [re.sub(r"\xa0|\n", r" ", ingredient) for ingredient in ingredients]
    steps = [re.sub(r"ÉTAPE \d+\n*", r"", step) for step in steps]
    return ingredients, steps


def process_ingredients(ingredients: list[str]) -> dict[str, str]:
    """take a list of ingredient, human formatted, and transform them to cooklang format

    Returns:
        a dict with keys the name of the ingredient and value the cooklang definition
    """
    out = {}
    for ingredient in ingredients:
        # first clean the string
        ingredient = ingredient.removeprefix("* ").strip().lower()
        # sometime we got empty string. In this case do nothing
        if not ingredient:
            continue
        # if the ingredient is a single word, then this is its cooklang def
        if " " not in ingredient:
            out[ingredient] = ingredient
            continue
        # if the first word start an number, then this is the quantity
        ingredient_split = ingredient.split(" ")
        if m := re.match(r"\d+", ingredient_split[0]):
            # if the first word is the concat of a number and a word, then this word is the unit
            if m.end() != len(ingredient_split[0]):
                quantity_unit = f"{{{ingredient_split[0][:m.end()]}%{ingredient_split[0][m.end():]}}}"
                ingredient_name = " ".join(ingredient_split[1:])
            # if the second word is an unit, then we got to cooklang def
            elif ingredient_split[1] in UNITS:
                quantity_unit = f"{{{ingredient_split[0]}%{ingredient_split[1]}}}"
                ingredient_name = " ".join(ingredient_split[2:])
            else:
                quantity_unit = f"{{{ingredient_split[0]}}}"
                ingredient_name = " ".join(ingredient_split[1:])
            # now check if ingredient name starts by "de" or d'...
            # check if third word is "de" or "d'..."
            ingredient_name = ingredient_name.removeprefix("de ")
            ingredient_name = ingredient_name.removeprefix("d'")
            out[ingredient_name] = f"@{ingredient_name}{quantity_unit}"
            continue

        # if the ingredient contains unsplitable words, then this words are the ingredient name
        valid_unsplitable_word = [
            unsplitable_word for unsplitable_word in UNSPLITABLE_WORDS if unsplitable_word in ingredient
        ]
        if valid_unsplitable_word:
            unsplitable_word = valid_unsplitable_word[0]
            ingredient_name = unsplitable_word
            ingredient_quantity_and_units = " ".join(ingredient.split(unsplitable_word)).strip()
            out[ingredient_name] = f"@{ingredient_name}{{{ingredient_quantity_and_units}}}"
            continue

        # If the ingredient contains a split word, then text before are quantity and units, and
        # text after is ingredient name
        valid_split_word = [split_word for split_word in SPLIT_WORDS if split_word in ingredient]
        if valid_split_word:
            split_word = valid_split_word[0]
            splitted_ingredient = ingredient.split(split_word)
            ingredient_quantity_and_units = splitted_ingredient[0]
            ingredient_name = split_word.join(splitted_ingredient[1:])
            out[ingredient_name] = f"@{ingredient_name}{{{ingredient_quantity_and_units}}}"
            continue
        out[ingredient] = f"@{ingredient}"
    return out


def process_steps(steps: list[str], ingredient_mapping: dict) -> str:
    processed_ingredients = []
    add_to_file = "\n"
    for step in steps:
        step = step.strip().removeprefix("* ").strip()
        if not step:
            continue
        for ingredient in ingredient_mapping.keys():
            if ingredient in step and ingredient not in processed_ingredients:
                step = step.replace(ingredient, ingredient_mapping[ingredient])
                processed_ingredients.append(ingredient)

        add_to_file += step + "\n"

    add_to_file += "\n".join(v for k, v in ingredient_mapping.items() if k not in processed_ingredients)
    return add_to_file


def main() -> None:
    parser = argparse.ArgumentParser("create a new recipe")
    parser.add_argument("--name", type=str, help="name of the recipe")
    parser.add_argument("--kind", type=int, help="1: entrées, 2: plats, 3: desserts", required=True)
    parser.add_argument("--source", type=str, help="source of the recipe (website, book...)")
    parser.add_argument("--time", type=str, help="estimated time to prepare the meal")
    args = parser.parse_args()

    metadata = {"title": args.name, "time": args.time, "servings": 6, "source": args.source}

    for k, v in metadata.items():
        if v is None:
            metadata[k] = input(f"Please provide a value for {k}\n> ")

    recipes_path = Path(__file__).parent / "recipes"
    cooklang_file_path = recipes_path / RECIPE_CATEGORIES[args.kind] / (metadata["title"].replace(" ", "_") + ".cook")

    with cooklang_file_path.open("w") as f:
        for k, v in metadata.items():
            f.write(f">> {k}: {v}\n")

    if metadata["source"].startswith("https://www.marmiton.org/"):
        ingredients, steps = process_marmiton(metadata["source"])
        map_ingredient_to_cooklang = process_ingredients(ingredients)
        add_to_file = process_steps(steps, map_ingredient_to_cooklang)
        with cooklang_file_path.open("a") as f:
            f.write(add_to_file)


if __name__ == "__main__":
    main()
