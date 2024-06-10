from app import app
from flask import render_template, request, redirect, url_for, send_file
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import requests
from app import utils
import os
import json
import io

@app.route('/')
@app.route('/index')
def index():
    return render_template("base.html.jinja")

@app.route('/extract', methods=['POST','GET'])
def extract():
    if request.method=='POST':
        product_id = request.form.get('product_id')
        url = f"https://www.ceneo.pl/{product_id}"
        response = requests.get(url)
        if response.status_code == requests.codes['ok']:
            page_dom = BeautifulSoup(response.text, "html.parser")
            opinions_count = utils.extract(page_dom, "a.product-review__link > span")
            if opinions_count:
                product_name = utils.extract(page_dom, "h1")
                url = f"https://www.ceneo.pl/{product_id}/opinie-1"
                all_opinions = []
                while(url):
                    response = requests.get(url)
                    page_dom = BeautifulSoup(response.text, "html.parser")
                    opinions = page_dom.select("div.js_product-review")
                    for opinion in opinions:
                        single_opinion = {
                            key: utils.extract(opinion, *value)
                                for key, value in utils.selectors.items()
                        }
                        all_opinions.append(single_opinion)
                    try:
                        url = "https://www.ceneo.pl"+utils.extract(page_dom, "a.pagination__next")["href"].strip()
                    except TypeError:
                        url = None
                    if not os.path.exists("app/data/stats"):
                        os.mkdir("app/data/stats")    
                    if not os.path.exists("app/data"):
                        os.mkdir("app/data")
                    if not os.path.exists("app/data/opinions"):
                        os.makedirs("app/data/opinions")
                    opinions = pd.DataFrame.from_dict(all_opinions)
                    opinions_rating = opinions.rating.apply(lambda r: r.split("/")[0].replace(",",".")).astype(float)
                    opinions.recommendation = opinions.recommendation.apply(lambda r : "Brak rekomendacji" if r is None else r)
                    stats = {
                        "product_id" : product_id,
                        "opinions_count" : opinions.shape[0],
                        "pros_count" : int(opinions.pros.apply(lambda p: 1 if p else 0).sum()),
                        "cons_count" : int(opinions.cons.apply(lambda c: 1 if c else 0).sum()),
                        "average_rating" : opinions_rating.mean(),
                        "rating_distribution" : opinions_rating.value_counts().reindex(np.arange(0,5.5,0.5), fill_value=0).to_dict(),
                        "recommendations_distribution" : opinions.recommendation.value_counts().reindex(["Polecam", "Nie polecam", "Brak rekomendacji"]).to_dict(),
                        "produt_name" : product_name


                    }
                    with open(f"app/data/stats/{product_id}.json", "w", encoding="UTF-8") as jf:
                        json.dump(stats, jf, indent=4, ensure_ascii=False)
                return redirect(url_for('product', product_id=product_id))
            return render_template("extract.html.jinja", error="Dla produktu o podanym id nie ma żadnych opinii")
        return render_template("extract.html.jinja", error="Produkt o podanym id nie istnieje") 
    return render_template("extract.html.jinja")


@app.route('/author')
def author():
    return render_template("author.html.jinja")

@app.route('/products')
def products():
    products_list = [filename.split(".")[0] for filename in os.listdir("app/data/stats")]
    products = []
    for product_id in products_list:
        
        with open(f"app/data/stats/{product_id}.json", "r", encoding="UTF-8") as jf:
            stats = json.load(jf)
            products.append(stats)
    return render_template("products.html.jinja", products = products, product_id = product_id,)

@app.route('/product/<product_id>')
def product(product_id):
     product_file_path = os.path.join('app/products', f'{product_id}.json')
     product_data = None
     try:
        with open(product_file_path, 'r', encoding='utf-8') as file:
            product_data = json.load(file)
     except FileNotFoundError:
        f"Product with ID {product_id} not found"
     except json.JSONDecodeError:
        f"Error decoding JSON for product with ID {product_id}"
     if product_data is None:
        f"Unexpected error for product with ID {product_id}"
     return render_template("product.html.jinja", product=product_data,product_id=product_id)





@app.route('/product/download_json/<product_id>')
def download_json(product_id):
    return send_file(f"app/data/opinions/{product_id}.json", "text/json", as_attachment=True)



@app.route('/product/download_csv/<product_id>')
def download_csv(product_id):
    opinions = pd.read_json(f"app/data/opinions/{product_id}.json")
    buffer = io.BytesIO(opinions.to_csv(sep=";", decimal=",", index=False).encode())
    opinions.to_csv()
    return send_file(buffer, "text/csv", as_attachment=True, download_name=f"{product_id}.csv")
    
@app.route('/product/download_xlsx/<product_id>')
def download_xlsx(product_id):
    pass

