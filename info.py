from scrapy.item import Field, Item
from scrapy.spiders import Rule, CrawlSpider
from scrapy.linkextractors import LinkExtractor
from scrapy.loader import ItemLoader

class Articulo(Item):
    titulo = Field()
    contenido = Field()

class Reviews(Item):
    titulo = Field()
    calificacion = Field()

class Video(Item):  # Hereda de Item
    titulo = Field()
    fecha_de_publicacion = Field()

class IGNCrawler(CrawlSpider):
    name = "ign"
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "CLOSESPIDER_PAGECOUNT": 100
    }
    allowed_domains = ['latam.ign.com']
    start_urls = ["https://latam.ign.com/se/?model=article&q=ps4"]
    download_delay = 1  # Corregido

    rules = (
        Rule(
            LinkExtractor(allow=r'type='),
            follow=True  # Corregido
        ),
        Rule(
            LinkExtractor(allow=r'/video/'),
            callback='parse_video',
            follow=False
        ),
        Rule(
            LinkExtractor(allow=r'/news/'),
            callback='parse_news',
            follow=False
        ),
    )

    def parse_video(self, respuesta):
        item = ItemLoader(Video(), respuesta)
        item.add_xpath('titulo', '//h1/text()')
        item.add_xpath('fecha_de_publicacion', '//span[@class="publish-date"]/text()')  # Agregar /text()
        yield item.load_item()

    def parse_news(self, respuesta):
        item = ItemLoader(Articulo(), respuesta)
        item.add_xpath('titulo', '//h1/text()')
        item.add_xpath('contenido', '//div[@id="id_text"]//text()')  # Simplificado
        yield item.load_item()