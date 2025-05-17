import requests
from bs4 import BeautifulSoup
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import SnowballStemmer
from collections import Counter
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import warnings
import urllib.parse
import json
import os
from langdetect import detect
import ssl

# Ignorar advertencias
warnings.filterwarnings('ignore')

# Configuración para evitar errores SSL
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Descargar recursos necesarios de NLTK
def download_nltk_resources():
    try:
        resources = ['punkt', 'stopwords']
        for resource in resources:
            try:
                nltk.data.find(f'tokenizers/{resource}')
            except LookupError:
                nltk.download(resource, quiet=True)
    except Exception as e:
        print(f"Error al descargar recursos NLTK: {e}")

download_nltk_resources()

# Diccionario de categorías con palabras clave asociadas (multilingüe)
categories = {
    'tecnologia': ['tecnología', 'software', 'hardware', 'programming', 'código', 'technology', 
                  'computer', 'computadora', 'app', 'application', 'aplicación', 'tech', 'digital'],
    'noticias': ['noticias', 'news', 'artículo', 'article', 'periodismo', 'journalism', 'reportaje', 
                'report', 'actualidad', 'diario', 'newspaper'],
    'deportes': ['deportes', 'sports', 'fútbol', 'football', 'soccer', 'baloncesto', 'basketball', 
                'tenis', 'tennis', 'deporte', 'atleta', 'athlete', 'liga', 'league'],
    'entretenimiento': ['entretenimiento', 'entertainment', 'película', 'movie', 'música', 'music', 
                       'televisión', 'television', 'serie', 'series', 'artista', 'artist'],
    'ciencia': ['ciencia', 'science', 'investigación', 'research', 'científico', 'scientific', 
               'estudio', 'study', 'experimento', 'experiment', 'descubrimiento', 'discovery'],
    'salud': ['salud', 'health', 'médico', 'medical', 'medicina', 'medicine', 'enfermedad', 
             'disease', 'tratamiento', 'treatment', 'doctor', 'hospital'],
    'educacion': ['educación', 'education', 'universidad', 'university', 'escuela', 'school', 
                 'aprendizaje', 'learning', 'estudiante', 'student', 'curso', 'course'],
    'finanzas': ['finanzas', 'finance', 'economía', 'economy', 'dinero', 'money', 'inversión', 
                'investment', 'mercado', 'market', 'banco', 'bank'],
    'viajes': ['viajes', 'travel', 'turismo', 'tourism', 'vacaciones', 'vacation', 'hotel', 
              'destino', 'destination', 'vuelo', 'flight', 'aventura', 'adventure'],
    'gastronomia': ['gastronomía', 'gastronomy', 'comida', 'food', 'receta', 'recipe', 'cocina', 
                   'cooking', 'restaurante', 'restaurant', 'chef', 'ingrediente', 'ingredient'],
    'moda': ['moda', 'fashion', 'ropa', 'clothing', 'estilo', 'style', 'diseño', 'design', 
            'tendencia', 'trend', 'modelo', 'model', 'belleza', 'beauty'],
    'politica': ['política', 'politics', 'gobierno', 'government', 'elección', 'election', 
                'partido', 'party', 'presidente', 'president', 'congreso', 'congress'],
    'otros': []  # Categoría por defecto
}

