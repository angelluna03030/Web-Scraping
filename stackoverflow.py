import requests
from scrapy.item import Field
from scrapy.item import Item
from scrapy.spiders import Spider
from scrapy.selector import Selector

from scrapy.loader import ItemLoader
from bs4 import BeautifulSoup

url = "https://stackoverflow.com/questions"

class Preguntas(Item):
    pregunta = Field()
    descripcion = Field()

class StackOverflowSpider(Spider):
    name = "stackoverflow"
    # Esto debe ser custom_settings (plural), no custom_setting
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    start_urls = [url]

    def parse(self, response):
        sel = Selector(response)
        # El método .get() devuelve un string. Necesitas usar .getall() o quitar el .get()
        # para obtener una lista de elementos
        preguntas = sel.xpath('//div[@id="questions"]//div[@class="s-post-summary--content"]')
        
        for pregunta in preguntas:
            item = ItemLoader(Preguntas(), selector=pregunta)
            item.add_xpath('pregunta', './/h3/a/text()')
            item.add_xpath('descripcion', './/div[@class="s-post-summary--content-excerpt"]/text()')
            yield item.load_item()




