import json

INPUT_FILE = "report_data.json"
OUTPUT_FILE = "articles_clean.json"

with open(INPUT_FILE, encoding="utf-16") as f:
    raw = json.load(f)

rows = raw["factMap"]["T!T"]["rows"]

articles = []
for row in rows:
    cells = row["dataCells"]
    articles.append(
        {
            "language": cells[0]["label"],
            "published_date": cells[1]["value"],
            "published_date_label": cells[1]["label"],
            "published_by": cells[2]["label"],
            "product": cells[3]["label"],
            "article_number": cells[4]["label"],
            "title": cells[5]["label"],
            "last_modified_by": cells[6]["label"],
            "publish_status": cells[7]["label"],
        }
    )

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(articles, f, indent=2, ensure_ascii=False)

print(f"Parsed {len(articles)} articles -> {OUTPUT_FILE}")

products = {}
languages = {}
for a in articles:
    products[a["product"]] = products.get(a["product"], 0) + 1
    languages[a["language"]] = languages.get(a["language"], 0) + 1

print("\nArticles by product:")
for product, count in sorted(products.items(), key=lambda x: -x[1]):
    print(f"  {count:>4}  {product}")

print("\nArticles by language:")
for lang, count in sorted(languages.items(), key=lambda x: -x[1]):
    print(f"  {count:>4}  {lang}")
