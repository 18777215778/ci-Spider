from gevent import monkey
monkey.patch_all(thread=False)

from bs4 import BeautifulSoup
from urllib import parse
from fake_useragent import UserAgent
from saveToMongoDB import MongoDB
import requests, lxml, re, json, time, base64, gevent, hashlib, os


class WordData(object):
    '''
    由于存放单词数据
    '''
    def __init__(self):
        self.word = {
            "word": "",  # 单词
            "syll": [],  # 音节
            "symbolUK": "",  # 英式音标
            "symbolUS": "",  # 美式音标
            "proUK": [],  # 英式发音
            "proUS": [],  # 美式发音
            "defWord": {},  # 变形
            "oriWord": None,  # 原形
            "paraZh": {},  # 中文释义
            "paraEn": {},  # 英文释义
            "detParaZh": {},  # 中文详细释义
            "phrase": [],  # 词组/短语
            "highFreProp": [],  # 高频词性
            "highFrePara": [],  # 高频释义
            "sentEn": [],  # 英文例句
            "sentDB": [],  # 双语例句
            "synonym": [],  # 近义词
            "antonym": [],  # 反义词
            "affixes": []  # 词根
        }


# 所有字典对象的基类
class Base(object):

    reg = re.compile("([a-zA-Z]+)[的|\]| ]")

    def getHTML(self, **kwargs):
        '''
        :param kwargs:
        :return: 服务器响应的数据
        '''
        # 最多请求 3 次
        for i in range(1, 4):

            # 当 session 使用到指定次数后，重置 session
            if kwargs["req_count"] > 10:
                kwargs["session"].clear()
                kwargs["req_count"] = 0

            # 开始发起请求
            try:
                kwargs["headers"]["User-Agent"] = UserAgent().random
                html = kwargs["session"].get(kwargs["url"],
                                             headers = kwargs["headers"],
                                             timeout = kwargs["timeout"],
                                             allow_redirects = False)

            # 无效 URL
            except requests.exceptions.MissingSchema:
                print("Host：{} 无效 URL：{}".format(kwargs["headers"]["Host"], kwargs["url"]))
                break

            # 请求超时集合
            except (requests.exceptions.Timeout,
                    requests.exceptions.ConnectTimeout,
                    requests.exceptions.ReadTimeout):
                if (i == 3) and kwargs["msg"]:
                    print("请求 {} 超时！".format(kwargs["url"]))

            # 建立连接失败
            except requests.exceptions.ConnectionError:
                if (i == 3) and kwargs["msg"]:
                    print("连接 {} 连接失败！".format(kwargs["url"]))

            else:
                status_code = str(html.status_code)[0]
                if status_code == "2":
                    return html
                elif status_code == "3":
                    kwargs["url"] = html.headers["Location"]
                else:
                    if kwargs["msg"]:
                        print("状态码<{}> {}".format(html.status_code, kwargs["url"]))
                    return False

        else:

            return False

    def downloadAudio(self, url, headers):
        '''
        下载单词发音的音频，并保存到磁盘
        :param url: 音频的 URL
        :param headers: 请求头
        :return: 文件名
        '''
        for i in range(1, 4):
            headers["User-Agent"] = UserAgent().random
            try:
                mp3 = requests.get(url=url, headers=headers, timeout=3, allow_redirects=False)

            except  (requests.exceptions.Timeout,
                    requests.exceptions.ConnectTimeout,
                    requests.exceptions.ReadTimeout,
                    requests.exceptions.ConnectionError):
                    pass
            else:
                return mp3.content

        print("获取音频失败 {}".format(url))
        return False

    def addEle(self, word, str):
        '''
        找出例句中的当前单词，并标记出来
        :param word: 当前单词
        :param str: 例句
        :return: 标记后的例句
        '''
        wordArr = [word.lower(), word.upper(), word.title()]

        for w in wordArr:
            if " {} ".format(w) in str:
                str = str.replace(" {} ".format(w), " <mark>{}</mark> ".format(w))
                break

            elif "{} ".format(w) in str:
                str = str.replace("{} ".format(w), "<mark>{}</mark> ".format(w))
                break

            elif " {}".format(w) in str:
                str = str.replace(" {}".format(w), " <mark>{}</mark>".format(w))
                break

        return str

    def drawPrototype(self, wd, str):
        '''
        从内容中找出单词的原形形式
        :param wd: 单词数据
        :param str: 内容
        :return:
        '''
        if wd.word["oriWord"] != None: return True

        rest = re.findall(self.reg, str)
        for word in rest:
            if word != wd.word["word"]:
                wd.word["oriWord"] = word

        return True

    def running(self):
        '''
        执行对象里的成员
        :return: bool值。
        '''
        for func in self.func:

            # 负责执行 "_REQ"
            if "_REQ" in func:
                if getattr(self, func)():
                    continue
                else:
                    return False
            else:
                # 负责执行 "_ANA"
                getattr(self, func)()
        return True


