from bs4 import BeautifulSoup
from urllib import parse
from fake_useragent import UserAgent
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import requests, lxml, re, json, time, os, threading, base64


class Base:

    def __init__(self):
        self.mdb = MongoDB()
        self.word = {
            "word": "",  # 单词
            "syll": [],  # 音节
            "symbolUK": "",  # 英式音标
            "symbolUS": "",  # 美式音标
            "proUK": [],  # 英式发音
            "proUS": [],  # 美式发音
            "deformedWord":{},  # 变形
            "originalWord":{},  # 原形
            "paraZh":{},  # 中文释义
            "paraEn": {},  # 英文释义
            "detParaZh": {},  # 中文详细释义
            "phrase": [],  # 词组/短语
            "highFreProp":[],  # 高频词性
            "highFrePara":[],  # 高频释义
            "sentEn":[],  # 英文例句
            "sentDB":[],  # 双语例句
            "synonym":[],  # 近义词
            "antonym":[],  # 反义词
            "affixes":[]    #词根
        }


    # 获取网页源代码
    # 接收参数：会话对象、URL、请求头、超时时间
    def getHTML(self, s, url, header, timeout):

            # 最多请求 3 次
            for i in range(1, 4):
                try:
                    header["User-Agent"] = UserAgent().random
                    html = s.get(url, headers=header, timeout=timeout)

                except requests.exceptions.ProxyError:
                    pass

                except requests.exceptions.Timeout or \
                       requests.exceptions.ConnectTimeout or \
                       requests.exceptions.ReadTimeout:
                    print("{} 次尝试请求 {} 超时！".format(i, url))

                except requests.exceptions.ConnectionError:
                    print("{} 次尝试请求 {} 连接失败！".format(i, url))

                else:
                    if html.status_code != 200:
                        print("状态码<{}> {}".format(html.status_code, url))
                        return False

                    else:
                        return html

    # 获取音频, 并使用base64转成文本
    def getAudio(self, url, headers):

        for i in range(1, 4):
            headers["User-Agent"] = UserAgent().random
            try:
                mp3 = requests.get(url=url, headers=headers, timeout=10)

            except  requests.exceptions.Timeout or \
                    requests.exceptions.ConnectTimeout or \
                    requests.exceptions.ReadTimeout:
                    print("尝试 {} 次获取音频失败 {}".format(i, url))

            else:
                # 返回编码后的音频
                return base64.urlsafe_b64encode(mp3.content)

        return False

    # 给添加HTML标签
    def addEle(self, str):

        word = self.word["word"]
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

    # 数据汇总
    def printCount(self):

        # 打印结果
        mess = "\n单词:>{}< / 音节:{} / 英标:{} / 美标:{} / 英音:{}个 / 美音:{}个 / 变形:{}个 / 原形:{} / 中释:{}条 / 英释:{}条" \
               "\n中文细释:{}条 / 短语:{}条 / 高频释义:{} / 高频词性:{} / 双语例句:{}条 / 英文例句:{}条 / 近义词:{}个 / 反义词:{}个 / " \
               "词根:{}个"
        m = []
        # 单词
        m.append(self.word["word"])
        # 音节
        if self.word["syll"]:
            m.append("有")
        else:
            m.append("无")
        # 英标
        if self.word["symbolUK"]:
            m.append(self.word["symbolUK"])
        else:
            m.append("无")
        # 美标
        if self.word["symbolUS"]:
            m.append(self.word["symbolUS"])
        else:
            m.append("无")
        # 英音
        m.append(len(self.word["proUK"]))
        # 美英
        m.append(len(self.word["proUS"]))
        # 变形
        m.append(len(self.word["deformedWord"]))
        # 原形
        if self.word["originalWord"]:
            m.append(self.word["originalWord"]["o"])
        else:
            m.append(self.word["word"])
        # 中释
        m.append(len(self.word["paraZh"]))
        # 英释
        m.append(len(self.word["paraEn"]))
        # 中文细释
        m.append(len(self.word["detParaZh"]))
        # 短语
        m.append(len(self.word["phrase"]))
        # 高频释义
        if self.word["highFreProp"]:
            m.append("有")
        else:
            m.append("无")
        # 高频词性
        if self.word["highFrePara"]:
            m.append("有")
        else:
            m.append("无")
        # 双语例句
        m.append(len(self.word["sentDB"]))
        # 英文例句
        m.append(len(self.word["sentEn"]))
        # 近义词
        m.append(len(self.word["synonym"]))
        # 反义词
        m.append(len(self.word["antonym"]))
        # 词根
        m.append(len(self.word["affixes"]))
        print(mess.format(*m), end="\n")


