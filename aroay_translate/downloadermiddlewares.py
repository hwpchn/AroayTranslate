import asyncio
import sys
import urllib.parse
from typing import Tuple

import twisted.internet
from pyppeteer import launch
from pyppeteer.errors import PageError, TimeoutError
from scrapy.http import HtmlResponse
from scrapy.utils.python import global_object_name
from twisted.internet.asyncioreactor import AsyncioSelectorReactor
from twisted.internet.defer import Deferred

from .pretend import SCRIPTS as PRETEND_SCRIPTS
from .settings import *
from textwrap import dedent
from urllib.request import urlopen

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

reactor = AsyncioSelectorReactor(asyncio.get_event_loop())

# install AsyncioSelectorReactor
twisted.internet.reactor = reactor
sys.modules['twisted.internet.reactor'] = reactor


def as_deferred(f):
    """
    transform a Twisted Deffered to an Asyncio Future
    :param f: async function
    """
    return Deferred.fromFuture(asyncio.ensure_future(f))


logger = logging.getLogger('daoke.aroay_translate')


class DeepLCLIArgCheckingError(Exception):
    pass


class DeepLCLIPageLoadError(Exception):
    pass


class TranslateMiddleware(object):
    """
    Downloader middleware handling the requests with Puppeteer
    """

    def _retry(self, request, reason, spider):
        """
        get retry request
        :param request:
        :param reason:
        :param spider:
        :return:
        """
        if not self.retry_enabled:
            return

        retries = request.meta.get('retry_times', 0) + 1
        retry_times = self.max_retry_times

        if 'max_retry_times' in request.meta:
            retry_times = request.meta['max_retry_times']

        stats = spider.crawler.stats
        if retries <= retry_times:
            logger.debug("Retrying %(request)s (failed %(retries)d times): %(reason)s",
                         {'request': request, 'retries': retries, 'reason': reason},
                         extra={'spider': spider})
            retryreq = request.copy()
            retryreq.meta['retry_times'] = retries
            retryreq.dont_filter = True
            retryreq.priority = request.priority + self.priority_adjust

            if isinstance(reason, Exception):
                reason = global_object_name(reason.__class__)

            stats.inc_value('retry/count')
            stats.inc_value('retry/reason_count/%s' % reason)
            return retryreq
        else:
            stats.inc_value('retry/max_reached')
            logger.error("Gave up retrying %(request)s (failed %(retries)d times): %(reason)s",
                         {'request': request, 'retries': retries, 'reason': reason},
                         extra={'spider': spider})

    @classmethod
    def from_crawler(cls, crawler):
        """
        init the middleware
        :param crawler:
        :return:
        """
        settings = crawler.settings
        logging_level = settings.get('AROAY_TRANSLATE_LOGGING_LEVEL', AROAY_TRANSLATE_LOGGING_LEVEL)
        logging.getLogger('websockets').setLevel(logging_level)
        logging.getLogger('aroay_translate').setLevel(logging_level)

        # init settings
        cls.window_width = settings.get('AROAY_TRANSLATE_WINDOW_WIDTH', AROAY_TRANSLATE_WINDOW_WIDTH)
        cls.window_height = settings.get('AROAY_TRANSLATE_WINDOW_HEIGHT', AROAY_TRANSLATE_WINDOW_HEIGHT)
        cls.default_user_agent = settings.get('AROAY_TRANSLATE_DEFAULT_USER_AGENT',
                                              AROAY_TRANSLATE_DEFAULT_USER_AGENT)
        cls.headless = settings.get('AROAY_TRANSLATE_HEADLESS', AROAY_TRANSLATE_HEADLESS)
        cls.dumpio = settings.get('AROAY_TRANSLATE_DUMPIO', AROAY_TRANSLATE_DUMPIO)
        cls.ignore_https_errors = settings.get('AROAY_TRANSLATE_IGNORE_HTTPS_ERRORS',
                                               AROAY_TRANSLATE_IGNORE_HTTPS_ERRORS)
        cls.slow_mo = settings.get('AROAY_TRANSLATE_SLOW_MO', AROAY_TRANSLATE_SLOW_MO)
        cls.ignore_default_args = settings.get('AROAY_TRANSLATE_IGNORE_DEFAULT_ARGS',
                                               AROAY_TRANSLATE_IGNORE_DEFAULT_ARGS)
        cls.handle_sigint = settings.get('AROAY_TRANSLATE_HANDLE_SIGINT', AROAY_TRANSLATE_HANDLE_SIGINT)
        cls.handle_sigterm = settings.get('AROAY_TRANSLATE_HANDLE_SIGTERM', AROAY_TRANSLATE_HANDLE_SIGTERM)
        cls.handle_sighup = settings.get('AROAY_TRANSLATE_HANDLE_SIGHUP', AROAY_TRANSLATE_HANDLE_SIGHUP)
        cls.auto_close = settings.get('AROAY_TRANSLATE_AUTO_CLOSE', AROAY_TRANSLATE_AUTO_CLOSE)
        cls.devtools = settings.get('AROAY_TRANSLATE_DEVTOOLS', AROAY_TRANSLATE_DEVTOOLS)
        cls.executable_path = settings.get('AROAY_TRANSLATE_EXECUTABLE_PATH', AROAY_TRANSLATE_EXECUTABLE_PATH)
        cls.disable_extensions = settings.get('AROAY_TRANSLATE_DISABLE_EXTENSIONS',
                                              AROAY_TRANSLATE_DISABLE_EXTENSIONS)
        cls.hide_scrollbars = settings.get('AROAY_TRANSLATE_HIDE_SCROLLBARS', AROAY_TRANSLATE_HIDE_SCROLLBARS)
        cls.mute_audio = settings.get('AROAY_TRANSLATE_MUTE_AUDIO', AROAY_TRANSLATE_MUTE_AUDIO)
        cls.no_sandbox = settings.get('AROAY_TRANSLATE_NO_SANDBOX', AROAY_TRANSLATE_NO_SANDBOX)
        cls.disable_setuid_sandbox = settings.get('AROAY_TRANSLATE_DISABLE_SETUID_SANDBOX',
                                                  AROAY_TRANSLATE_DISABLE_SETUID_SANDBOX)
        cls.disable_gpu = settings.get('AROAY_TRANSLATE_DISABLE_GPU', AROAY_TRANSLATE_DISABLE_GPU)
        cls.download_timeout = settings.get('AROAY_TRANSLATE_DOWNLOAD_TIMEOUT',
                                            settings.get('DOWNLOAD_TIMEOUT', AROAY_TRANSLATE_DOWNLOAD_TIMEOUT))
        cls.ignore_resource_types = settings.get('AROAY_TRANSLATE_IGNORE_RESOURCE_TYPES',
                                                 AROAY_TRANSLATE_IGNORE_RESOURCE_TYPES)
        cls.screenshot = settings.get('AROAY_TRANSLATE_SCREENSHOT', AROAY_TRANSLATE_SCREENSHOT)
        cls.pretend = settings.get('AROAY_TRANSLATE_PRETEND', AROAY_TRANSLATE_PRETEND)
        cls.sleep = settings.get('AROAY_TRANSLATE_SLEEP', AROAY_TRANSLATE_SLEEP)
        cls.enable_request_interception = settings.getbool('AROAY_ENABLE_REQUEST_INTERCEPTION',
                                                           AROAY_ENABLE_REQUEST_INTERCEPTION)
        cls.retry_enabled = settings.getbool('RETRY_ENABLED')
        cls.max_retry_times = settings.getint('RETRY_TIMES')
        cls.retry_http_codes = set(int(x) for x in settings.getlist('RETRY_HTTP_CODES'))
        cls.priority_adjust = settings.getint('RETRY_PRIORITY_ADJUST')

        return cls()

    # 开始
    def usage(self) -> None:
        """Print usage."""
        logger.info(dedent('''\
           $ deepl
           SYNTAX:
               $ ... | deepl <from:lang>:<to:lang>
               $ deepl <from:lang>:<to:lang> << 'EOS'
                 ...
                 EOS
               $ deepl <from:lang>:<to:lang> <<< "..."
               $ deepl <from:lang>:<to:lang> < <filepath>
           USAGE:
               $ echo Hello | deepl en:ja
               $ deepl :ru << 'EOS' # :ru is equivalent of auto:ru
                 good morning!
                 good night.
                 EOS
               $ deepl fr:zh <<< "Mademoiselle"
               $ deepl de:pl < README_de.md
           LANGUAGE CODES:
               <from:lang>: {auto it et nl el sv es sk sl cs da
                             de hu fi fr bg pl pt lv lt ro ru en zh ja}
               <to:lang>:   {it et nl el sv es sk sl cs da
                             de hu fi fr bg pl pt lv lt ro ru en zh ja}
           '''))

    def internet_on(self) -> bool:
        """Check an internet connection."""
        try:
            urlopen('https://www.google.com/', timeout=10)
            return True
        except IOError:
            return False

    def _chk_stdin(self) -> None:
        """Check if stdin is entered."""
        if (sys.stdin.isatty() and len(sys.argv) == 1) or '-h' in sys.argv:
            # if `$ deepl` or `$ deepl -h`
            self.usage()
            sys.tracebacklimit = 0
            raise DeepLCLIArgCheckingError('show help.')
        elif sys.stdin.isatty():
            # raise err if stdin is empty
            raise DeepLCLIArgCheckingError('stdin seems to be empty.')

    def _chk_argnum(self, args) -> None:
        """Check if num of args are valid."""
        num_opt = len(args)
        if num_opt != 1:
            # raise err if arity != 1
            raise DeepLCLIArgCheckingError(
                'num of option is wrong(given %d, expected 1 or 2).' % num_opt)

    def _chk_lang(self, in_lang) -> Tuple[str, str]:
        """Check if language options are valid."""
        fr_langs = {'auto', 'it', 'et', 'nl', 'el',
                    'sv', 'es', 'sk', 'sl', 'cs',
                    'da', 'de', 'hu', 'fi', 'fr',
                    'bg', 'pl', 'pt', 'lv', 'lt',
                    'ro', 'ru', 'en', 'zh', 'ja', ''}
        to_langs = fr_langs - {'', 'auto'}

        if len(in_lang) != 2 or in_lang[0] not in fr_langs \
                or in_lang[1] not in to_langs:
            # raise err if specify 2 langs is empty
            raise DeepLCLIArgCheckingError('correct your lang format.')

        if in_lang[0] == in_lang[1]:
            # raise err if <fr:lang> == <to:lang>
            raise DeepLCLIArgCheckingError('two languages cannot be same.')

        fr = ('auto' if in_lang[0] == ''
              else in_lang[0])
        to = in_lang[1]

        return (fr, to)

    def chk_cmdargs(self) -> None:
        """Check cmdargs and configurate languages.(for using as a command)"""
        self._chk_stdin()
        self._chk_argnum(sys.argv[1::])
        # self._chk_auth()

    def _chk_script(self, script: str) -> str:
        """Check cmdarg and stdin."""
        self.max_length = 5000
        script = script.rstrip("\n")

        if self.max_length is not None and len(script) > self.max_length:
            # raise err if stdin > self.max_length chr
            raise DeepLCLIArgCheckingError(
                'limit of script is less than {} chars(Now: {} chars).'.format(
                    self.max_length, len(script)))
        if len(script) <= 0:
            # raise err if stdin <= 0 chr
            raise DeepLCLIArgCheckingError('script seems to be empty.')

        return script

    async def _process_request(self, request, spider):
        """
        use aroay_translate to process spider
        :param request:
        :param spider:
        :return:
        """
        # get aroay_translate meta
        translate_meta = request.meta.get('aroay_translate') or {}
        logger.debug('translate_meta %s', translate_meta)
        if not isinstance(translate_meta, dict) or len(translate_meta.keys()) == 0:
            return

        options = {
            'headless': self.headless,
            'dumpio': self.dumpio,
            'devtools': self.devtools,
            'args': [
                f'--window-size={self.window_width},{self.window_height}',
            ]
        }
        if self.executable_path:
            options['executablePath'] = self.executable_path
        if self.ignore_https_errors:
            options['ignoreHTTPSErrors'] = self.ignore_https_errors
        if self.slow_mo:
            options['slowMo'] = self.slow_mo
        if self.ignore_default_args:
            options['ignoreDefaultArgs'] = self.ignore_default_args
        if self.handle_sigint:
            options['handleSIGINT'] = self.handle_sigint
        if self.handle_sigterm:
            options['handleSIGTERM'] = self.handle_sigterm
        if self.handle_sighup:
            options['handleSIGHUP'] = self.handle_sighup
        if self.auto_close:
            options['autoClose'] = self.auto_close
        if self.disable_extensions:
            options['args'].append('--disable-extensions')
        if self.hide_scrollbars:
            options['args'].append('--hide-scrollbars')
        if self.mute_audio:
            options['args'].append('--mute-audio')
        if self.no_sandbox:
            options['args'].append('--no-sandbox')
        if self.disable_setuid_sandbox:
            options['args'].append('--disable-setuid-sandbox')
        if self.disable_gpu:
            options['args'].append('--disable-gpu')

        # pretend as normal browser
        _pretend = self.pretend  # get global pretend setting
        if translate_meta.get('pretend') is not None:
            _pretend = translate_meta.get('pretend')  # get local pretend setting to overwrite global
        if _pretend:
            options['ignoreDefaultArgs'] = [
                '--enable-automation'
            ]
            options['args'].append('--disable-blink-features=AutomationControlled')

        # set proxy
        _proxy = translate_meta.get('proxy')
        logger.info("proxy is %s" % _proxy)
        if translate_meta.get('proxy') is not None:
            _proxy = translate_meta.get('proxy')
        if _proxy:
            # 如果有用户名和密码，则进行验证
            if "@" in str(_proxy):
                if str(_proxy).startswith("http://"):
                    self.username, self.password = str(_proxy).split("http://")[1].split("@")[0].split(":")
                    myproxy = "http://" + str(_proxy).split("http://")[1].split("@")[1]
                else:
                    self.username, self.password = str(_proxy).split("https://")[1].split("@")[0].split(":")
                    myproxy = "https://" + str(_proxy).split("http://")[1].split("@")[1]
                options['args'].append(f'--proxy-server={myproxy}')

            else:
                options['args'].append(f'--proxy-server={_proxy}')
        logger.debug('set options %s', options)

        browser = await launch(options)
        page = await browser.newPage()

        # 开始
        await page.setViewport({'width': self.window_width, 'height': self.window_height})
        # 如果有用户名和密码，验证用户名和密码
        if hasattr(self, "username") and hasattr(self, "password"):
            await page.authenticate({'username': self.username, 'password': self.password})

        if _pretend:
            _default_user_agent = self.default_user_agent
            # get Scrapy request ua, exclude default('Scrapy/2.5.0 (+https://scrapy.org)')
            if 'Scrapy' not in request.headers.get('User-Agent').decode():
                _default_user_agent = request.headers.get('User-Agent').decode()
            await page.setUserAgent(_default_user_agent)
            logger.debug('PRETEND_SCRIPTS is run')
            for script in PRETEND_SCRIPTS:
                await page.evaluateOnNewDocument(script)

        # set cookies
        parse_result = urllib.parse.urlsplit(request.url)
        domain = parse_result.hostname
        _cookies = []
        if isinstance(request.cookies, dict):
            _cookies = [{'name': k, 'value': v, 'domain': domain}
                        for k, v in request.cookies.items()]
        else:
            for _cookie in _cookies:
                if isinstance(_cookie, dict) and 'domain' not in _cookie.keys():
                    _cookie['domain'] = domain
        await page.setCookie(*_cookies)

        # the headers must be set using request interception
        await page.setRequestInterception(self.enable_request_interception)

        if self.enable_request_interception:
            @page.on('request')
            async def _handle_interception(pu_request):
                # handle headers
                overrides = {
                    'headers': pu_request.headers
                }
                # handle resource types
                _ignore_resource_types = self.ignore_resource_types
                if request.meta.get('aroay_translate', {}).get('ignore_resource_types') is not None:
                    _ignore_resource_types = request.meta.get('aroay_translate', {}).get('ignore_resource_types')
                if pu_request.resourceType in _ignore_resource_types:
                    await pu_request.abort()
                else:
                    await pu_request.continue_(overrides)

        _timeout = self.download_timeout
        if translate_meta.get('timeout') is not None:
            _timeout = translate_meta.get('timeout')

        logger.debug('crawling %s', request.url)

        response = None
        _langs = translate_meta.get('langs')
        _script = translate_meta.get('script')
        if _langs:
            self.fr_lang, self.to_lang = self._chk_lang(_langs)
        try:
            options = {
                'timeout': 1000 * _timeout
            }
            logger.debug('request %s with options %s', request.url, options)
            response = await page.goto(
                'https://www.deepl.com/translator#{}/{}/{}'.format(
                    self.fr_lang, self.to_lang, _script), options=options)
            await page.waitForSelector(
                '#dl_translator > div.lmt__text', timeout=15000)
        except (PageError, TimeoutError):
            logger.error('error rendering url %s using aroay_translate', request.url)
            await page.close()
            await browser.close()
            return self._retry(request, 504, spider)
        try:
            await page.waitForFunction('''
                        () => document.querySelector(
                        'textarea[dl-test=translator-target-input]').value !== ""
                    ''')
            await page.waitForFunction('''
                        () => !document.querySelector(
                        'textarea[dl-test=translator-target-input]').value.includes("[...]")
                    ''')
        except TimeoutError:
            await page.close()
            await browser.close()
            return self._retry(request, 504, spider)

        output_area = await page.J(
            'textarea[dl-test="translator-target-input"]')
        res = await page.evaluate('elm => elm.value', output_area)

        # sleep
        _sleep = self.sleep
        if translate_meta.get('sleep') is not None:
            _sleep = translate_meta.get('sleep')
        if _sleep is not None:
            logger.debug('sleep for %ss', _sleep)
            await asyncio.sleep(_sleep)

        body = str.encode(res)

        # close page and browser
        logger.debug('close aroay_translate')
        await page.close()
        await browser.close()

        if not response:
            logger.error('get null response by aroay_translate of url %s', request.url)

        # Necessary to bypass the compression middleware (?)
        response.headers.pop('content-encoding', None)
        response.headers.pop('Content-Encoding', None)

        response = HtmlResponse(
            page.url,
            status=response.status,
            headers=response.headers,
            body=res,
            encoding='utf-8',
            request=request
        )
        return response

    def process_request(self, request, spider):
        """
        process request using aroay_translate
        :param request:
        :param spider:
        :return:
        """
        logger.debug('processing request %s', request)
        return as_deferred(self._process_request(request, spider))

    async def _spider_closed(self):
        pass

    def spider_closed(self):
        """
        callback when spider closed
        :return:
        """
        return as_deferred(self._spider_closed())