# 沪江小D
class XiaoD(Base):

    def __init__(self, wd):
        self.wd = wd
        self.func = [f for f in self.__dir__() if ("_REQ" in f) or ("_ANA" in f)]

        self.url_templet = "https://dict.hjenglish.com/w/{}"
        self.requests = {
            "msg": True,
            "req_count": 0,
            "session": requests.session(),
            "url": "",
            "timeout": 5,
            "headers": {
                "Host": "dict.hjenglish.com",
                "Connection": "Close",
                "Referer": "https://dict.hjenglish.com"
            },
        }
        self.html = None
        self.soup = None

    # 获取页面的 HTML, 同时承担单词是否正确的验证
    def getPageHTML_REQ(self):

        self.requests["url"] = self.url_templet.format(self.wd.word["word"])
        html = self.getHTML(**self.requests)

        if not html: return False

        self.html = html.text
        self.soup = BeautifulSoup(self.html, "lxml")

        word = self.soup.select_one("div.word-text > h2")

        # 验证抓取到的单词是否和输入的单词一样
        if not word: return False
        word = word.get_text(strip=True)
        wls = [word.lower(), word.upper(), word.title()]
        for w in wls:
            if w == self.wd.word["word"]:
                return True
        else:
            return False

    # 获取英式音标
    def getSymbolUK_ANA(self):

        if self.wd.word["symbolUK"]: return True

        sUK = self.soup.select_one("div.pronounces > span.pronounce-value-en")

        if not sUK: return False

        self.wd.word["symbolUK"] = sUK.get_text()[1:-1]
        return True

    # 获取美式音标
    def getSymbolUS_ANA(self):

        if self.wd.word["symbolUS"]: return True

        sUS = self.soup.select_one("div.pronounces > span.pronounce-value-us")

        if not sUS: return False

        self.wd.word["symbolUS"] = sUS.get_text()[1:-1]
        return True

    # 获取中文释义
    def getParaZh_ANA(self):

        temp1 = self.soup.select("header > div.simple > p")

        if not temp1: return False

        for i in temp1:
            wProp = i.find("span", class_=False)

            if not wProp:
                wProp = "empty"
            else:
                wProp = wProp.get_text(strip=True).replace(".", "")

            wPara = i.select_one("span.simple-definition").get_text(strip=True)
            self.wd.word["paraZh"][wProp] = wPara

            # 检测释义中是否包含单词原形
            self.drawPrototype(self.wd, wPara)

        return True

    # 获取中文详细释义（例句 + 用法）
    def getDetParaZh_ANA(self):
        # 获取所有词性的详细释义
        temp1 = self.soup.select("div.word-details-item.detail > div > section > dl")

        if not temp1: return False

        # 对单条词性详细进行分解
        for i in temp1:
            temp2 = list(i.find("dt").stripped_strings)[0].replace(".", "")
            if not temp2: continue
            wProp = temp2.replace(".", "")
            self.wd.word["detParaZh"][wProp] = []

            # 对词性的不同释义分解
            for ddEle in i.find_all("dd"):
                itmePara = {}
                wPara = ddEle.select_one("p").get_text().replace("\n","").replace("\r","").replace("  ","")
                itmePara["para"] = wPara

                # 对不同释义下的例句分解
                itmePara["lj"] = []
                for phrase in ddEle.select("ul > li"):
                    pEn, pZh = list(phrase.stripped_strings)
                    pEn = self.addEle(self.wd.word["word"], pEn)
                    itmePara["lj"].append([pEn, pZh])

                self.wd.word["detParaZh"][wProp].append(itmePara)

        return True

    # 获取英式发音
    def getProUK_ANA(self):
        headers = {
            "Host":"n1audio.hjfile.cn"
        }
        audios = self.soup.select("div.pronounces > span.word-audio")

        if not audios: return False

        if "https://n1audio.hjfile.cn" in audios[0].attrs["data-src"]:
            url = audios[0].attrs["data-src"]
            file_name = self.downloadAudio(url, headers)
            if file_name:
                self.wd.word["proUK"].append(file_name)

        return True

    # 获取美式发音
    def getProUS_ANA(self):
        headers = {
            "Host": "n1audio.hjfile.cn"
        }
        audios = self.soup.select("div.pronounces > span.word-audio")

        if not audios: return False

        if (len(audios) == 2) and ("https://n1audio.hjfile.cn" in audios[1].attrs["data-src"]):
            url = audios[1].attrs["data-src"]
            file_name = self.downloadAudio(url, headers)
            if file_name:
                self.wd.word["proUS"].append(file_name)

        return True

    # 获取短语
    def getPhrase_ANA(self):
        ol = self.soup.select("ol.phrase-items > li")

        for li in ol:
            phrase = list(li.stripped_strings)
            self.wd.word["phrase"].append(phrase)

        return True

    # 解析出单词原形
    def analyzeWord_ANA(self):

        redi = self.soup.select_one("div.word-info p.redirection")

        if not redi: return False

        self.drawPrototype(self.wd, redi.get_text())


