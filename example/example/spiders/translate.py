import scrapy
from aroay_translate import PyppeteerRequest


class TranlateSpider(scrapy.Spider):
    name = 'tranlate'
    allowed_domains = ['deepl.com']
    start_urls = ['http://deepl.com/']

    def start_requests(self):
        for i in range(1, 2):
            yield PyppeteerRequest(
                script="愛くるしい雰囲気たっぷりの女優4人が男たちを勃起させ惑わせます！悩ましいお顔でカメラ目線の垂直式イラマチオをする美波ゆさちゃんは途中ゲホっとしつつも喉奥まで咥えてしっかりザーメン受けとめます。ムチムチボディの藤沢えみりちゃんと、スレンダー美女の橘小春ちゃんのロリ2人は馬乗りフェラとパイズリ、ラストの豊田ゆうちゃんの淫語連発カメラ目線主観オナニーは文句なしで卑猥すぎ！4人の心のこもったご奉仕をご堪能ください～",
                langs=('ja', 'zh'))

    def parse(self, response):
        print(response.text)
