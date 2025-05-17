import requests
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urlparse
import pandas as pd
from collections import defaultdict
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import hashlib
import logging
import os
# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebContentExtractor:
    def __init__(self):
        # Descargar recursos NLTK necesarios (solo la primera vez)
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('punkt')
            nltk.download('stopwords')
        
        self.stop_words = set(stopwords.words('english') + stopwords.words('spanish'))
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Patrones para identificar tipos específicos de contenido
        self.patterns = {
            'price': r'(\$|€|£|\bUSD|\bEUR|\bGBP|\bMXN|\bUS\$)?\s?(\d+[.,]\d+|\d+)\s?(\$|€|£|\bUSD|\bEUR|\bGBP|\bMXN)?',
            'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            'phone': r'(\+\d{1,3})?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}',
            'url': r'https?://[^\s]+',
            'date': r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{2,4}[/-]\d{1,2}[/-]\d{1,2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{2,4}'
        }
        
        # Categorías comunes de contenido
        self.categories = {
            'product': ['product', 'item', 'buy', 'price', 'shop', 'purchase', 'cart', 'checkout', 'add to cart'],
            'article': ['article', 'post', 'blog', 'news', 'story', 'publish', 'author', 'read'],
            'profile': ['profile', 'user', 'account', 'login', 'signin', 'signup', 'register'],
            'contact': ['contact', 'email', 'phone', 'call', 'message', 'support', 'help'],
            'about': ['about', 'company', 'history', 'mission', 'vision', 'team', 'staff'],
            'service': ['service', 'tool', 'solution', 'software', 'platform', 'app', 'application']
        }
        
        # Equivalentes en español
        self.es_categories = {
            'producto': ['producto', 'artículo', 'comprar', 'precio', 'tienda', 'compra', 'carrito', 'pagar', 'añadir'],
            'artículo': ['artículo', 'publicación', 'blog', 'noticia', 'historia', 'publicar', 'autor', 'leer'],
            'perfil': ['perfil', 'usuario', 'cuenta', 'iniciar sesión', 'ingresar', 'registrarse'],
            'contacto': ['contacto', 'correo', 'teléfono', 'llamar', 'mensaje', 'soporte', 'ayuda'],
            'acerca': ['acerca', 'empresa', 'historia', 'misión', 'visión', 'equipo', 'personal'],
            'servicio': ['servicio', 'herramienta', 'solución', 'software', 'plataforma', 'app', 'aplicación']
        }
        
        # Unir ambos conjuntos de categorías
        for es_cat, es_words in self.es_categories.items():
            en_cat = self.translate_category(es_cat)
            if en_cat in self.categories:
                self.categories[en_cat].extend(es_words)
    
    def translate_category(self, es_cat):
        """Mapea categorías en español a inglés"""
        translations = {
            'producto': 'product',
            'artículo': 'article',
            'perfil': 'profile',
            'contacto': 'contact',
            'acerca': 'about',
            'servicio': 'service'
        }
        return translations.get(es_cat, es_cat)
    
    def get_webpage_content(self, url):
        """Obtiene el contenido HTML de una URL"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error obteniendo la página {url}: {e}")
            return None
    
    def clean_text(self, text):
        """Limpia el texto de caracteres no deseados y espacios en blanco adicionales"""
        if not text:
            return ""
        # Eliminar etiquetas HTML restantes
        text = re.sub(r'<[^>]+>', ' ', text)
        # Eliminar caracteres especiales y múltiples espacios en blanco
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s.,;:!?¿¡\-$€£%&()[\]{}\'\"]+', ' ', text)
        return text.strip()
    
    def extract_main_content(self, soup):
        """Intenta identificar y extraer el contenido principal de la página"""
        # Candidatos para contenido principal
        main_candidates = soup.find_all(['main', 'article', 'div', 'section'], 
                                      class_=lambda c: c and any(x in str(c).lower() for x in 
                                                            ['main', 'content', 'article', 'post', 'product']))
        
        if not main_candidates:
            main_candidates = soup.find_all(['div', 'section'], 
                                          style=lambda s: s and 'width' in s and ('margin' in s or 'padding' in s))
        
        if main_candidates:
            # Ordenar por cantidad de texto y elegir el que tenga más
            return max(main_candidates, key=lambda x: len(x.get_text(strip=True)))
        else:
            # Si no se encuentra contenido principal, usar body
            return soup.body
    
    def extract_text_elements(self, soup):
        """Extrae todos los elementos de texto con su jerarquía"""
        elements = []
        
        # Extraer título de la página
        title = soup.title.get_text() if soup.title else ""
        if title:
            elements.append({
                'type': 'title',
                'text': self.clean_text(title),
                'importance': 10
            })
        
        # Extraer encabezados
        for i in range(1, 7):
            for heading in soup.find_all(f'h{i}'):
                text = heading.get_text(strip=True)
                if text:
                    elements.append({
                        'type': f'h{i}',
                        'text': self.clean_text(text),
                        'importance': 10 - i
                    })
        
        # Extraer párrafos
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if text and len(text) > 15:  # Filtrar párrafos muy cortos
                elements.append({
                    'type': 'paragraph',
                    'text': self.clean_text(text),
                    'importance': 3
                })
        
        # Extraer listas
        for list_tag in soup.find_all(['ul', 'ol']):
            items = []
            for li in list_tag.find_all('li'):
                item_text = li.get_text(strip=True)
                if item_text:
                    items.append(self.clean_text(item_text))
            
            if items:
                elements.append({
                    'type': 'list',
                    'items': items,
                    'importance': 4
                })
        
        # Extraer imágenes con descripciones
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            if src and (src.startswith('http') or src.startswith('/')):
                elements.append({
                    'type': 'image',
                    'src': src,
                    'alt': self.clean_text(alt),
                    'importance': 5
                })
        
        return elements
    
    def extract_structured_data(self, soup, url):
        """Extrae datos estructurados como JSON-LD o microdata"""
        structured_data = []
        
        # Extraer JSON-LD
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                structured_data.append({
                    'type': 'json-ld',
                    'data': data
                })
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Extraer microdata
        items = soup.find_all(itemscope=True)
        for item in items:
            item_type = item.get('itemtype', '')
            if item_type:
                props = {}
                for prop in item.find_all(itemprop=True):
                    prop_name = prop.get('itemprop', '')
                    if prop_name:
                        # Intentar extraer el valor dependiendo del tipo de elemento
                        if prop.name == 'meta':
                            props[prop_name] = prop.get('content', '')
                        elif prop.name in ('img', 'audio', 'video', 'source'):
                            props[prop_name] = prop.get('src', '')
                        elif prop.name == 'a':
                            props[prop_name] = prop.get('href', '')
                        elif prop.name == 'time':
                            props[prop_name] = prop.get('datetime', prop.get_text(strip=True))
                        else:
                            props[prop_name] = prop.get_text(strip=True)
                
                structured_data.append({
                    'type': 'microdata',
                    'itemType': item_type,
                    'properties': props
                })
        
        return structured_data
    
    def extract_specific_patterns(self, text):
        """Extrae patrones específicos como precios, emails, teléfonos, etc."""
        results = {}
        
        for pattern_name, pattern in self.patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                if pattern_name == 'price':
                    # Procesar precios de manera especial para unificar formato
                    cleaned_prices = []
                    for match in matches:
                        if isinstance(match, tuple):
                            price = ''.join([m for m in match if m])
                            cleaned_prices.append(price)
                        else:
                            cleaned_prices.append(match)
                    results[pattern_name] = cleaned_prices
                else:
                    results[pattern_name] = matches
        
        return results
    
    def detect_language(self, text):
        """Detecta el idioma del texto basado en palabras comunes"""
        if not text or len(text) < 20:
            return "unknown"
        
        # Palabras comunes en inglés y español
        en_common = {'the', 'and', 'is', 'in', 'to', 'it', 'of', 'for', 'with', 'on', 'at', 'this'}
        es_common = {'el', 'la', 'los', 'las', 'y', 'es', 'en', 'de', 'para', 'con', 'por', 'este', 'esta'}
        
        tokens = set(word.lower() for word in word_tokenize(text)[:100])
        
        en_count = sum(1 for word in tokens if word in en_common)
        es_count = sum(1 for word in tokens if word in es_common)
        
        return "es" if es_count > en_count else "en"
    
    def categorize_content(self, elements, url):
        """Categoriza el contenido basado en palabras clave"""
        domain = urlparse(url).netloc
        raw_text = ' '.join([e.get('text', '') for e in elements if isinstance(e.get('text', ''), str)])
        
        # Detectar idioma
        language = self.detect_language(raw_text)
        
        # Tokenizar todo el texto
        tokens = [word.lower() for word in word_tokenize(raw_text) if word.lower() not in self.stop_words]
        
        # Contar ocurrencias de palabras clave por categoría
        category_scores = defaultdict(int)
        for category, keywords in self.categories.items():
            for keyword in keywords:
                category_scores[category] += tokens.count(keyword.lower())
        
        # Determinar categoría principal
        if category_scores:
            main_category = max(category_scores.items(), key=lambda x: x[1])[0]
        else:
            # Inferir por el dominio
            if any(word in domain for word in ['shop', 'store', 'tienda']):
                main_category = 'product'
            elif any(word in domain for word in ['blog', 'news', 'noticia']):
                main_category = 'article'
            else:
                main_category = 'unknown'
        
        return {
            'main_category': main_category,
            'language': language,
            'all_categories': dict(category_scores)
        }
    
    def extract_products(self, soup, patterns_found):
        """Extrae información de productos si se detectan"""
        products = []
        
        # Buscar elementos de producto comunes
        product_containers = soup.find_all(['div', 'li', 'article'], 
                                         class_=lambda c: c and any(x in str(c).lower() for x in 
                                                               ['product', 'item', 'card', 'resultado']))
        
        for container in product_containers:
            product = {}
            
            # Extraer título
            title_elem = container.find(['h1', 'h2', 'h3', 'h4', 'h5', 'div', 'span'], 
                                      class_=lambda c: c and any(x in str(c).lower() for x in 
                                                            ['title', 'name', 'producto', 'nombre']))
            if title_elem:
                product['title'] = self.clean_text(title_elem.get_text())
            
            # Extraer precio
            price_elem = container.find(['span', 'div', 'p'], 
                                      class_=lambda c: c and any(x in str(c).lower() for x in 
                                                            ['price', 'precio', 'cost', 'amount']))
            if price_elem:
                product['price'] = self.clean_text(price_elem.get_text())
            
            # Extraer imagen
            img_elem = container.find('img')
            if img_elem and img_elem.get('src'):
                product['image'] = img_elem.get('src')
            
            # Extraer URL
            link_elem = container.find('a')
            if link_elem and link_elem.get('href'):
                product['url'] = link_elem.get('href')
            
            # Solo añadir si tiene título o precio
            if product.get('title') or product.get('price'):
                products.append(product)
        
        return products if products else None
    
    def extract_articles(self, soup):
        """Extrae información de artículos si se detectan"""
        articles = []
        
        # Buscar elementos de artículo comunes
        article_containers = soup.find_all(['article', 'div', 'section'], 
                                         class_=lambda c: c and any(x in str(c).lower() for x in 
                                                               ['article', 'post', 'blog', 'news', 'noticia']))
        
        for container in article_containers:
            article = {}
            
            # Extraer título
            title_elem = container.find(['h1', 'h2', 'h3', 'h4'], 
                                      class_=lambda c: c and any(x in str(c).lower() for x in 
                                                            ['title', 'heading', 'titulo']))
            if title_elem:
                article['title'] = self.clean_text(title_elem.get_text())
            
            # Extraer fecha
            date_elem = container.find(['time', 'span', 'div'], 
                                     class_=lambda c: c and any(x in str(c).lower() for x in 
                                                           ['date', 'time', 'fecha', 'published']))
            if date_elem:
                article['date'] = self.clean_text(date_elem.get_text())
            
            # Extraer autor
            author_elem = container.find(['span', 'div', 'a'], 
                                       class_=lambda c: c and any(x in str(c).lower() for x in 
                                                             ['author', 'autor', 'by']))
            if author_elem:
                article['author'] = self.clean_text(author_elem.get_text())
            
            # Extraer resumen
            summary_elem = container.find(['p', 'div'], 
                                       class_=lambda c: c and any(x in str(c).lower() for x in 
                                                             ['summary', 'excerpt', 'resumen', 'description']))
            if summary_elem:
                article['summary'] = self.clean_text(summary_elem.get_text())
            
            # Solo añadir si tiene título
            if article.get('title'):
                articles.append(article)
        
        return articles if articles else None
    
    def extract_metadata(self, soup):
        """Extrae metadatos del head de la página"""
        metadata = {}
        
        # Extraer título
        if soup.title:
            metadata['title'] = self.clean_text(soup.title.get_text())
        
        # Extraer meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name', meta.get('property', ''))
            content = meta.get('content')
            
            if name and content:
                name = name.lower()
                if name in ['description', 'keywords', 'author', 'viewport', 'robots']:
                    metadata[name] = content
                elif name.startswith('og:') or name.startswith('twitter:'):
                    metadata[name] = content
        
        return metadata
    
    def cache_key(self, url):
        """Genera una clave única para la caché basada en la URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def save_to_cache(self, url, data):
        """Guarda los datos extraídos en una caché local"""
        try:
            cache_dir = 'web_cache'
            os.makedirs(cache_dir, exist_ok=True)
            
            key = self.cache_key(url)
            cache_file = os.path.join(cache_dir, f"{key}.json")
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Datos guardados en caché: {cache_file}")
        except Exception as e:
            logger.error(f"Error guardando caché: {e}")
    
    def load_from_cache(self, url):
        """Carga datos de la caché si existen"""
        try:
            key = self.cache_key(url)
            cache_file = os.path.join('web_cache', f"{key}.json")
            
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"Datos cargados desde caché: {cache_file}")
                return data
        except Exception as e:
            logger.error(f"Error cargando caché: {e}")
        
        return None
    
    def extract_all(self, url, use_cache=True):
        """Punto de entrada principal - extrae toda la información de la URL"""
        # Comprobar caché primero
        if use_cache:
            cached_data = self.load_from_cache(url)
            if cached_data:
                return cached_data
        
        html_content = self.get_webpage_content(url)
        if not html_content:
            return {"error": "No se pudo obtener el contenido de la página"}
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Obtener el contenido principal
        main_content = self.extract_main_content(soup)
        
        # Extraer elementos de texto
        text_elements = self.extract_text_elements(main_content if main_content else soup)
        
        # Extraer datos estructurados
        structured_data = self.extract_structured_data(soup, url)
        
        # Extraer texto completo para búsqueda de patrones
        full_text = ' '.join([e.get('text', '') for e in text_elements if isinstance(e.get('text', ''), str)])
        
        # Extraer patrones específicos
        patterns_found = self.extract_specific_patterns(full_text)
        
        # Categorizar el contenido
        categorization = self.categorize_content(text_elements, url)
        
        # Extraer metadatos
        metadata = self.extract_metadata(soup)
        
        # Resultados específicos según la categoría
        specific_data = None
        if categorization['main_category'] == 'product':
            specific_data = self.extract_products(soup, patterns_found)
        elif categorization['main_category'] == 'article':
            specific_data = self.extract_articles(soup)
        
        # Compilar todos los resultados
        results = {
            'url': url,
            'metadata': metadata,
            'categorization': categorization,
            'main_elements': text_elements[:10],  # Limitar a los 10 principales elementos por brevedad
            'patterns_found': patterns_found,
            'specific_data': specific_data,
            'structured_data_count': len(structured_data)  # Solo contar para no hacer el JSON muy grande
        }
        
        # Guardar en caché
        self.save_to_cache(url, results)
        
        return results

    def extract_and_print_summary(self, url):
        """Extrae información y la presenta de forma resumida y legible"""
        results = self.extract_all(url)
        
        print("\n" + "="*80)
        print(f"ANÁLISIS DE PÁGINA WEB: {url}")
        print("="*80)
        
        if 'error' in results:
            print(f"\nERROR: {results['error']}")
            return
        
        # Metadatos básicos
        print("\n📄 INFORMACIÓN BÁSICA:")
        print(f"  Título: {results['metadata'].get('title', 'No disponible')}")
        print(f"  Descripción: {results['metadata'].get('description', 'No disponible')}")
        
        # Categorización
        print(f"\n🔍 TIPO DE PÁGINA: {results['categorization']['main_category'].upper()}")
        print(f"  Idioma detectado: {results['categorization']['language']}")
        
        # Elementos principales
        print("\n📝 CONTENIDO PRINCIPAL:")
        for i, elem in enumerate(results['main_elements'][:5], 1):
            if elem['type'] == 'paragraph':
                print(f"  {i}. Párrafo: {elem['text'][:100]}...")
            elif elem['type'].startswith('h'):
                print(f"  {i}. {elem['type'].upper()}: {elem['text']}")
            elif elem['type'] == 'list':
                print(f"  {i}. Lista: {', '.join(elem['items'][:3])}...")
        
        # Información específica según categoría
        if results['specific_data']:
            if results['categorization']['main_category'] == 'product':
                print("\n🛒 PRODUCTOS DETECTADOS:")
                for i, product in enumerate(results['specific_data'][:3], 1):
                    print(f"  {i}. {product.get('title', 'Sin título')} - {product.get('price', 'Precio no disponible')}")
            
            elif results['categorization']['main_category'] == 'article':
                print("\n📰 ARTÍCULOS DETECTADOS:")
                for i, article in enumerate(results['specific_data'][:3], 1):
                    print(f"  {i}. {article.get('title', 'Sin título')}")
                    if 'date' in article:
                        print(f"     Fecha: {article['date']}")
                    if 'author' in article:
                        print(f"     Autor: {article['author']}")
        
        # Patrones encontrados
        print("\n🔢 DATOS ESPECÍFICOS ENCONTRADOS:")
        if results['patterns_found'].get('price'):
            print(f"  Precios: {', '.join(results['patterns_found']['price'][:5])}")
        if results['patterns_found'].get('email'):
            print(f"  Emails: {', '.join(results['patterns_found']['email'][:3])}")
        if results['patterns_found'].get('phone'):
            print(f"  Teléfonos: {', '.join(results['patterns_found']['phone'][:3])}")
        
        print("\n" + "="*80)
        print("ANÁLISIS COMPLETADO")
        print("="*80 + "\n")
        
        return results

# Ejemplo de uso
if __name__ == "__main__":
    extractor = WebContentExtractor()
    url = input("Ingresa la URL de la página web a analizar: ")
    extractor.extract_and_print_summary(url)
    
    # Guardar resultados completos en JSON
    results = extractor.extract_all(url)
    with open('resultados_analisis.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"Resultados completos guardados en 'resultados_analisis.json'")