# xiaoD
class XiaoD():

    def __init__(self, base):
        self.base = base
        self.header = {
            "Host": "dict.hjenglish.com",
            "Referer": "https://dict.hjenglish.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0"
        }
        self.url = "https://dict.hjenglish.com/w/{}"
        self.s = requests.session()
        self.html = None
        self.soup = None

    # 获取页面的 HTML, 同时承担单词是否正确的验证
    def getPageHTML(self):

        html = self.base.getHTML(self.s, self.url.format(self.base.word["word"]), self.header, 3)

        if not html: return False

        self.html = html.text
        self.soup = BeautifulSoup(self.html, "lxml")
        return True

    # 获取英式音标
    def getSymbolUK(self):

        if self.base.word["symbolUK"]: return True

        sUK = self.soup.select_one("div.pronounces > span.pronounce-value-en")

        if not sUK: return False

        self.base.word["symbolUK"] = sUK.get_text()[1:-1]
        return True

    # 获取美式音标
    def getSymbolUS(self):

        if self.base.word["symbolUS"]: return True

        sUS = self.soup.select_one("div.pronounces > span.pronounce-value-us")

        if not sUS: return False

        self.base.word["symbolUS"] = sUS.get_text()[1:-1]
        return True

    # 获取中文释义
    def getParaZh(self):

        temp1 = self.soup.select("header > div.simple > p")

        if not temp1: return False

        for i in temp1:
            wProp = i.find("span", class_=False)

            if not wProp:
                wProp = "empty"
            else:
                wProp = wProp.get_text(strip=True).replace(".", "")

            wPara = i.select_one("span.simple-definition").get_text(strip=True)
            self.base.word["paraZh"][wProp] = wPara

        return True

    # 获取中文详细释义（例句 + 用法）
    def getDetParaZh(self):
        # 获取所有词性的详细释义
        temp1 = self.soup.select("div.word-details-item.detail > div > section > dl")

        if not temp1: return False

        # 对单条词性详细进行分解
        for i in temp1:
            wProp = list(i.find("dt").stripped_strings)[0].replace(".", "")

            self.base.word["detParaZh"][wProp] = {}
            # 对词性的不同释义分解
            for ddEle in i.find_all("dd"):
                wPara = ddEle.select_one("p").get_text().replace("\n","").replace("\r","").replace("  ","")
                self.base.word["detParaZh"][wProp][wPara] = []
                # 对不同释义下的例句分解
                for phrase in ddEle.select("ul > li"):
                    pEn, pZh = list(phrase.stripped_strings)
                    pEn = self.base.addEle(pEn)
                    self.base.word["detParaZh"][wProp][wPara].append([pEn, pZh])

        return True

    # 获取英式发音
    def getProUK(self):
        headers = {
            "Host":"n1audio.hjfile.cn"
        }
        audios = self.soup.select("div.pronounces > span.word-audio")

        if not audios: return False

        if "https://n1audio.hjfile.cn" in audios[0].attrs["data-src"]:
            url = audios[0].attrs["data-src"]
            self.base.word["proUK"].append(self.base.getAudio(url, headers))

        return True

    # 获取美式发音
    def getProUS(self):
        headers = {
            "Host": "n1audio.hjfile.cn"
        }
        audios = self.soup.select("div.pronounces > span.word-audio")

        if not audios: return False

        if (len(audios) == 2) and ("https://n1audio.hjfile.cn" in audios[1].attrs["data-src"]):
            url = audios[1].attrs["data-src"]
            self.base.word["proUS"].append(self.base.getAudio(url, headers))

        return True

    # 获取短语
    def getPhrase(self):
        ol = self.soup.select("ol.phrase-items > li")

        for li in ol:
            phrase = list(li.stripped_strings)
            self.base.word["phrase"].append(phrase)

        return True

    # 判断单词是否为原形
    def judgementWord(self):

        if self.base.word["originalWord"]: return True

        redi_1 = self.soup.select_one("div.word-info p.redirection")
        redi_2 = self.soup.select_one("header > div.simple")

        if not (redi_1 or redi_2): return False

        if redi_1:
            defInfo = re.findall("是\[(\w+)\]的(\w+)", redi_1.get_text(strip=True))
        else:
            defInfo = re.findall("（(\w+)的(\w+)）", redi_2.get_text(strip=True))

        if not defInfo: return False

        self.base.word["originalWord"]["o"] = defInfo[0][0].replace("形式", "")
        self.base.word["originalWord"]["p"] = defInfo[0][1].replace("形式", "")

        return True


