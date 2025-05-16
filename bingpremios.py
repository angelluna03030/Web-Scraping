from scrapy.item import Field
from scrapy.item import Item
from scrapy.spiders import Spider
from scrapy.selector import Selector

from scrapy.loader import ItemLoader
from bs4 import BeautifulSoup

url = "https://rewards.bing.com/redeem/?form=dash_2"

class Recompensa(Item):
    pregunta = Field()
    descripcion = Field()

class StackOverflowSpider(Spider):
    name = "rewards"
    # Esto debe ser custom_settings (plural), no custom_setting
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    start_urls = [url]

    def parse(self, response):
        sel = Selector(response)
        
        # Buscar dentro del div correcto
        recompensas = sel.xpath('//div[@id="redeemCatalog"]//div[@class="c-card-content"]')
        
        for recompensa in recompensas:
            item = ItemLoader(Recompensa(), selector=recompensa)
            
            # Extraer nombre de la recompensa
            item.add_xpath('nombre', './/h3[@class="c-heading searchByName ng-binding"]/text()')
            
            # Extraer precio con descuento
            item.add_xpath('precio_descuento', './/p[@class="ng-binding c-paragraph-4 price-after-coupon"]/text()')
            
            # Extraer precio original
            item.add_xpath('precio_original', './/p[@class="couponDiscountRemove ng-binding ng-scope c-paragraph-4"]/text()')
            
            # Extraer descuento
            item.add_xpath('descuento', './/span[@class="info-text ng-binding"]/text()')
            
            # Extraer URL de la imagen
            item.add_xpath('imagen_url', './/img[@class="c-image"]/@src')
            
            # Extraer URL de la acción
            item.add_xpath('url_accion', './/a[@class="clickable-card ng-scope"]/@href')
            
            yield item.load_item()