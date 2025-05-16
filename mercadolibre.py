import requests 
from lxml import html
#por defecto se envia un robots y si los servidores de la pagina que vamosa scrapear lo aceptan
#la podemos scrapear, de lo contrario si no aceptan robots no se puede scrapear 

#se puede cambiar el user agent 
#con el header
emcabezado = {
"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",

}
url = "https://listado.mercadolibre.com.co/tablet-xiaomi?sb=all_mercadolibre#D[A:tablet%20xiaomi,L:undefined]&origin=UNKNOWN&as.comp_t=SUG&as.comp_v=ta&as.comp_id=HIS"

respuesta = requests.get(url, headers=emcabezado)
#si la respuesta es 200 significa que la pagina se puede scrapear



parse = html.fromstring(respuesta.text)


relojes = parse.find_class("ui-search-layout ui-search-layout--stack")

# Verifica si hay resultados
if relojes:
    print(relojes[0].text_content())
else:
    print("No se encontraron elementos con esa clase.")