# 必应词典
class BingDict():

    def __init__(self, base):
        self.base = base
        self.header = {
            "Host": "cn.bing.com",
            "Referer": "http://cn.bing.com/dict/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0"
        }
        self.url = "http://cn.bing.com/dict/search?q={}"
        self.s = requests.session()
        self.html = None
        self.soup = None

    # 获取页面的 HTML
    def getPageHTML(self):

        html = self.base.getHTML(self.s, self.url.format(self.base.word["word"]), self.header, 3)

        if not html: return False

        self.html = html.text
        self.soup = BeautifulSoup(self.html, "lxml")

        return True

    # 判断单词是否为原形
    def judgementWord(self):

        if self.base.word["originalWord"]: return True

        tip = self.soup.find("div", class_="in_tip")

        if not tip: return False

        defInfo = re.findall("\w+是(\w+)的(\S+)", tip.get_text())

        if not defInfo: return False

        self.base.word["originalWord"]["o"] = defInfo[0][0]
        self.base.word["originalWord"]["p"] = defInfo[0][1]

        return True

    # 获取双语例句
    def getSentDB(self):
        word = self.base.word["word"]
        url = "https://cn.bing.com/dict/service?q={}+src:web&offset={}&dtype=sen"

        # 翻页
        for i in range(0,30, 10):
            html = self.base.getHTML(self.s, url.format(word, i), self.header, 3)

            if not html: continue

            soup = BeautifulSoup(html.text, "lxml")

            pharses = soup.select("div.se_li > div.se_li1")

            # 对每一页的例句分解
            for pharse in pharses:
                sEn = pharse.select_one("div.sen_en")
                sZh = pharse.select_one("div.sen_cn")
                if not (sEn and sZh): continue

                sEn = self.base.addEle(sEn.get_text())
                self.base.word["sentDB"].append([sEn, sZh.get_text()])

        return True


