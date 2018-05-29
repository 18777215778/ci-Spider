import requests, threading, lxml, re, random, time
from queue import Queue
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


class Start():
    IPpool = set()

    def __init__(self):
        self.ip66 = IP66()
        self.xicidaili = Xicidaili()
        self.kuadiaili = Kuaidaili()
        self.ip3366 = IP3366()
        self.data5u = Data5u()
        self.xsdaili = Xsdaili()
        self.mimiip = Mimiip()
        self.superfastip = Superfastip()

        self.q = Queue()

    def get(self):
        # IPpool 池中还有 IP 时，不从网页中抓取 IP
        if (not self.IPpool) and self.q.empty():
            if __name__ == '__main__':
                print("从网页上抓取...")
            self.ip66.getIP()
            self.xicidaili.getIP()
            self.kuadiaili.getIP()
            self.ip3366.getIP()
            self.data5u.getIP()
            self.xsdaili.getIP()
            self.mimiip.getIP()
            self.superfastip.getIP()

        # 队列不为空时，直接返回队列里的IP
        if self.q.empty():
            for i in range(16):
                t = threading.Thread(target=self.testIP, args=())
                t.start()

        if __name__ == '__main__':
            print("IP池中IP还有 {} 个，队列中还有 {} 个".format(len(self.IPpool), self.q.qsize()), end="")
        return self.q.get(True)

    def testIP(self):
        url = "https://www.baidu.com"
        headers = {
            "Host": "www.baidu.com",
            "User-Agen": UserAgent().random
        }

        while self.IPpool:
            try:
                IP = self.IPpool.pop()
                proxies = {
                    "http": "{}:{}".format(*IP),
                    "https": "{}:{}".format(*IP)
                }
                requests.head(url, headers=headers, proxies=proxies, timeout=3)
            except:
                pass
            else:
                self.q.put(IP)


# http://www.66ip.cn
class IP66():

    def __init__(self):
        self.url = "http://www.66ip.cn/areaindex_{}/1.html"
        self.headers = {
            "Host": "www.66ip.cn",
            "Referer":"http://www.66ip.cn/areaindex_2/1.html",
            "User-Agent": None
        }
        self.page = 1

    def getIP(self):
        self.headers["User-Agent"] = UserAgent().random
        html = requests.get(self.url.format(self.page), headers = self.headers, allow_redirects=False)

        # 设置页面IP
        if self.page == 33:
            self.page = 1
        else:
            self.page += 1

        if not html: return False

        soup = BeautifulSoup(html.text, "lxml")
        trs = soup.select("#footer > div > table > tr")


        for tr in trs[1:]:
            ip = tr.select_one("td:nth-of-type(1)").get_text().encode('iso-8859-1').decode('gbk')
            prot = tr.select_one("td:nth-of-type(2)").get_text().encode('iso-8859-1').decode('gbk')
            Start.IPpool.add((ip, prot))


# http://www.xicidaili.com
class Xicidaili():

    def __init__(self):
        self.url = "http://www.xicidaili.com/{}/{}"
        self.headers = {
            "Host": "www.xicidaili.com",
            "Referer":"http://www.xicidaili.com",
            "User-Agent": None
        }

        self.page = {"nn":1, "nt":1}

    def getIP(self):
        self.headers["User-Agent"] = UserAgent().random

        # 交叉轮流抓取不同的种类的IP
        if self.page["nn"] <= self.page["nt"]:
            kind = "nn"
        else:
            kind = "nt"

        html = requests.get(self.url.format(kind, self.page[kind]), headers=self.headers, allow_redirects=False)

        # 设置翻页临界值
        if self.page[kind] == 10:
            self.page[kind] = 1
        else:
            self.page[kind] += 1

        if not html: return False

        soup = BeautifulSoup(html.text, "lxml")
        trs = soup.select("#ip_list > tr")

        for tr in trs[1:]:
            ip = tr.select_one("td:nth-of-type(2)").get_text()
            prot = tr.select_one("td:nth-of-type(3)").get_text()
            Start.IPpool.add((ip, prot))


# https://www.kuaidaili.com
class Kuaidaili():

    def __init__(self):
        self.url = "https://www.kuaidaili.com/free/{}/{}"
        self.headers = {
            "Host": "www.kuaidaili.com",
            "Referer":"https://www.kuaidaili.com",
            "User-Agent": None
        }
        self.page = {"inha": 1, "intr": 1}

    def getIP(self):
        self.headers["User-Agent"] = UserAgent().random

        # 交叉轮流抓取不同的种类的IP
        if self.page["inha"] <= self.page["intr"]:
            kind = "inha"
        else:
            kind = "intr"

        html = requests.get(self.url.format(kind, self.page[kind]), headers=self.headers, allow_redirects=False)

        # 设置翻页临界值
        if self.page[kind] == 10:
            self.page[kind] = 1
        else:
            self.page[kind] += 1

        if not html: return False

        soup = BeautifulSoup(html.text, "lxml")
        trs = soup.select("#list > table > tbody > tr")

        for tr in trs:
            ip = tr.select_one("td:nth-of-type(1)").get_text()
            prot = tr.select_one("td:nth-of-type(2)").get_text()
            Start.IPpool.add((ip, prot))


