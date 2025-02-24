import os
import time
import re
from flask import Flask, jsonify, render_template, request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Ajusta caminho para a pasta 'templates' (sobe um nível)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app = Flask(__name__, template_folder=TEMPLATES_DIR)

# Dicionário com links diferentes para cada produto, incluindo o nome da loja
PRODUCT_LINKS = {
    "coca-cola": [
        {"store": "Pão de Açúcar", "url": "https://www.paodeacucar.com/produto/355907?storeId=461"},
        {"store": "Lojas Rede",       "url": "https://www.lojasrede.com.br/refrigerante-coca-cola-lata-310ml/p?idsku=798004&srsltid=AfmBOopsrxvPMQ3bemiK9ykI3owNZMmwSHoZM9h1ZuEFvqSCwi6_k1IDIhM"},
        {"store": "Atacadão",     "url": "https://www.atacadao.com.br/refrigerante-coca-cola-sleek-lata-com-310ml-55803-4100/p"},
        {"store": "Carrefour",    "url": "https://mercado.carrefour.com.br/cocacola-lata-310-ml-8666822/p"}
    ],
    "guarana": [
        {"store": "Pão de Açúcar", "url": "https://www.paodeacucar.com/produto/11428/refrigerante-guarana-diet-antarctica-garrafa-2l"},
        {"store": "Amazon",       "url": "https://www.amazon.com.br/Antarctica-Refrigerante-Guaraná-Pet/dp/B006DQOXTY/ref=sr_1_1?crid=1FZK4CU3AVSM1&dib=eyJ2IjoiMSJ9.AQp-CbRaLZTr-1d2kQfKAU02CzHBNJsSeE18nElfMReIiNzR6eBeANR-B2GIXgajl1aDCOp22-DfZTn3Ow7pwZAYoVRZ85PL167Cgjy1sHoWJd_f1H78b3ZMJRx4GL2IFByJP8sJ7fUIf74cPSf49TUCtrO2BWgqm6oaRc6TQSj8TLYPeblblK4vU-2SJBT_3sZ8lqCqadUvClpyy7QRW6oVduE_p6b6JYTAzSsWJk1l69feZPnDOofok1hePsml93G5Xam0V-eO1hSk9vVbHB_DknTFTnYeipaRiqYcs4O2oiNFwgaIYeGEbO1nLx-3rX5iYzHaB5Afn9o17ISqKb_TTB-ZCQZNyOktaLCPi1oGDmPuC1ywSxxB-As8JbxIXmqyDj0AYYI74lK4QRLODfr78GZNDRZmhwCh88DCZlB6nANm8Pe9jAYUrymXBLRK.YqteJN1zdI7-rJqfx8JpNsHEbhSrmS3DAx_-Yyo9rII&dib_tag=se&keywords=guarana+2l&qid=1740437107&sprefix=guarana+2%2Caps%2C264&sr=8-1"},
        {"store": "Atacadão",     "url": "https://www.atacadao.com.br/refrigerante-guarana-antarctica-19691-5482/p"},
        {"store": "Carrefour",    "url": "https://mercado.carrefour.com.br/refrigerante-guarana-antarctica-garrafa-2l-156396/p"}
    ],
    "pepsi": [
        {"store": "Pão de Açúcar", "url": "https://www.paodeacucar.com/produto/149709/refrigerante-pepsi-garrafa-2l"},
        {"store": "Amazon",       "url": "https://www.amazon.com.br/Refrigerante-Pepsi-Pet-2-Litros/dp/B07Y2F2D85/ref=sr_1_17?__mk_pt_BR=ÅMÅŽÕÑ&crid=3RHIXG73GWFKE&dib=eyJ2IjoiMSJ9.-yHfFHMJvFgrnEtOXeNKfeocAhKz2h7iR59UwtboB3RIMdcLynptCScNPc56unr2AxqY-CxwmfXqTARuomprP08VkBpShezZqEPkge9VDcK6ZSi9j2Drxp4WauooY8Nq49p0uBgT15w3mHif5L7vvlE-TlaVKGRj-mZOxPB5NTjryV8_BrL4RGD_CTAhN0loz3pfRFJJo5PZmx0W4qHLvSfhLpsx5znf9I9SBMStwW2C8SnaOWoCZf1pJ0GDPgRrEwGtXQddWIV2vDys8r1s5O5yqbEEZQDBkA9Fg5yjt5yfupYgHfeQNEsHpINOlBM-TEZCUhir2DCqLm2_IK5N7KBKmMCZVRrZqshVwvq6Wn6WCjOpCIXyyQPSN9Q5wJoTeDj1ufgJ-4VZGa2uXyzjd60l9pIb4Rj8VYuEh-Hynity841RwmGBTePSOajrCCum.ECCPZujrrY9k-40awc0AfnlcYw_ifF1x83VHOGMMyZE&dib_tag=se&keywords=pepsi&qid=1740436968&sprefix=pepsi%2Caps%2C199&sr=8-17"},
        {"store": "Atacadão",     "url": "https://www.atacadao.com.br/refrigerante-pepsi-cola-21944-38140/p"},
        {"store": "Carrefour",    "url": "https://mercado.carrefour.com.br/refrigerante-pepsi-25l-garrafa-pet-7167180/p"}
    ]
}

def scrape_products(product_choice):
    """Recebe o nome do produto (coca-cola, guarana, pepsi),
       acessa os links correspondentes e retorna uma lista de dicionários
       com [store, nome, preco, url]."""

    # Verifica se temos esse produto no dicionário
    if product_choice not in PRODUCT_LINKS:
        return []

    # Configuração do Selenium
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(
        service=webdriver.chrome.service.Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    resultados = []
    for item in PRODUCT_LINKS[product_choice]:
        store_name = item["store"]
        url = item["url"]

        try:
            print(f"🔎 Acessando: {url}")
            driver.get(url)
            time.sleep(5)  # Tempo para o JavaScript carregar

            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Extrair nome do produto
            nome_elem = soup.find("h1")
            nome = nome_elem.get_text(strip=True) if nome_elem else "Nome não encontrado"

            # Extrair preço (buscando tags que contenham 'R$')
            preco_elem = soup.find(
                lambda tag: tag.name in ["span", "p"] and tag.get_text() and "R$" in tag.get_text()
            )
            preco_texto = preco_elem.get_text(strip=True) if preco_elem else "Preço não encontrado"

            # Converter preço em float
            preco_limpo = re.findall(r"\d+,\d+", preco_texto)
            preco_float = float(preco_limpo[0].replace(",", ".")) if preco_limpo else float("inf")

            # Adiciona nos resultados
            resultados.append({
                "store": store_name,
                "nome": nome,
                "preco": preco_float,
                "url": url
            })

            print(f"✅ [{store_name}] {nome} - {preco_texto}")

        except Exception as e:
            print(f"❌ Erro ao processar {url}: {e}")
            resultados.append({
                "store": store_name,
                "nome": "Erro ao extrair",
                "preco": float("inf"),
                "url": url
            })

    driver.quit()
    return resultados

@app.route('/')
def index():
    """Retorna a página HTML com o dropdown para escolha do produto."""
    return render_template("index.html")

@app.route('/api/products')
def api_products():
    """Endpoint que recebe ?product=coca-cola|guarana|pepsi e retorna JSON."""
    product_choice = request.args.get('product', '').lower()
    data = scrape_products(product_choice)
    return jsonify(data)

import os

if __name__ == '__main__':
    PORT = int(os.environ.get("PORT", 10000))  # Usa a porta que o Render define
    app.run(host="0.0.0.0", port=PORT, debug=True)