# 必应词典
class BingDict(Base):

    def __init__(self, wd):
        self.wd = wd
        self.func = [f for f in self.__dir__() if ("_REQ" in f) or ("_ANA" in f)]

        self.url_templet = "http://cn.bing.com/dict/search?q={}"
        self.requests = {
            "msg": True,
            "req_count": 0,
            "session": requests.session(),
            "url": "",
            "timeout": 5,
            "headers": {
                "Host": "cn.bing.com",
                "Connection": "Close",
                "Referer": "http://cn.bing.com/dict/"
            },
        }
        self.html = None
        self.soup = None

    # 获取页面的 HTML
    def getPageHTML_REQ(self):

        self.requests["url"] = self.url_templet.format(self.wd.word["word"])
        html = self.getHTML(**self.requests)

        if not html: return False

        self.html = html.text
        self.soup = BeautifulSoup(self.html, "lxml")

        return True

    # 判断单词是否为原形
    def judgementWord_ANA(self):

        tip = self.soup.find("div", class_="in_tip")

        if not tip: return False

        self.drawPrototype(self.wd, tip.get_text())

        return True

    # 获取双语例句
    def getSentDB_ANA(self):
        word = self.wd.word["word"]

        url = "https://cn.bing.com/dict/service?q={}+src:web&offset={}&dtype=sen"

        # 翻页
        for i in range(0,30, 10):
            self.requests["url"] = "https://cn.bing.com/dict/service?q={}+src:web&offset={}&dtype=sen".format(word, i)
            html = self.getHTML(**self.requests)
            if not html: continue

            soup = BeautifulSoup(html.text, "lxml")
            pharses = soup.select("div.se_li > div.se_li1")

            # 对每一页的例句分解
            for pharse in pharses:
                sEn = pharse.select_one("div.sen_en")
                sZh = pharse.select_one("div.sen_cn")
                if not (sEn and sZh): continue

                sEn = self.addEle(self.wd.word["word"], sEn.get_text())
                self.wd.word["sentDB"].append([sEn, sZh.get_text()])

        return True