# 金山词霸
class Iciba():

    def __init__(self, base):
        self.base = base
        self.url = "http://www.iciba.com/index.php?a=getWordMean&c=search&list=1,2,3,4,5,8,9,10,12,13,14,15,18,21,22,24," \
              "3003,3004,3005&word={}"
        self.headers = {
            "Host": "www.iciba.com",
            "Referer": "http://www.iciba.com/",
            "User-Agent": None
        }
        self.s = requests.session()
        self.json = None

    # 获取json数据
    def getJson(self):
        j = self.base.getHTML(self.s, self.url.format(self.base.word["word"]), self.headers, 3)

        if not j: return False
        deJson = j.json()

        if deJson["errno"] == 404: return False

        self.json = deJson
        return True

    # 获取英式音标
    def getSymbolUK(self):
        try:
            uk = self.json["baesInfo"]["symbols"][0]["ph_en"]
            self.base.word["symbolUK"] = uk
        except KeyError:
            return False

    # 获取英式音标
    def getSymbolUS(self):
        try:
            us = self.json["baesInfo"]["symbols"][0]["ph_am"]
            self.base.word["symbolUS"] = us
        except KeyError:
            return False

    # 获取英式发音
    def getProUK(self):
        headers = {"Host":"res.iciba.com"}
        try:
            url = self.json["baesInfo"]["symbols"][0]["ph_en_mp3"]
            print(url)
            if "?" in url:
                url = url[:url.index("?")]
            self.base.word["proUK"].append(self.base.getAudio(url, headers))

        except KeyError:
            return False

    # 获取美式发音
    def getProUS(self):
        headers = {"Host": "res.iciba.com"}
        try:
            url = self.json["baesInfo"]["symbols"][0]["ph_am_mp3"]
            print(url)
            if "?" in url:
                url = url[:url.index("?")]
            self.base.word["proUS"].append(self.base.getAudio(url, headers))

        except KeyError:
            return False

    # 获取双语例句
    def getSentDB(self):
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
            en = self.base.addEle(sent[0])
            cn = sent[1]
            self.base.word["sentDB"].append([en, cn])

    # 获取英文释义
    def getParaEn(self):
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
                if posp not in self.base.word["paraEn"]:
                    self.base.word["paraEn"][posp] = []

                entryDict["tran"] = entry["tran"]
                entryDict["def"] = entry["def"]
                entryDict["example"] = []
                for e in entry["example"]:
                    en = self.base.addEle(e["ex"])
                    cn = e["tran"]
                    entryDict["example"].append([en, cn])

                self.base.word["paraEn"][posp].append(entryDict)
        except KeyError: pass
        except IndexError: pass

    # 获取词根
    def getaAffixes(self):

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

            self.base.word["affixes"].append(temp)


# 海词
class HaiCi():

    def __init__(self, base):
        self.base = base
        self.header = {
            "Host": "www.dict.cn",
            "Referer": "http://www.dict.cn/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0"
        }
        self.url = "http://www.dict.cn/{}"
        self.s = requests.session()
        self.html = None
        self.soup = None

    # 获取页面
    def getPageHTML(self):
        html = self.base.getHTML(self.s, self.url.format(self.base.word["word"]), self.header, 3)

        if not html: return False

        self.html = html.text
        self.soup = BeautifulSoup(self.html, "lxml")

        return True

    # 获取英式发音
    def getProUK(self):
        headers = {
            "Host": "audio.dict.cn"
        }
        proUK = self.soup.select("div.phonetic > span:nth-of-type(1) > i")

        if not proUK: return False

        for i in proUK:
            url = "http://audio.dict.cn/" + i.attrs["naudio"]
            self.base.word["proUK"].append(self.base.getAudio(url, headers))

        return True

    # 获取美式发音
    def getProUS(self):
        headers = {
            "Host": "audio.dict.cn"
        }
        proUS = self.soup.select("div.phonetic > span:nth-of-type(2) > i")

        if not proUS: return False

        for i in proUS:
            url = "http://audio.dict.cn/" + i.attrs["naudio"]
            self.base.word["proUS"].append(self.base.getAudio(url, headers))

        return True

    # 获取音节
    def getStyll(self):

        if self.base.word["syll"]: return True

        temp1 = self.soup.select_one("#content > div.main > div.word > div.word-cont > h1")

        if not(temp1 and "tip" in temp1.attrs): return False

        syll = temp1.attrs["tip"][5:]

        if self.base.word["word"] == syll.replace("·",""):
            self.base.word["syll"] = syll.split("·")
            return True

        return False

    # 获取变形
    def getWordChange(self):
        temp1 = self.soup.select("div.shape > label")
        temp2 = self.soup.select("div.shape > a")

        if not (temp1 and temp2):
            return False

        for i in zip(temp1, temp2):
            forms = i[0].get_text()[:-1]
            word = i[1].get_text(strip=True)
            self.base.word["deformedWord"][forms] = word

        return True

    # 获取高频释义
    def getHighFrePara(self):
        temp1 = self.soup.select_one("div#dict-chart-basic")

        if not temp1:
            return False

        temp2 = parse.unquote(temp1.attrs["data"])
        highFrePara = json.loads(temp2)
        self.base.word["highFrePara"] = highFrePara

        return True

    # 获取高频词性
    def getHighFreProp(self):
        temp1 = self.soup.select_one("div#dict-chart-examples")

        if not temp1:
            self.highFreProp = False
            return False

        temp2 = parse.unquote(temp1.attrs["data"])
        highFreProp = json.loads(temp2)
        self.base.word["highFreProp"] = highFreProp

        return True

    # 获取近义词
    def getSynonym(self):
        temp1 = self.soup.select("#content > div.main > div.section.rel > div.layout.nfo > ul:nth-of-type(1) > li > a")

        if not temp1: return False

        for t in temp1:
            temp2 = t.get_text().strip()
            if not (" " in temp2) or ("-" in temp2):
                self.base.word["synonym"].append(temp2)

        return True

    # 获取反义词
    def getAntonym(self):
        temp1 = self.soup.select("#content > div.main > div.section.rel > div.layout.nfo > ul:nth-of-type(2) > li > a")

        if not temp1: return False

        for t in temp1:
            temp2 = t.get_text().strip()
            if not (" " in temp2) or ("-" in temp2):
                self.base.word["antonym"].append(temp2)

        return True


