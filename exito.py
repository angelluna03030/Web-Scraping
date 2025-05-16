import requests
from bs4 import BeautifulSoup
import time

url = "https://www.exito.com/s?q=relojes&sort=score_desc&page=0"

encabezado = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}

# Realizar la petición con tiempo de espera
try:
    respuesta = requests.get(url, headers=encabezado, timeout=10)
    respuesta.raise_for_status()  # Verifica si la respuesta fue exitosa
    
    # Espera un momento para asegurar que la página cargue completamente
    time.sleep(2)
    
    # Parsear el HTML
    soup = BeautifulSoup(respuesta.text, 'html.parser')
    
    # Encuentra todos los artículos que representan productos
    articulos = soup.find_all("article", class_="productCard_productCard__M0677")
    
    if articulos:
        print(f"Se encontraron {len(articulos)} productos.")
        
        # Extrae y muestra información completa de cada producto
        for i, articulo in enumerate(articulos, 1):
            # Obtener marca
            marca_tag = articulo.find("h3", class_="styles_brand__IdJcB")
            marca = marca_tag.text.strip() if marca_tag else "Sin marca"
            
            # Obtener nombre del producto
            nombre_tag = articulo.find("h3", class_="styles_name__qQJiK")
            nombre = nombre_tag.text.strip() if nombre_tag else "Sin nombre"
            
            # Obtener precio con descuento (si existe)
            precio_tag = articulo.select_one("[data-fs-price='true']")
            precio = precio_tag.text.strip() if precio_tag else "Precio no disponible"
            
            # Obtener precio original (si existe)
            precio_original_tag = articulo.select_one(".priceSection_container-promotion_price-dashed__FJ7nI")
            precio_original = precio_original_tag.text.strip() if precio_original_tag else "Sin precio original"
            
            # Imprimir información
            print(f"\nProducto {i}:")
            print(f"Marca: {marca}")
            print(f"Nombre: {nombre}")
            print(f"Precio con descuento: {precio}")
            print(f"Precio original: {precio_original}")
            print("-" * 50)
    else:
        print("No se encontraron productos. La estructura del sitio puede haber cambiado.")
        print("Contenido de la página:")
        print(soup.prettify()[:500])  # Imprime parte del HTML para diagnóstico
        
except requests.exceptions.RequestException as e:
    print(f"Error al realizar la petición: {e}")
except Exception as e:
    print(f"Error inesperado: {e}")