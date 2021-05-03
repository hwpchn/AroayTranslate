# AroayTranslate
主要用于scrapy 异步翻译，需要使用代理

# 使用 
`pip install --upgrade aroay-translate`

# 配置
```
DOWNLOADER_MIDDLEWARES = {
    'aroay_translate.downloadermiddlewares.TranslateMiddleware': 543,
}
AROAY_TRANSLATE_HEADLESS = True
```
# 使用

`dont_filter=True 必须设置，因为翻译都是请求同一个网址`

```
class TranlateSpider(scrapy.Spider):
    name = 'tranlate'
    allowed_domains = ['deepl.com']
    start_urls = ['http://deepl.com/']

    def start_requests(self):
        """
        script :需要翻译
        langs： 翻译语言选择
        :return:
        """
        for i in range(1, 2):
            yield TranslateRequest(
                script="愛くるしい雰囲気たっぷりの女優4人が男たちを勃起させ惑わせます！悩ましいお顔でカメラ目線の垂直式イラマチオをする美波ゆさちゃんは途中ゲホっとしつつも喉奥まで咥えてしっかりザーメン受けとめます。ムチムチボディの藤沢えみりちゃんと、スレンダー美女の橘小春ちゃんのロリ2人は馬乗りフェラとパイズリ、ラストの豊田ゆうちゃんの淫語連発カメラ目線主観オナニーは文句なしで卑猥すぎ！4人の心のこもったご奉仕をご堪能ください～",
                langs=('ja', 'zh'),dont_filter=True)

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
