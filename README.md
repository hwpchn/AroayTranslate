# AroayTranslate
主要用于scrapy 异步翻译，需要使用代理

# 使用 
`pip install --upgrade aroay-translate`

# 配置
```
DOWNLOADER_MIDDLEWARES = {
    'aroay_translate.downloadermiddlewares.PyppeteerMiddleware': 543,
}
AROAY_TRANSLATE_HEADLESS = True
```
# 使用

```
class TranlateSpider(scrapy.Spider):
    name = 'tranlate'
    allowed_domains = ['deepl.com']
    start_urls = ['http://deepl.com/']

    def start_requests(self):
        for i in range(1, 2):
            yield PyppeteerRequest(
                script="hello",
                langs=('en', 'zh'))

    def parse(self, response):
        print(response.text)

```

# 支持的语言
```
               <from:lang>: {auto it et nl el sv es sk sl cs da
                             de hu fi fr bg pl pt lv lt ro ru en zh ja}
               <to:lang>:   {it et nl el sv es sk sl cs da
                             de hu fi fr bg pl pt lv lt ro ru en zh ja}
```