# 金山词霸
class Iciba(Base):

    def __init__(self, wd):
        self.wd = wd
        self.func = [f for f in self.__dir__() if ("_REQ" in f) or ("_ANA" in f)]

        self.url_templet = "http://www.iciba.com/index.php?a=getWordMean&c=search&list=1,2,3,4,5,8,9,10,12,13,14,15,18,21,22,24,3003,3004,3005&word={}"
        self.requests = {
            "msg": True,
            "req_count": 0,
            "session": requests.session(),
            "url": "",
            "timeout": 5,
            "headers": {
                "Host": "www.iciba.com",
                "Connection": "Close",
                "Referer": "http://www.iciba.com/"
            },
        }
        self.json = None

    # 获取json数据
    def getJson_REQ(self):

        self.requests["url"] = self.url_templet.format(self.wd.word["word"])
        rej = self.getHTML(**self.requests)

        if not rej: return False
        deJson = rej.json()

        if deJson["errno"] != 404:
            self.json = deJson
            return True
        else:
            return False

    # 获取英式音标
    def getSymbolUK_ANA(self):
        try:
            uk = self.json["baesInfo"]["symbols"][0]["ph_en"]
            self.wd.word["symbolUK"] = uk
        except KeyError:
            return False

    # 获取美式音标
    def getSymbolUS_ANA(self):
        try:
            us = self.json["baesInfo"]["symbols"][0]["ph_am"]
            self.wd.word["symbolUS"] = us
        except KeyError:
            return False

    # 获取英式发音
    def getProUK_ANA(self):
        headers = {"Host":"res.iciba.com"}
        try:
            url = self.json["baesInfo"]["symbols"][0]["ph_en_mp3"]
            if not url: return False
            file_name = self.downloadAudio(url, headers)
            if file_name:
                self.wd.word["proUK"].append(file_name)

        except KeyError:
            return False

    # 获取美式发音
    def getProUS_ANA(self):
        headers = {"Host": "res.iciba.com"}
        try:
            url = self.json["baesInfo"]["symbols"][0]["ph_am_mp3"]
            if not url: return False
            file_name = self.downloadAudio(url, headers)
            if file_name:
                self.wd.word["proUS"].append(file_name)

        except KeyError:
            return False

    # 获取双语例句
    def getSentDB_ANA(self):
        sentBox = []

        # 位置 1
        try:
            sents = self.json["sentence"]
            for sent in sents:
                en = sent["Network_en"]
                cn = sent["Network_cn"]
                sentBox.append([en, cn])

        except KeyError: pass

        # 位置 2
        try:
            phrases = self.json["phrase"]
            for phrase in phrases:
                try:
                    en = phrase["jx"][0]["lj"][0]["lj_ly"]
                    cn = phrase["jx"][0]["lj"][0]["lj_ls"]
                    if en and cn:
                        sentBox.append([en, cn])
                except KeyError: pass
                except IndexError: pass

        except KeyError: pass

        # 位置 3
        try:
            for item in self.json["jushi"]:
                en = item["english"]
                cn = item["chinese"]
                sentBox.append([en, cn])

        except KeyError: pass

        # 位置 4
        try:
            for part in self.json["bidec"]["parts"]:
                for mean in part["means"]:
                    for sent in mean["sentences"]:
                        en = sent["en"]
                        cn = sent["cn"]
                        sentBox.append([en, cn])

        except KeyError: pass

        # 逐句添HTML元素
        for sent in sentBox:
            en = self.addEle(self.wd.word["word"], sent[0])
            cn = sent[1]
            self.wd.word["sentDB"].append([en, cn])

    # 获取英文释义
    def getParaEn_ANA(self):
        entryBox =[]

        # 层层剥离出entry, 然后放到entryBox里
        try:
            collins = self.json["collins"]
            for col in collins:
                for en in col["entry"]:
                    entryBox.append(en)

        except KeyError: pass
        except IndexError: pass

        # 整合数据
        try:
            for entry in entryBox:
                posp = entry["posp"]
                entryDict = {}

                # 当发现有字典里有不存在的词性时, 给该词性创建一个空列表
                if posp not in self.wd.word["paraEn"]:
                    self.wd.word["paraEn"][posp] = []

                entryDict["tran"] = entry["tran"]
                entryDict["def"] = entry["def"]
                entryDict["example"] = []
                for e in entry["example"]:
                    en = self.addEle(self.wd.word["word"], e["ex"])
                    cn = e["tran"]
                    entryDict["example"].append([en, cn])

                self.wd.word["paraEn"][posp].append(entryDict)
        except KeyError: pass
        except IndexError: pass

    # 获取词根
    def getaAffixes_ANA(self):

        if "stems_affixes" not in self.json:
            return False

        for aff in self.json["stems_affixes"]:
            temp = {}
            temp["type"] = aff["type"]
            temp["typeValue"] = aff["type_value"]
            temp["typeExp"] = aff["type_exp"]
            temp["sameAffixes"] = []
            for part in aff["word_parts"]:
                for a in part["stems_affixes"]:
                    dic = {}
                    dic["valueEn"] = a["value_en"]
                    dic["valueCn"] = a["value_cn"]
                    dic["wordBuile"] = a["word_buile"]
                    temp["sameAffixes"].append(dic)

            self.wd.word["affixes"].append(temp)