class WebContentExtractor:
    def __init__(self):
        self.language_stemmers = {
            'es': SnowballStemmer('spanish'),
            'en': SnowballStemmer('english'),
            'fr': SnowballStemmer('french'),
            'pt': SnowballStemmer('portuguese'),
            'it': SnowballStemmer('italian'),
            'de': SnowballStemmer('german'),
            'nl': SnowballStemmer('dutch'),
            'ru': SnowballStemmer('russian'),
            'fi': SnowballStemmer('finnish'),
            'sv': SnowballStemmer('swedish'),
            'no': SnowballStemmer('norwegian'),
            'da': SnowballStemmer('danish'),
        }
        
        # Inicializar modelo de clasificación
        self.classifier = Pipeline([
            ('vectorizer', TfidfVectorizer(max_features=5000)),
            ('classifier', MultinomialNB())
        ])
        
        # Datos de entrenamiento básicos
        self.training_data = []
        self.training_labels = []
        
        # Preparar datos de entrenamiento
        for category, keywords in categories.items():
            for keyword in keywords:
                self.training_data.append(keyword)
                self.training_labels.append(category)
        
        # Entrenar el clasificador si hay datos
        if self.training_data:
            self.classifier.fit(self.training_data, self.training_labels)
    
    def get_headers(self):
        """Generar encabezados para parecer un navegador real"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
    
    def extract_content(self, url):
        """Extraer contenido de una URL"""
        try:
            # Comprobar si la URL es válida
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
            
            # Realizar la solicitud con un tiempo de espera razonable
            response = requests.get(url, headers=self.get_headers(), timeout=10)
            response.raise_for_status()
            
            # Analizar el contenido HTML
            soup = BeautifulSoup(response.text, 'html.parser'  )
            
            # Extraer información principal
            data = {
                'url': url,
                'domain': urllib.parse.urlparse(url).netloc,
                'title': self._extract_title(soup),
                'meta_description': self._extract_meta_description(soup),
                'content': self._extract_main_content(soup),
                'keywords': self._extract_keywords(soup),
                'language': self._detect_language(soup),
                'links': self._extract_links(soup, url),
                'images': self._extract_images(soup, url),
                'date_published': self._extract_date(soup),
                'author': self._extract_author(soup),
            }
            
            # Categorizar el contenido
            data['category'] = self.categorize_content(data)
            
            return data
            
        except Exception as e:
            return {'error': str(e), 'url': url}
    
    def _extract_title(self, soup):
        """Extraer el título de la página"""
        title = soup.title.string if soup.title else ''
        
        # Si no hay título en la etiqueta title, buscar en h1
        if not title and soup.h1:
            title = soup.h1.get_text(strip=True)
            
        return title.strip() if title else ''
    
    def _extract_meta_description(self, soup):
        """Extraer la descripción meta"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and 'content' in meta_desc.attrs:
            return meta_desc['content'].strip()
        return ''
    
    def _extract_main_content(self, soup):
        """Extraer el contenido principal de la página"""
        # Eliminar scripts, estilos y otros elementos no deseados
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        # Intentar encontrar el contenido principal
        main_content = ''
        
        # Buscar contenedores comunes de contenido principal
        main_containers = soup.select('main, article, .content, .main, #content, #main, .post, .entry, .article')
        
        if main_containers:
            # Usar el contenedor con más texto
            main_content = max([c.get_text(separator=' ', strip=True) for c in main_containers], key=len)
        else:
            # Si no hay contenedores específicos, usar todos los párrafos
            paragraphs = soup.find_all('p')
            main_content = ' '.join([p.get_text(strip=True) for p in paragraphs])
        
        # Limpiar el texto
        main_content = re.sub(r'\s+', ' ', main_content).strip()
        
        return main_content
    
    def _extract_keywords(self, soup):
        """Extraer palabras clave de la página"""
        # Buscar metaetiqueta de palabras clave
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and 'content' in meta_keywords.attrs:
            return [kw.strip() for kw in meta_keywords['content'].split(',')]
        
        # Si no hay meta keywords, extraer palabras frecuentes del contenido
        content = self._extract_main_content(soup)
        lang = self._detect_language(soup)
        
        # Usar el idioma detectado o inglés por defecto
        lang_code = lang if lang in self.language_stemmers else 'en'
        
        # Obtener stopwords para el idioma si están disponibles
        try:
            stop_words = set(stopwords.words(self._map_lang_to_nltk(lang_code)))
        except:
            # Si no hay stopwords para este idioma, usar un conjunto vacío
            stop_words = set()
        
        # Tokenizar y filtrar palabras
        words = word_tokenize(content.lower())
        filtered_words = [w for w in words if w.isalnum() and w not in stop_words and len(w) > 2]
        
        # Stemming si está disponible
        if lang_code in self.language_stemmers:
            stemmer = self.language_stemmers[lang_code]
            filtered_words = [stemmer.stem(w) for w in filtered_words]
        
        # Contar frecuencias y devolver las 10 palabras más comunes
        word_counts = Counter(filtered_words)
        return [word for word, _ in word_counts.most_common(10)]
    
    def _map_lang_to_nltk(self, lang_code):
        """Mapear códigos de idioma a los nombres de NLTK"""
        mapping = {
            'es': 'spanish',
            'en': 'english',
            'fr': 'french',
            'pt': 'portuguese',
            'it': 'italian',
            'de': 'german',
            'nl': 'dutch',
            'ru': 'russian',
            'fi': 'finnish',
            'sv': 'swedish',
            'no': 'norwegian',
            'da': 'danish',
        }
        return mapping.get(lang_code, 'english')
    
    def _detect_language(self, soup):
        """Detectar idioma de la página"""
        # Primero verificar el atributo lang en la etiqueta html
        html_tag = soup.find('html')
        if html_tag and 'lang' in html_tag.attrs:
            lang = html_tag['lang'].split('-')[0].lower()
            if lang:
                return lang
        
        # Intentar detectar idioma del contenido
        content = self._extract_main_content(soup)
        if content:
            try:
                return detect(content[:1000])  # Usar solo los primeros 1000 caracteres
            except:
                pass
        
        # Por defecto, devolver inglés
        return 'en'
    
    def _extract_links(self, soup, base_url):
        """Extraer enlaces de la página"""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            
            # Convertir enlaces relativos a absolutos
            if href.startswith('/'):
                parsed_base = urllib.parse.urlparse(base_url)
                href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
            elif not href.startswith(('http://', 'https://')):
                href = urllib.parse.urljoin(base_url, href)
            
            if text and href.startswith(('http://', 'https://')):
                links.append({'url': href, 'text': text})
        
        # Limitar a 20 enlaces para no sobrecargar el resultado
        return links[:20]
    
    def _extract_images(self, soup, base_url):
        """Extraer imágenes de la página"""
        images = []
        for img in soup.find_all('img', src=True):
            src = img['src']
            alt = img.get('alt', '')
            
            # Convertir rutas relativas a absolutas
            if src.startswith('/'):
                parsed_base = urllib.parse.urlparse(base_url)
                src = f"{parsed_base.scheme}://{parsed_base.netloc}{src}"
            elif not src.startswith(('http://', 'https://')):
                src = urllib.parse.urljoin(base_url, src)
            
            if src.startswith(('http://', 'https://')):
                images.append({'url': src, 'alt': alt})
        
        # Limitar a 10 imágenes
        return images[:10]
    
    def _extract_date(self, soup):
        """Extraer fecha de publicación"""
        # Buscar metaetiquetas comunes para fechas
        date_meta_tags = [
            soup.find('meta', attrs={'property': 'article:published_time'}),
            soup.find('meta', attrs={'property': 'og:article:published_time'}),
            soup.find('meta', attrs={'name': 'date'}),
            soup.find('meta', attrs={'name': 'datePublished'}),
            soup.find('time')
        ]
        
        for tag in date_meta_tags:
            if tag:
                if tag.name == 'time':
                    if 'datetime' in tag.attrs:
                        return tag['datetime']
                    else:
                        return tag.get_text(strip=True)
                elif 'content' in tag.attrs:
                    return tag['content']
        
        # Buscar patrones de fecha en el texto
        content = self._extract_main_content(soup)
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # DD/MM/YYYY or MM/DD/YYYY
            r'\d{1,2}-\d{1,2}-\d{2,4}',  # DD-MM-YYYY or MM-DD-YYYY
            r'\d{4}-\d{2}-\d{2}',        # YYYY-MM-DD (ISO)
            r'\d{2}\.\d{2}\.\d{4}'       # DD.MM.YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(0)
        
        return ''
    
    def _extract_author(self, soup):
        """Extraer autor del contenido"""
        # Buscar metaetiquetas comunes para autores
        author_meta = soup.find('meta', attrs={'name': 'author'})
        if author_meta and 'content' in author_meta.attrs:
            return author_meta['content']
        
        # Buscar Schema.org o elementos comunes
        author_selectors = [
            '[itemprop="author"]',
            '.author',
            '.byline',
            '.entry-author',
            '.post-author',
            '.writer'
        ]
        
        for selector in author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                return author_elem.get_text(strip=True)
        
        return ''
    
    def categorize_content(self, data):
        """Categorizar el contenido basado en el texto y palabras clave"""
        # Crear un texto para analizar combinando título, descripción y palabras clave
        text_to_analyze = f"{data['title']} {data['meta_description']} {' '.join(data['keywords'])}"
        content_sample = data['content'][:500] if len(data['content']) > 500 else data['content']
        text_to_analyze = f"{text_to_analyze} {content_sample}"
        
        # Detectar idioma
        lang = data['language']
        
        # Convertir a minúsculas
        text_to_analyze = text_to_analyze.lower()
        
        # Detectar categoría mediante coincidencia de palabras clave
        category_scores = {}
        
        # Comprobar cada categoría
        for category, keywords in categories.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text_to_analyze:
                    score += 1
            category_scores[category] = score
        
        # Encontrar la categoría con la puntuación más alta
        best_category = max(category_scores, key=category_scores.get)
        
        # Si la mejor puntuación es 0, intentar con el clasificador
        if category_scores[best_category] == 0:
            try:
                # Predecir categoría con el clasificador
                if len(self.training_data) > 0:
                    predicted_category = self.classifier.predict([text_to_analyze])[0]
                    return predicted_category
                else:
                    return 'otros'
            except:
                return 'otros'
        
        return best_category

    def save_to_json(self, data, filename='web_content.json'):
        """Guardar datos extraídos en un archivo JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return filename

    def save_to_csv(self, data, filename='web_content.csv'):
        """Guardar datos extraídos en un archivo CSV"""
        # Aplanar la estructura para CSV
        flat_data = {
            'url': data['url'],
            'domain': data['domain'],
            'title': data['title'],
            'category': data['category'],
            'language': data['language'],
            'description': data['meta_description'],
            'content': data['content'],
            'keywords': ','.join(data['keywords']),
            'date_published': data['date_published'],
            'author': data['author'],
            'num_links': len(data['links']),
            'num_images': len(data['images'])
        }
        
        df = pd.DataFrame([flat_data])
        df.to_csv(filename, index=False, encoding='utf-8')
        return filename

# Ejemplo de uso
def main():
    extractor = WebContentExtractor()
    
    # Solicitar URL al usuario
    url = input("Ingrese la URL del sitio web a analizar: ")
    
    print(f"Analizando {url}...")
    
    # Extraer contenido
    data = extractor.extract_content(url)
    
    # Verificar si hubo errores
    if 'error' in data:
        print(f"Error al analizar la página: {data['error']}")
        return
    
    # Guardar resultados
    json_file = extractor.save_to_json(data)
    csv_file = extractor.save_to_csv(data)
    
    # Mostrar resumen
    print("\n===== RESUMEN DE CONTENIDO =====")
    print(f"URL: {data['url']}")
    print(f"Dominio: {data['domain']}")
    print(f"Título: {data['title']}")
    print(f"Categoría: {data['category']}")
    print(f"Idioma: {data['language']}")
    print(f"Descripción: {data['meta_description'][:100]}...")
    print(f"Fecha de publicación: {data['date_published']}")
    print(f"Autor: {data['author']}")
    print(f"Palabras clave: {', '.join(data['keywords'])}")
    print(f"Enlaces encontrados: {len(data['links'])}")
    print(f"Imágenes encontradas: {len(data['images'])}")
    print(f"Contenido (primeros 150 caracteres): {data['content'][:150]}...")
    print("\nDatos guardados en:")
    print(f"- JSON: {json_file}")
    print(f"- CSV: {csv_file}")

if __name__ == "__main__":
    main()