# 有道词典
class Youdao():

    def __init__(self, base):
        self.base = base

        self.header = {
            "Host": "dict.youdao.com",
            "Referer": "http://dict.youdao.com",
            "User-Agent": ""
        }
        self.url = "http://dict.youdao.com/w/eng/{}/#keyfrom=dict2.index"
        self.s = requests.session()
        self.html = None
        self.soup = None

    # 获取页面
    def getPageHTML(self):

        self.header["User-Agent"] = UserAgent().random
        html = self.base.getHTML(self.s, self.url.format(self.base.word["word"]), self.header, 3)

        if not html: return False

        self.html = html.text
        self.soup = BeautifulSoup(self.html, "lxml")

        return True

    # 获取词组
    def getPhrase(self):
        pList = self.soup.select("#wordGroup2 > p")

        if not pList: return False

        for item in pList:
            phrase = list(item.stripped_strings)

            self.base.word["phrase"].append([phrase[0].replace("\t","").replace("\n","").replace("\r",""),
                                     phrase[1].replace("\t","").replace("\n","").replace("\r","")])

        return True

    # 获取英文例句
    def getSentEn(self):
        word = self.base.word["word"]
        url = "http://dict.youdao.com/example/auth/{}".format(word)

        html = self.base.getHTML(self.s, url, self.header, 3)

        if not html: return False

        soup = BeautifulSoup(html.text, "lxml")
        sentLi = soup.select("ul.ol > li")

        for sent in sentLi:
            sEn = self.base.addEle(sent.select_one("p:nth-of-type(1)").get_text()).strip()
            self.base.word["sentEn"].append(sEn)

        return True


