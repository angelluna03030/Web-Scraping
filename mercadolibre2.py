from scrapy.item import Field, Item
from scrapy.spiders import CrawlSpider, Rule
from scrapy.selector import Selector
from scrapy.loader import ItemLoader
from scrapy.linkextractors import LinkExtractor
import scrapy  # <-- Importa scrapy para usar scrapy.Request

class Producto(Item):
    titulo = Field()
    precio = Field()
    descripcion = Field()

class AmazonSpider(CrawlSpider):
    name = "merdaolibre"

    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.122 Mobile Safari/537.36",
        "DOWNLOAD_DELAY": 2,
        "AUTOTHROTTLE_ENABLED": True,
        "ROBOTSTXT_OBEY": False,
        
    }

    start_urls = ["https://listado.mercadolibre.com.co/celulares-smartphones"]
    allowed_domains = ["mercadolibre.com.co"]

    rules = (
        Rule(
            LinkExtractor(allow=r'/_Desde_\d+'),
            follow=True
        ),
        Rule(
            LinkExtractor(allow=r'/MCO-\d+'),
            callback='parse_item',
            follow=False
        ),
    )

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                callback=self.parse_start_url,
                meta={"playwright": True}
            )

    def _build_request(self, rule, link):
        """Sobrescribe para agregar Playwright a todas las requests de reglas"""
        return scrapy.Request(
            url=link.url,
            callback=self._response_downloaded,
            meta={'playwright': True},
            dont_filter=True
        )

    def parse(self, response):
        print("Título de la página:", response.xpath('//title/text()').get())
        productos = response.css('.ui-search-result__wrapper')
        print("Cantidad de productos encontrados:", len(productos))
        for producto in productos:
            yield {
                'titulo': producto.css('.ui-search-item__title::text').get(),
                'precio': producto.css('.andes-money-amount__fraction::text').get()
            }