# 海词
class HaiCi(Base):

    def __init__(self, wd):
        self.wd = wd
        self.func = [f for f in self.__dir__() if ("_REQ" in f) or ("_ANA" in f)]

        self.url_templet = "http://www.dict.cn/{}"
        self.requests = {
            "msg": True,
            "req_count": 0,
            "session": requests.session(),
            "url": "",
            "timeout": 5,
            "headers": {
                "Host": "www.dict.cn",
                "Connection": "Close",
                "Referer": "http://www.dict.cn/"
            },
        }
        self.html = None
        self.soup = None

    # 获取页面
    def getPageHTML_REQ(self):

        self.requests["url"] = self.url_templet.format(self.wd.word["word"])
        html = self.getHTML(**self.requests)

        if html:
            self.html = html.text
            self.soup = BeautifulSoup(self.html, "lxml")
            return True
        else:
            return False

    # 获取英式发音
    def getProUK_ANA(self):
        headers = {
            "Host": "audio.dict.cn"
        }
        proUK = self.soup.select("div.phonetic > span:nth-of-type(1) > i")

        if not proUK: return False

        for i in proUK:
            url = "http://audio.dict.cn/" + i.attrs["naudio"]
            file_name = self.downloadAudio(url, headers)
            if file_name:
                self.wd.word["proUK"].append(file_name)

        return True

    # 获取美式发音
    def getProUS_ANA(self):
        headers = {
            "Host": "audio.dict.cn"
        }
        proUS = self.soup.select("div.phonetic > span:nth-of-type(2) > i")

        if not proUS: return False

        for i in proUS:
            url = "http://audio.dict.cn/" + i.attrs["naudio"]
            file_name = self.downloadAudio(url, headers)
            if file_name:
                self.wd.word["proUS"].append(file_name)

        return True

    # 获取音节
    def getStyll_ANA(self):

        if self.wd.word["syll"]: return True

        temp1 = self.soup.select_one("#content > div.main > div.word > div.word-cont > h1")

        if not(temp1 and "tip" in temp1.attrs): return False

        syll = temp1.attrs["tip"][5:]

        if self.wd.word["word"] == syll.replace("·",""):
            self.wd.word["syll"] = syll.split("·")
            return True

        return False

    # 获取变形
    def getDefWord_ANA(self):
        temp1 = self.soup.select("div.shape > label")
        temp2 = self.soup.select("div.shape > a")

        if not (temp1 and temp2):
            return False

        for i in zip(temp1, temp2):
            forms = i[0].get_text()[:-1]
            word = i[1].get_text(strip=True)
            self.wd.word["defWord"][forms] = word

        return True

    # 获取高频释义
    def getHighFrePara_ANA(self):
        temp1 = self.soup.select_one("div#dict-chart-basic")

        if not temp1:
            return False

        temp2 = parse.unquote(temp1.attrs["data"])
        highFrePara = json.loads(temp2)
        self.wd.word["highFrePara"] = highFrePara

        return True

    # 获取高频词性
    def getHighFreProp_ANA(self):
        temp1 = self.soup.select_one("div#dict-chart-examples")

        if not temp1:
            self.highFreProp = False
            return False

        temp2 = parse.unquote(temp1.attrs["data"])
        highFreProp = json.loads(temp2)
        self.wd.word["highFreProp"] = highFreProp

        return True

    # 获取近义词
    def getSynonym_ANA(self):
        temp1 = self.soup.select("#content > div.main > div.section.rel > div.layout.nfo > ul:nth-of-type(1) > li > a")

        if not temp1: return False

        for t in temp1:
            temp2 = t.get_text().strip()
            if not (" " in temp2) or ("-" in temp2):
                self.wd.word["synonym"].append(temp2)

        return True

    # 获取反义词
    def getAntonym_ANA(self):
        temp1 = self.soup.select("#content > div.main > div.section.rel > div.layout.nfo > ul:nth-of-type(2) > li > a")

        if not temp1: return False

        for t in temp1:
            temp2 = t.get_text().strip()
            if not (" " in temp2) or ("-" in temp2):
                self.wd.word["antonym"].append(temp2)

        return True


# 有道词典
class Youdao(Base):

    def __init__(self, wd):
        self.wd = wd
        self.func = [f for f in self.__dir__() if ("_REQ" in f) or ("_ANA" in f)]

        self.url_templet = "http://dict.youdao.com/w/eng/{}/#keyfrom=dict2.index"
        self.requests = {
            "msg": True,
            "req_count": 0,
            "session": requests.session(),
            "url": "",
            "timeout": 5,
            "headers": {
                "Host": "dict.youdao.com",
                "Connection": "Close",
                "Referer": "http://dict.youdao.com"
            },
        }
        self.html = None
        self.soup = None

    # 获取页面
    def getPageHTML_REQ(self):

        self.requests["url"] = self.url_templet.format(self.wd.word["word"])
        html = self.getHTML(**self.requests)

        if html:
            self.html = html.text
            self.soup = BeautifulSoup(self.html, "lxml")
            return True
        else:
            return False

    # 获取词组
    def getPhrase_ANA(self):
        pList = self.soup.select("#wordGroup2 > p")

        if not pList: return False

        for item in pList:
            phrase = list(item.stripped_strings)
            self.wd.word["phrase"].append([p.replace("\t","").replace("\n","").replace("\r","") for p in phrase])

        return True

    # 获取英文例句
    def getSentEn_REQ(self):
        word = self.wd.word["word"]
        self.requests["url"] = "http://dict.youdao.com/example/auth/{}".format(word)

        html = self.getHTML(**self.requests)

        if not html: return False

        soup = BeautifulSoup(html.text, "lxml")
        sentLi = soup.select("ul.ol > li")

        for sent in sentLi:
            sEn = self.addEle(self.wd.word["word"], sent.select_one("p:nth-of-type(1)").get_text()).strip()
            self.wd.word["sentEn"].append(sEn)

        return True


