from pathlib import Path
import argparse

RECIPE_CATEGORIES = {
    1: "entrées",
    2: "plats",
    3: "desserts"
}

def main():
    parser = argparse.ArgumentParser("create a new recipe")
    parser.add_argument("--name", type=str, help="name of the recipe")
    parser.add_argument("--kind", type=int , help="1: entrées, 2: plats, 3: desserts", required=True)
    parser.add_argument("--source", type=str , help="source of the recipe (website, book...)")
    parser.add_argument("--time", type=str, help="estimated time to prepare the meal")
    args = parser.parse_args()

    metadata = {
        "title": args.name,
        "time": args.time,
        "servings": 6,
        "source": args.source
    }

    for k, v in metadata.items():
        if v is None:
            metadata[k] = input(f"Please provide a value for {k}\n> ")

    recipes_path = Path(__file__).parent / "recipes"
    cooklang_file_path = recipes_path / RECIPE_CATEGORIES[args.kind] / (metadata["title"].replace(" ", "_") + ".cook")

    with cooklang_file_path.open("w") as f:
        for k, v in metadata.items():
            f.write(f">> {k}: {v}\n")


if __name__ == "__main__":
    main()