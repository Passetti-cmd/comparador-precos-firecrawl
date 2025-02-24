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
        {"store": "Lojas Rede", "url": "https://www.lojasrede.com.br/refrigerante-coca-cola-lata-310ml/p?idsku=798004&srsltid=AfmBOopsrxvPMQ3bemiK9ykI3owNZMmwSHoZM9h1ZuEFvqSCwi6_k1IDIhM"},
        {"store": "Atacadão", "url": "https://www.atacadao.com.br/refrigerante-coca-cola-sleek-lata-com-310ml-55803-4100/p"},
        {"store": "Carrefour", "url": "https://mercado.carrefour.com.br/cocacola-lata-310-ml-8666822/p"}
    ],
    "guarana": [
        {"store": "Pão de Açúcar", "url": "https://www.paodeacucar.com/produto/11428/refrigerante-guarana-diet-antarctica-garrafa-2l"},
        {"store": "Amazon", "url": "https://www.amazon.com.br/Antarctica-Refrigerante-Guaraná-Pet/dp/B006DQOXTY/ref=sr_1_1"},
        {"store": "Atacadão", "url": "https://www.atacadao.com.br/refrigerante-guarana-antarctica-19691-5482/p"},
        {"store": "Carrefour", "url": "https://mercado.carrefour.com.br/refrigerante-guarana-antarctica-garrafa-2l-156396/p"}
    ],
    "pepsi": [
        {"store": "Pão de Açúcar", "url": "https://www.paodeacucar.com/produto/149709/refrigerante-pepsi-garrafa-2l"},
        {"store": "Amazon", "url": "https://www.amazon.com.br/Refrigerante-Pepsi-Pet-2-Litros/dp/B07Y2F2D85/ref=sr_1_17"},
        {"store": "Atacadão", "url": "https://www.atacadao.com.br/refrigerante-pepsi-cola-21944-38140/p"},
        {"store": "Carrefour", "url": "https://mercado.carrefour.com.br/refrigerante-pepsi-25l-garrafa-pet-7167180/p"}
    ]
}

def scrape_products(product_choice):
    """Recebe o nome do produto (coca-cola, guarana, pepsi),
       acessa os links correspondentes e retorna uma lista de dicionários
       com [store, nome, preco, url]."""

    if product_choice not in PRODUCT_LINKS:
        return []

    # Configuração do Selenium para funcionar no Render
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")  # Essencial em ambientes de contêiner
    chrome_options.binary_location = "/usr/bin/google-chrome-stable"  # Caminho do Chrome no Render

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
            preco_elem = soup.find(lambda tag: tag.name in ["span", "p"] and tag.get_text() and "R$" in tag.get_text())
            preco_texto = preco_elem.get_text(strip=True) if preco_elem else "Preço não encontrado"

            # Converter preço em float
            preco_limpo = re.findall(r"\d+,\d+", preco_texto)
            preco_float = float(preco_limpo[0].replace(",", ".")) if preco_limpo else float("inf")

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

if __name__ == '__main__':
    PORT = int(os.environ.get("PORT", 10000))  # Usa a porta definida pelo ambiente (Render define PORT)
    app.run(host="0.0.0.0", port=PORT, debug=True)