# 句酷
class Jukuu(Base):

    def __init__(self, wd):
        self.wd = wd
        self.func = [f for f in self.__dir__() if ("_REQ" in f) or ("_ANA" in f)]

        self.url_templet = "http://www.jukuu.com/show-{}-{}.html"
        self.requests = {
            "msg": False,
            "req_count": 0,
            "session": requests.session(),
            "url": "",
            "timeout": 3,
            "headers": {
                "Host": "www.jukuu.com",
                "Connection":"Close",
                "Referer": "http://www.jukuu.com"
            },
        }

    # 获取双语例句
    def getSentDB_REQ(self):

        count = 0
        page = 0
        while True:
            self.requests["url"] = self.url_templet.format(self.wd.word["word"], page)
            html = self.getHTML(**self.requests)

            if not html: break

            soup = BeautifulSoup(html.text, "lxml")

            es = soup.select("table > tr.e > td:nth-of-type(2)")
            cs = soup.select("table > tr.c > td:nth-of-type(2)")
            ss = soup.find_all("td", width="75%")

            if not (es and cs): break

            for i in zip(es, cs, ss):
                # 过滤
                if "设计"  in i[2].get_text(): continue

                e = self.addEle(self.wd.word["word"], i[0].get_text().strip())
                c = i[1].get_text().strip()
                self.wd.word["sentDB"].append([e, c])
                count += 1

            # 当翻页大于10次或例句大于30条使结束跳出循环
            if (page > 10) or (count > 30):
                count = 0
                break

            page += 1


# freeDictionary
class FreeDict(Base):

    def __init__(self, wd):
        self.wd = wd
        self.func = [f for f in self.__dir__() if ("_REQ" in f) or ("_ANA" in f)]

        self.url_templet = "http://www.thefreedictionary.com/{}"
        self.requests = {
            "msg": True,
            "req_count": 0,
            "session": requests.session(),
            "url": "",
            "timeout": 5,
            "headers": {
                "Host": "www.thefreedictionary.com",
                "Referer": "http://www.thefreedictionary.com"
            },
        }
        self.html = None
        self.soup = None

    # 获取页面
    def getPageHTML_REQ(self):

        self.requests["url"] = self.url_templet.format(self.wd.word["word"])
        html = self.getHTML(**self.requests)

        if html:
            self.html = html.text
            self.soup = BeautifulSoup(self.html, "lxml")
            return True
        else:
            return False

    # 获取英式发音
    def getProUK_ANA(self):
        headers = {
            "Host":"img2.tfd.com"
        }
        url = "http://img2.tfd.com/pron/mp3/{}.mp3"

        r = re.findall('<span class=snd2 data-snd="([\da-z/]+/UK/[\da-z/]+)"></span>', self.html)

        if not r: return False
        file_name = self.downloadAudio(url.format(r[0]), headers)
        if file_name:
            self.wd.word["proUK"].append(file_name)

        return True

    # 获取美式发音
    def getProUS_ANA(self):
        headers = {
            "Host": "img2.tfd.com"
        }
        url = "http://img2.tfd.com/pron/mp3/{}.mp3"

        r = re.findall('<span class="snd2" data-snd="([\da-z/]+/US/[\da-z/]+)">', self.html)

        if not r: return False
        file_name = self.downloadAudio(url.format(r[0]), headers)
        if file_name:
            self.wd.word["proUS"].append(file_name)

        return True

    # 获取音节
    def getSyll_ANA(self):

        if self.wd.word["syll"]: return True

        temp1 = self.soup.select_one("#Definition > section:nth-of-type(1) > h2")
        temp2 = self.soup.select("div.pseg > b")

        if not (temp1 or temp2): return False

        if not temp1: return False

        temp2.append(temp1)

        for i in temp2:
            i = i.get_text(strip=True).replace("1","")

            if self.wd.word["word"] == i.replace("·",""):
                self.wd.word["syll"] = i.split("·")

        return True


