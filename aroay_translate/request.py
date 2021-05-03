from scrapy import Request
from typing import Optional, Tuple
import copy


class TranslateRequest(Request):
    """
    Scrapy ``Request`` subclass providing additional arguments
    """

    def __init__(self, url="https://www.deepl.com", callback=None, wait_until=None, wait_for=None, script=None, proxy=None,
                 click=None,
                 sleep=None, timeout=None, ignore_resource_types=None, pretend=None, screenshot=None, meta=None,
                 langs: Optional[Tuple[str, str]] = None, *args,
                 **kwargs):
        """
        :param url: request url
        :param callback: callback
        :param one of "load", "domcontentloaded", "networkidle0", "networkidle2".
                see https://miyakogi.github.io/pyppeteer/reference.html#pyppeteer.page.Page.goto, default is `domcontentloaded`
        :param wait_for: wait for some element to load, also supports dict
        :param script: script to execute
        :param proxy: use proxy for this time, like `http://x.x.x.x:x`
        :param sleep: time to sleep after loaded, override `AROAY_TRANSLATE_SLEEP`
        :param timeout: load timeout, override `AROAY_TRANSLATE_DOWNLOAD_TIMEOUT`
        :param ignore_resource_types: ignored resource types, override `AROAY_TRANSLATE_IGNORE_RESOURCE_TYPES`
        :param pretend: pretend as normal browser, override `AROAY_TRANSLATE_PRETEND`
        :param screenshot: ignored resource types, see
                https://miyakogi.github.io/pyppeteer/_modules/pyppeteer/page.html#Page.screenshot,
                override `AROAY_TRANSLATE_SCREENSHOT`
        :param args:
        :param kwargs:
        """
        # use meta info to save args
        meta = copy.deepcopy(meta) or {}
        translate_meta = meta.get('aroay_translate') or {}

        self.wait_until = translate_meta.get('wait_until') if translate_meta.get(
            'wait_until') is not None else (wait_until or 'domcontentloaded')
        self.wait_for = translate_meta.get('wait_for') if translate_meta.get('wait_for') is not None else wait_for
        self.script = translate_meta.get('script') if translate_meta.get('script') is not None else script
        self.click = translate_meta.get('click') if translate_meta.get('click') is not None else click
        self.sleep = translate_meta.get('sleep') if translate_meta.get('sleep') is not None else sleep
        self.proxy = translate_meta.get('proxy') if translate_meta.get('proxy') is not None else proxy
        self.pretend = translate_meta.get('pretend') if translate_meta.get('pretend') is not None else pretend
        self.timeout = translate_meta.get('timeout') if translate_meta.get('timeout') is not None else timeout
        self.langs = translate_meta.get('langs') if translate_meta.get('langs') is not None else langs
        self.ignore_resource_types = translate_meta.get('ignore_resource_types') if translate_meta.get(
            'ignore_resource_types') is not None else ignore_resource_types
        self.screenshot = translate_meta.get('screenshot') if translate_meta.get(
            'screenshot') is not None else screenshot

        translate_meta = meta.setdefault('aroay_translate', {})
        translate_meta['wait_until'] = self.wait_until
        translate_meta['wait_for'] = self.wait_for
        translate_meta['script'] = self.script
        translate_meta['sleep'] = self.sleep
        translate_meta['proxy'] = self.proxy
        translate_meta['pretend'] = self.pretend
        translate_meta['timeout'] = self.timeout
        translate_meta['screenshot'] = self.screenshot
        translate_meta['ignore_resource_types'] = self.ignore_resource_types
        translate_meta['langs'] = self.langs

        super().__init__(url, callback, meta=meta, *args, **kwargs)