# http://www.ip3366.net
class IP3366():

    def __init__(self):
        self.url = "http://www.ip3366.net/free/"
        self.headers = {
            "Host": "www.ip3366.net",
            "Referer":"http://www.ip3366.net",
            "User-Agent": None
        }

    def getIP(self):
        self.headers["User-Agent"] = UserAgent().random
        html = requests.get(self.url, headers=self.headers, allow_redirects=False)

        if not html: return False

        soup = BeautifulSoup(html.text, "lxml")
        trs = soup.select("#list > table > tbody > tr")

        for tr in trs:
            ip = tr.select_one("td:nth-of-type(1)").get_text()
            prot = tr.select_one("td:nth-of-type(2)").get_text()
            Start.IPpool.add((ip, prot))


# http://www.data5u.com
class Data5u():
    def __init__(self):
        self.url = "http://www.data5u.com/free/{}/index.shtml"
        self.headers = {
            "Host": "www.data5u.com",
            "Referer":"http://www.data5u.com/free/gnpt/index.shtml",
            "User-Agent": None
        }
        self.page = {"gngn": 1, "gnpt": 1}

    def getIP(self):
        self.headers["User-Agent"] = UserAgent().random
        # 交叉轮流抓取不同的种类的IP
        if self.page["gngn"] <= self.page["gnpt"]:
            kind = "gngn"
            self.page["gngn"] = 0
            self.page["gnpt"] = 1
        else:
            kind = "gnpt"
            self.page["gngn"] = 1
            self.page["gnpt"] = 0

        html = requests.get(self.url.format(kind), headers=self.headers, allow_redirects=False)

        if not html: return False

        soup = BeautifulSoup(html.text, "lxml")
        uls = soup.select("div.wlist > ul > li:nth-of-type(2) > ul")

        for ul in uls[1:]:
            ip = ul.select_one("span:nth-of-type(1)").get_text()
            prot = ul.select_one("span:nth-of-type(2)").get_text()
            Start.IPpool.add((ip, prot))


# http://www.xsdaili.com
class Xsdaili():

    def __init__(self):
        self.url = "http://www.xsdaili.com/dayProxy/{}.html"
        self.urls = []
        self.headers = {
            "Host": "www.xsdaili.com",
            "User-Agent": None
        }
        self.getURL()

    def getIP(self):
        self.headers["User-Agent"] = UserAgent().random
        url = self.urls.pop(0)
        self.urls.append(url)
        html = requests.get(url, headers= self.headers, allow_redirects=False)

        if not html: return False

        IP = re.findall("[\d\.]+:\d+", html.text)

        for i in IP:
            ip, prot = i.split(":")
            Start.IPpool.add((ip, prot))

    def getURL(self):
        for i in range(1,11):
            self.headers["User-Agent"] = UserAgent().random
            html = requests.get(self.url.format(i), headers=self.headers, allow_redirects=False)

            if not html: continue

            soup = BeautifulSoup(html.text, "lxml")

            for a in soup.select("div.title > a"):
                self.urls.append("http://www.xsdaili.com" + a.attrs["href"])


# http://www.mimiip.com
class Mimiip():

    def __init__(self):
        self.url = "http://www.mimiip.com/gngao/{}"
        self.headers = {
            "Host":"www.mimiip.com",
            "User-Agent":None
        }
        self.page = 1

    def getIP(self):
        for _ in range(3):
            self.headers["User-Agent"] = UserAgent().random

            html = requests.get(self.url.format(self.page), headers=self.headers, allow_redirects=False)
            if self.page >= 600:
                self.page = 1
            else:
                self.page += 1

            if not html: return False

            soup = BeautifulSoup(html.text, "lxml")
            trs = soup.select("table.list > tr")

            for tr in trs[1:]:
                ip = tr.select_one("td:nth-of-type(1)").get_text()
                prot = tr.select_one("td:nth-of-type(2)").get_text()
                Start.IPpool.add((ip, prot))


# http://www.superfastip.com
class Superfastip():

    def __init__(self):
        self.url = "http://www.superfastip.com/welcome/getips/{}"
        self.headers = {
            "Host":"www.superfastip.com",
            "User-Agent":None
        }
        self.page = 1

    def getIP(self):
        self.headers["User-Agent"] = UserAgent().random
        html = requests.get(self.url.format(self.page), headers=self.headers, allow_redirects=False)
        if self.page == 20:
            self.page = 1
        else:
            self.page += 1

        if not html: return False

        soup = BeautifulSoup(html.text, "lxml")
        trs = soup.select("#iptable11 > tr")

        for tr in trs[1:]:
            ip = tr.select_one("td:nth-of-type(3)").get_text()
            prot = tr.select_one("td:nth-of-type(4)").get_text()
            Start.IPpool.add((ip, prot))


if __name__ == '__main__':
    start = Start()
    for i in range(300):
        print(start.get())
        time.sleep(2)