# Oxford
class Oxford(Base):

    def __init__(self, wd):
        self.wd = wd
        self.func = [f for f in self.__dir__() if ("_REQ" in f) or ("_ANA" in f)]

        self.url_templet = "https://www.oxfordlearnersdictionaries.com/definition/english/{}"
        self.requests = {
            "msg": True,
            "req_count": 0,
            "session": requests.session(),
            "url": "",
            "timeout": 5,
            "headers" :{
                "Host": "www.oxfordlearnersdictionaries.com",
                "Connection": "Close",
                "Referer": "https://www.oxfordlearnersdictionaries.com",
            },
        }
        self.html = None
        self.soup = None

    # 获取页面
    def getPageHTML_REQ(self):

        self.requests["url"] = self.url_templet.format(self.wd.word["word"])
        html = self.getHTML(**self.requests)

        if html:
            self.html = html.text
            self.soup = BeautifulSoup(self.html, "lxml")
            return True
        else:
            return False

    # 获取英式发音
    def getProUK_ANA(self):
        headers = {
            "Host":"www.oxfordlearnersdictionaries.com"
        }
        temp1 = self.soup.select_one("div.pron-uk")

        if not temp1: return False

        url = temp1.attrs["data-src-mp3"]
        if url:
            file_name = self.downloadAudio(url, headers)
            if file_name:
                self.wd.word["proUK"].append(file_name)

        return True

    # 获取美式发音
    def getProUS_ANA(self):
        headers = {
            "Host": "www.oxfordlearnersdictionaries.com"
        }
        temp1 = self.soup.select_one("div.pron-us")

        if not temp1: return False

        url = temp1.attrs["data-src-mp3"]
        if url:
            file_name = self.downloadAudio(url, headers)
            if file_name:
                self.wd.word["proUK"].append(file_name)

        return True

    # 获取双语例句
    def getSentEn_ANA(self):

        word = self.wd.word["word"]

        temp1 = self.soup.select("span.x")
        if temp1:
            for item in temp1:
                self.wd.word["sentEn"].append(self.addEle(word, item.get_text()))


# Collins
class Collins(Base):

    def __init__(self, wd):
        self.wd = wd
        self.func = [f for f in self.__dir__() if ("_REQ" in f) or ("_ANA" in f)]

        self.url_templet = "https://www.collinsdictionary.com/zh/dictionary/english/{}"
        self.requests = {
            "msg": True,
            "req_count": 0,
            "session": requests.session(),
            "url": "",
            "timeout": 5,
            "headers":{
                "Host": "www.collinsdictionary.com",
                "Connection": "Close",
                "Referer": "https://www.collinsdictionary.com",
                }
        }
        self.html = None
        self.soup = None

    # 获取页面
    def getPageHTML_REQ(self):

        self.requests["url"] = self.url_templet.format(self.wd.word["word"])
        html = self.getHTML(**self.requests)

        if html:
            self.html = html.text
            self.soup = BeautifulSoup(self.html, "lxml")
            return True
        else:
            return False

    # 获取英式发音
    def getProUK_ANA(self):

        if not self.soup: return False

        headers = {
            "Host": "www.collinsdictionary.com"
        }
        ukBox = self.soup.select_one("div.Collins_Eng_Dict")

        if not ukBox: return False

        audios = ukBox.find_all("a", class_="audio_play_button")

        if audios and ("data-src-mp3" in audios[0].attrs):
            url = audios[0].attrs["data-src-mp3"]
            file_name = self.downloadAudio(url, headers)
            if file_name:
                self.wd.word["proUK"].append(file_name)

    # 获取美式发音
    def getProUS_ANA(self):
        headers = {
            "Host": "www.collinsdictionary.com"
        }
        usBox = self.soup.select_one("div.Large_US_Webster")

        if not usBox: return False

        audios = usBox.find_all("a", class_="audio_play_button")

        if audios and ("data-src-mp3" in audios[0].attrs):
            url = audios[0].attrs["data-src-mp3"]
            file_name = self.downloadAudio(url, headers)
            if file_name:
                self.wd.word["proUK"].append(file_name)

    # 获取英文例句
    def getSentEn_ANA(self):

        word = self.wd.word["word"]

        temp1 = self.soup.select("div.type-example > span.quote")
        if temp1:
            for item in temp1:
                sent = self.addEle(word, item.get_text().strip().replace("\n", " "))
                self.wd.word["sentEn"].append(sent)


