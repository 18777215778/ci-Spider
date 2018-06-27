from getWordData import start
import threading, queue, time, os, hashlib
from saveToMongoDB import MongoDB
from multiprocessing import Process, Queue, freeze_support, Queue
import multiprocessing


def createAudioPath():
    '''
    用于创建音频存放目录。
    :return: None
    '''
    abs_path = os.path.abspath(".")
    audio_path = os.path.join(abs_path, "wordAudio")

    if not os.path.exists(audio_path):
        os.makedirs(audio_path)


def saveAudioToDisc(mp3):
    '''
    保存单词发音音频到磁盘
    :return:
    '''
    # # 获得音频的MD5摘要
    md5 = hashlib.md5()
    md5.update(mp3)

    file_path = os.path.join("./wordAudio", md5.hexdigest() + ".mp3")

    if not os.path.exists(file_path):
        try:
            with open(file_path, "wb") as f:
                f.write(mp3)
        except:
            # 保存失败
            return False
        else:
            # 保存成功
            return md5.hexdigest()
    else:
        # 文件已存在
        return md5.hexdigest()


def readWordFromfiler():
    '''
    从文件读取单词到队列
    :return: 单词队列
    '''
    word_queue = Queue()
    for path in os.listdir("./"):

        if ".txt" not in path:
            continue

        try:
            with open(path, "r", encoding="utf-8") as file:
                for word in file:
                    word = word.replace("\n", "")
                    if word:
                        word_queue.put(word)
        except UnicodeDecodeError:
            print("文件编码错误")

    return word_queue


def printBearFruit(wd):
        mess = "单词:>\033[32m{}\033[0m< / 音节:{} / 英标:{} / 美标:{} / 英音:{}个 / 美音:{}个 / 变形:{}个 / 原形:{} / 中释:{}条 / 英释:{}条" \
               "\n中文细释:{}条 / 短语:{}条 / 高频释义:{} / 高频词性:{} / 双语例句:{}条 / 英文例句:{}条 / 近义词:{}个 / 反义词:{}个 / " \
               "词根:{}个"
        m = []
        # 单词
        m.append(wd["word"])
        # 音节
        m.append("有") if wd["syll"] else m.append("无")
        # 英标
        m.append(wd["symbolUK"]) if wd["symbolUK"] else m.append("无")
        # 美标
        m.append(wd["symbolUS"]) if wd["symbolUS"] else m.append("无")
        # 英音
        m.append(len(wd["proUK"])) if wd["proUK"] else m.append("0")
        # 美英
        m.append(len(wd["proUS"])) if wd["proUS"] else m.append("0")
        # 变形
        m.append(len(wd["defWord"])) if wd["defWord"] else m.append("0")
        # 原形
        m.append(wd["oriWord"]) if wd["oriWord"] else m.append("无")
        # 中释
        m.append(len(wd["paraZh"])) if wd["paraZh"] else m.append("0")
        # 英释
        m.append(len(wd["paraEn"])) if wd["paraEn"] else m.append("0")
        # 中文细释
        m.append(len(wd["detParaZh"])) if wd["detParaZh"] else m.append("0")
        # 短语
        m.append(len(wd["phrase"])) if wd["phrase"] else m.append("无")
        # 高频释义
        m.append("有") if wd["highFrePara"] else m.append("无")
        # 高频词性
        m.append("有") if wd["highFreProp"] else m.append("无")
        # 双语例句
        m.append(len(wd["sentDB"])) if wd["sentDB"] else m.append("0")
        # 英文例句
        m.append(len(wd["sentEn"])) if wd["sentEn"] else m.append("0")
        # 近义词
        m.append(len(wd["synonym"])) if wd["synonym"] else m.append("0")
        # 反义词
        m.append(len(wd["antonym"])) if wd["antonym"] else m.append("0")
        # 词根
        m.append(len(wd["affixes"])) if wd["affixes"] else m.append("0")
        print(mess.format(*m), end="\n")


def collateData(data):
    keys = []

    if (isinstance(data, list)):
        keys = range(len(data))

    if (isinstance(data, dict)):
        keys = data.keys()

    for i in keys:
        if data[i] == {}:
            data[i] = None
        else:
            data[i] = collateData(data[i])

    if data == "" or data == [] or data == {}:
        data = None

    return data


def dbHandler(wl_queue, wd_queue):
    '''
    :param wd_queue: 单词数据队列
    :return: None
    '''
    db = MongoDB()
    while True:
        try:
            word_data = wd_queue.get(timeout=180)

        except queue.Empty:
            print("\n队列中的所有单词的数据抓取完毕")
            return True

        # 保存不完整的单词数据
        if ("full" in word_data) and (not word_data["full"]):
            db.sureBe(word_data)
            continue

        # 对于没有音节的单词，音节 = 单词
        if not word_data["syll"]:
            word_data["syll"] = word_data["word"]

        # 保存单词单词发音音频
        # for key in ["proUK", "proUS"]:
        #     del_count = 0
        #     audios = word_data[key]
        #     for index, audio in enumerate(audios):
        #         file_name = saveAudioToDisc(audio)
        #         if file_name:
        #             word_data[key][index] = file_name
        #         else:
        #             del word_data[index-del_count]
        #             del_count += 1

        # 获得单词的原形，并添加到队列
        if word_data["oriWord"] and (not db.sureBe(word_data["oriWord"])):
            wl_queue.put(word_data["oriWord"])

        # 获取单词的变形，并添加到队列
        if word_data["defWord"]:
            for w in list(word_data["defWord"].values()):
                if not db.sureBe(w):
                    wl_queue.put(w)

        # 保存到数据库
        if db.add_one(collateData(word_data)):
            # 打印结果
            printBearFruit(word_data)
            print("剩余 {} 个单词".format(wl_queue.qsize()))


def mainContrl():
    '''
    主控制函数
    :return: None
    '''
    wl_queue = readWordFromfiler()
    wd_queue = Queue()
    createAudioPath()

    # 创建并启动 save() 线程
    save_thread = threading.Thread(target=dbHandler, args=(wl_queue, wd_queue,))
    save_thread.start()

    # 创建进程池
    for i in range(3):
        mul = Process(target = start, args = (wl_queue, wd_queue, ))
        mul.daemon = True
        mul.start()

    # 等待
    save_thread.join()


if __name__ == '__main__':
    mainContrl()
    # queue = readWordFromfiler()
    # while not queue.empty():
    #     print(queue.get())