# 句酷
class Jukuu():

    def __init__(self, base):
        self.base = base
        self.header = {
            "Host": "www.jukuu.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0"
        }
        self.url = "http://www.jukuu.com/show-{}-{}.html"
        self.s = requests.session()


    # 获取双语例句
    def getSentDB(self):

        count = 0
        page = 0
        while True:
            url = self.url.format(self.base.word["word"], page)
            html = self.base.getHTML(self.s, url, self.header, 5)

            if not html: break

            soup = BeautifulSoup(html.text, "lxml")

            es = soup.select("table > tr.e > td:nth-of-type(2)")
            cs = soup.select("table > tr.c > td:nth-of-type(2)")
            ss = soup.find_all("td", width="75%")

            if not (es and cs): break

            for i in zip(es, cs, ss):
                # 过滤
                if "设计"  in i[2].get_text(): continue

                e = self.base.addEle(i[0].get_text().strip())
                c = i[1].get_text().strip()
                self.base.word["sentDB"].append([e, c])
                count += 1

            # 当翻页大于10次或例句大于30条使结束跳出循环
            if (page > 10) or (count > 30):
                count = 0
                break

            page += 1


# freeDictionary
class FreeDict():

    def __init__(self, base):
        self.base = base
        self.header = {
            "Host": "www.thefreedictionary.com",
            "Referer": "http://www.thefreedictionary.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0"
        }
        self.url = "http://www.thefreedictionary.com/{}"
        self.s = requests.session()
        self.html = None
        self.soup = None

    # 获取页面
    def getPageHTML(self):

        html = self.base.getHTML(self.s, self.url.format(self.base.word["word"]), self.header, 7)

        if not html: return False

        self.html = html.text
        self.soup = BeautifulSoup(self.html, "lxml")

        return True

    # 获取英式发音
    def getProUK(self):
        headers = {
            "Host":"img2.tfd.com"
        }
        url = "http://img2.tfd.com/pron/mp3/{}.mp3"

        r = re.findall('<span class=snd2 data-snd="([\da-z/]+/UK/[\da-z/]+)"></span>', self.html)

        if not r: return False

        self.base.word["proUK"].append(self.base.getAudio(url.format(r[0]), headers))

        return True

    # 获取美式发音
    def getProUS(self):
        headers = {
            "Host": "img2.tfd.com"
        }
        url = "http://img2.tfd.com/pron/mp3/{}.mp3"

        r = re.findall('<span class="snd2" data-snd="([\da-z/]+/US/[\da-z/]+)">', self.html)

        if not r: return False

        self.base.word["proUS"].append(self.base.getAudio(url.format(r[0]), headers))

        return True

    # 获取音节
    def getSyll(self):

        if self.base.word["syll"]: return True

        temp1 = self.soup.select_one("#Definition > section:nth-of-type(1) > h2")
        temp2 = self.soup.select("div.pseg > b")

        if not (temp1 or temp2): return False

        if not temp1: return False

        temp2.append(temp1)

        for i in temp2:
            i = i.get_text(strip=True).replace("1","")

            if self.base.word["word"] == i.replace("·",""):
                self.base.word["syll"] = i.split("·")

        return True


# Oxford
class Oxford():

    def __init__(self, base):
        self.base = base
        self.header = {
            "Host": "www.oxfordlearnersdictionaries.com",
            "Referer": "https://www.oxfordlearnersdictionaries.com",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0"
        }
        self.urls = ["https://www.oxfordlearnersdictionaries.com/definition/english/{}",
                    "https://www.oxfordlearnersdictionaries.com/definition/english/{}_1"]
        self.s = requests.session()
        self.html = None
        self.soup = None

    # 获取页面
    def getPageHTML(self):

        for url in self.urls:
            html = self.base.getHTML(self.s, url.format(self.base.word["word"]), self.header, 5)
            if html:
                break
        else:
            return False

        self.html = html.text
        self.soup = BeautifulSoup(self.html, "lxml")

        return True

    # 获取英式发音
    def getProUK(self):
        headers = {
            "Host":"www.oxfordlearnersdictionaries.com"
        }
        temp1 = self.soup.select_one("div.pron-uk")
        if not temp1: return False

        url = temp1.attrs["data-src-mp3"]
        self.base.word["proUK"].append(self.base.getAudio(url, headers))

        return True

    # 获取美式发音
    def getProUS(self):
        headers = {
            "Host": "www.oxfordlearnersdictionaries.com"
        }
        temp1 = self.soup.select_one("div.pron-us")

        if not temp1: return False
        url = temp1.attrs["data-src-mp3"]
        self.base.word["proUS"].append(self.base.getAudio(url, headers))

        return True