# merriam-webster
class MerriamWebster(Base):

    def __init__(self, wd):
        self.wd = wd
        self.func = [f for f in self.__dir__() if ("_REQ" in f) or ("_ANA" in f)]

        self.url_templet = "https://www.merriam-webster.com/dictionary/{}"
        self.requests = {
            "msg": True,
            "req_count":0,
            "session": requests.session(),
            "url": "",
            "timeout": 5,
            "headers": {
                "Host": "www.merriam-webster.com",
                "Connection": "Close",
                "Referer": "https://www.merriam-webster.com/",
            }
        }
        self.html = None
        self.soup = None

    # 获取页面
    def getPageHTML_REQ(self):

        self.requests["url"] = self.url_templet.format(self.wd.word["word"])
        html = self.getHTML(**self.requests)

        if html:
            self.html = html.text
            self.soup = BeautifulSoup(self.html, "lxml")
            return True
        else:
            return False

    # 获取音节
    def getStyll_ANA(self):

        if self.wd.word["syll"]: return True

        temp1 = self.soup.select_one("div.entry-header > div.entry-attr > span.word-syllables")

        if temp1:
            syll = temp1.get_text(strip = True)
        else:
            return False

        if self.wd.word["word"] == syll.replace("·", ""):
            self.wd.word["syll"] = syll.split("·")
            return True
        else:
            return False

    # 获取英文例句
    def getSentEn_ANA(self):

        word = self.wd.word["word"]

        # 第 1 处位置
        temp1 = self.soup.select("div.examples-box > div.inner-box-wrapper > div.card-primary-content > ol.definition-list > li > p.definition-inner-item")
        if temp1:
            for item in temp1:
                self.wd.word["sentEn"].append(self.addEle(word, item.get_text()))

        # 第 2 处位置
        temp2 = self.soup.select("div.fresh-examples-box > div.inner-box-wrapper > div.card-primary-content > ul.fresh-example-list > li > div.cite-example")
        if temp2:
            for item in temp2:
                self.wd.word["sentEn"].append(self.addEle(word, item.get_text()))


# 开始单词的抓取工作
def start(wl_queue, wd_queue):
    '''
    开始从网络上抓取单词数据
    :param queue: 单词队列
    :param child_conn:
    :return: None
    '''
    db = MongoDB()
    wd = WordData()
    # 所有的字典对象
    allDict = []
    for cls in globals():
        try:
            # 从 globals() 取出全局的对象，并然后使用 issubclass() 方法逐一判断是否为 Base 的子类，
            # 然后添加到 allDict() 列表中（排除 Base 本身）
            if (issubclass(globals()[cls], Base)) and not(globals()[cls] is Base):
                allDict.append(globals()[cls](wd))
        except TypeError:
            pass

    while not wl_queue.empty():
        wd.word["word"] = wl_queue.get(timeout=10)
        # 从数据库查询单词是否已收录
        if db.sureBe(wd.word["word"]):
            print("\033[32m{} 已收录\033[0m".format(wd.word["word"]))
            continue

        # 以沪江小D词典为准，判断单词是否存在或符合抓取标准
        if not allDict[0].running():
            print("\033[31m{} 可能不存在或不符合抓取标准\033[0m".format(wd.word["word"]))
            wd.word["full"] = False
            wd_queue.put(wd.word)
            continue

        gevent.joinall([gevent.spawn(dict.running) for dict in allDict[1:]])
        wd_queue.put(wd.word)
        wd.__init__()


# 整体测试
def fullTest(wordlist):
    wd = WordData()
    db = MongoDB()
    allDict = []
    for cls in globals():
        try:
            if (issubclass(globals()[cls], Base)) and not (globals()[cls] is Base):
                allDict.append(globals()[cls](wd))
        except TypeError:
            pass

    # 放入需要测试的单词
    for word in wordlist:
        wd.word["word"] = word

        # 从数据库查询单词是否已收录
        if db.sureBe(wd.word["word"]):
            print("\033[32m{} 已收录\033[0m".format(wd.word["word"]))
            continue

        # 以沪江小D词典为准，判断单词是否存在或符合抓取标准
        if not allDict[0].running():
            print("\033[31m{} 可能不存在或不符合抓取标准\033[0m".format(wd.word["word"]))
            continue

        gevent.joinall([gevent.spawn(dict.running) for dict in allDict[1:]])
        # db.add_one(wd.word)
        wd.__init__()


# 单元测试
def unitTest(wordlist):
    wd = WordData()
    example = Oxford(wd)

    for w in wordlist:
        wd.word["word"] = w
        example.running()
        print(wd.word["sentEn"])
        wd.__init__()


if __name__ == '__main__':
    # unitTest(["looking"])
    fullTest(["looking"])

