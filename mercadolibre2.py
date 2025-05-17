from scrapy.item import Field
from scrapy.item import Item
from scrapy.spiders import Spider
from scrapy.selector import Selector
from scrapy.loader import ItemLoader

class Producto(Item):
    titulo = Field()
    precio = Field()
    patrocinado = Field()
    url = Field()

class AmazonSpider(Spider):
    name = "amazon_productos"
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    start_urls = ["https://www.amazon.com/s?k=celulares+iphone&crid=30V5MM2J4Z3S0&sprefix=celulares+i%2Caps%2C174&ref=nb_sb_ss_p13n-pd-dpltr-ranker_1_11"]

    def parse(self, response):
        sel = Selector(response)
        
        # Buscar todos los contenedores de productos
        productos = sel.xpath('//div[contains(@class, "s-result-item")]')
        
        for producto in productos:
            item = ItemLoader(Producto(), selector=producto)
            
            # Extraer título del producto - buscando el elemento h2 y el texto dentro del span
            item.add_xpath('titulo', './/h2//span/text()')
            
            # Extraer precio - buscando el span con clase a-offscreen
            item.add_xpath('precio', './/span[@class="a-price"]//span[@class="a-offscreen"]/text()')
            
            # Verificar si es patrocinado
            item.add_xpath('patrocinado', './/span[contains(text(), "Patrocinado")]/text()')
            
            # Extraer URL del producto
            item.add_xpath('url', './/h2/parent::a/@href')
            
            yield item.load_item()