# Collins
class Collins():

    def __init__(self, base):
        self.base = base
        self.header = {
            "Host": "www.collinsdictionary.com",
            "Referer": "https://www.collinsdictionary.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0"
        }
        self.url = "https://www.collinsdictionary.com/zh/dictionary/english/{}"
        self.s = requests.session()
        self.html = None
        self.soup = None

    # 获取页面
    def getPageHTML(self):

        html = self.base.getHTML(self.s, self.url.format(self.base.word["word"]), self.header, 5)

        if not html: return False

        self.html = html.text
        self.soup = BeautifulSoup(self.html, "lxml")

        return True

    # 获取英式发音
    def getProUK(self):
        headers = {
            "Host": "www.collinsdictionary.com"
        }
        ukBox = self.soup.select_one("div.Collins_Eng_Dict")

        if not ukBox: return False

        audios = ukBox.find_all("a", class_="audio_play_button")

        if audios and ("data-src-mp3" in audios[0].attrs):
            url = audios[0].attrs["data-src-mp3"]
            self.base.word["proUK"].append(self.base.getAudio(url, headers))

    # 获取美式发音
    def getProUS(self):
        headers = {
            "Host": "www.collinsdictionary.com"
        }
        usBox = self.soup.select_one("div.Large_US_Webster")

        if not usBox: return False

        audios = usBox.find_all("a", class_="audio_play_button")

        if audios and ("data-src-mp3" in audios[0].attrs):
            url = audios[0].attrs["data-src-mp3"]
            self.base.word["proUS"].append(self.base.getAudio(url, headers))


# MongoDB
class MongoDB():

    def __init__(self):
        self.client = MongoClient("127.0.0.1", 27017)
        self.db = self.client["word"]
        self.word_info = self.db.word_info

    # 添加数据
    def add_one(self, d):
        try:
            self.word_info.insert_one(d)
        except:
            print("{} 保存失败!".format(d["word"]))

    def sureBe(self, word):
        rest = self.word_info.find_one({"word": word}, {"word": True})

        if rest:
            return True
        else:
            return False


# 控制器
class Control():

    def __init__(self):

        # 存放单词的列表
        self.wordList = set()
        # 从文件读取单词
        self.readFile()
        # 记录单词剩余数量
        self.wordReQty = len(self.wordList)
        # 声明词典对象
        self.base = Base()
        self.xiaoD = XiaoD(self.base)
        self.bingDict = BingDict(self.base)
        self.iciBa = Iciba(self.base)
        self.haiCi = HaiCi(self.base)
        self.youDao = Youdao(self.base)
        self.jukuu = Jukuu(self.base)
        self.freeDict = FreeDict(self.base)
        self.oxford = Oxford(self.base)
        self.collins = Collins(self.base)

    # 开始抓取
    def start(self):

        timeFlag = 1
        nextWordList = set()

        for word in self.wordList:

            # 先确认数据库中没有待抓取的单词
            if self.base.mdb.sureBe(word):
                print("{} 已收录, 跳过~".format(word))
                continue
            else:
                # 再执行所有词典对象，抓取数据
                if not self.threadRun(word): continue

            # 把查到的单词原形加入到wordlist
            if self.base.word["originalWord"]:
                self.wordReQty += 1
                nextWordList.add(self.base.word["originalWord"]["o"])

            # 单个单词的数据汇总
            self.base.printCount()
            self.wordReQty -= 1
            print("剩余单词：{}个".format(self.wordReQty))

            # 把数据保存到数据库
            self.base.mdb.add_one(self.base.word)

            # 抓取完一个单词后初始化属性
            self.base.__init__()

            # 到达指定次数后重置Cookis
            if timeFlag == 30:
                timeFlag = 1
                self.xiaoD.s.cookies.clear()
                self.bingDict.s.cookies.clear()
                self.iciBa.s.cookies.clear()
                self.haiCi.s.cookies.clear()
                self.youDao.s.cookies.clear()
                self.freeDict.s.cookies.clear()
                self.oxford.s.cookies.clear()
                self.collins.s.cookies.clear()
                self.jukuu.s.cookies.clear()
            else:
                timeFlag += 1

        # 检测 nextWordList 里是否有单词
        if nextWordList:
            # 如果有单词，开始递归
            self.wordList = nextWordList
            self.start()
        else:
            # 否则返回 False
            return False

    # 执行字典对象
    def threadRun(self, word):
        self.base.word["word"] = word

        if not self.xiaoD.getPageHTML():
            return False

        def tRun(strFun):
            fun = eval(strFun)

            if strFun == "self.xiaoD":
                # 小D词典
                fun.getSymbolUK(), fun.getSymbolUS(), fun.getParaZh(), fun.getDetParaZh()
                fun.getProUK(), fun.getProUS(), fun.getPhrase(), fun.judgementWord()
                return True

            elif strFun == "self.bingDict":
                # 必应词典
                if not fun.getPageHTML():
                    return False
                else:
                    fun.getSentDB(), fun.judgementWord()
                    return True

            elif strFun == "self.iciBa":
                # 金山词霸
                if not fun.getJson():
                    return False
                else:
                    fun.getSymbolUK(), fun.getSymbolUS(), fun.getProUK(), fun.getProUS(), fun.getSentDB()
                    fun.getParaEn(), fun.getaAffixes()
                    return True

            elif strFun == "self.haiCi":
                # 海词
                if not fun.getPageHTML():
                    return False
                else:
                    fun.getProUK(), fun.getProUS(), fun.getStyll(), fun.getWordChange()
                    fun.getHighFrePara(), fun.getHighFreProp(), fun.getSynonym(), fun.getAntonym()
                    return True

            elif strFun == "self.youDao":
                # 有道
                if not fun.getPageHTML():
                    return False
                else:
                    fun.getPhrase()
                    return True

            elif strFun == "self.jukuu":
                # 句酷
                fun.getSentDB()
                return True

            elif strFun == "self.freeDict":
                # freeDict
                if not fun.getPageHTML():
                    return False
                else:
                    fun.getProUK(), fun.getProUS(), fun.getSyll()

            elif strFun == "self.oxford":
                # Oxford
                if not fun.getPageHTML():
                    return False
                else:
                    self.oxford.getProUK(), self.oxford.getProUS()
                    return True

            elif strFun == "self.collins":
                # Oxford
                if not fun.getPageHTML():
                    return False
                else:
                    fun.getProUK(), fun.getProUS()
                return True

        arrFun = [
            "self.xiaoD",
            "self.bingDict",
            "self.iciBa",
            "self.haiCi",
            "self.youDao",
            "self.jukuu",
            "self.freeDict",
            "self.oxford",
            "self.collins"
        ]

        # 多线程池
        arrThread = []

        # 开始执行多线程
        for f in range(len(arrFun)):
            arrThread.append(threading.Thread(target=tRun, args=(arrFun[f],)))
            arrThread[f].start()

        # 等待多线程
        for f in arrThread:
            f.join()

        return True

    # 从文件读取单词
    def readFile(self):

        # self.wordList = set(["revokable"])

        for path in os.listdir("./"):

            if ".txt" not in path: continue

            with open(path, "r", encoding="utf-8") as file:

                for word in file:
                    word = word.replace("\n", "")
                    if not word: continue
                    self.wordList.add(word)


def Test():
    base = Base()
    iciba = Iciba(base)
    for w in ["suppress"]:
        base.word["word"] = w
        iciba.getJson()
        iciba.getaAffixes()


if __name__ == '__main__':
    ctrl = Control()
    ctrl.start()
    # Test()


