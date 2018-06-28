from pymongo import MongoClient
from datetime import datetime

class MongoDB():

    def __init__(self):
        self.client = MongoClient("127.0.0.1", 27017)
        self.db = self.client["ciPanGuan"]
        self.word_data = self.db.word_data

    # 添加数据
    def add_one(self, d):
        d["lastTime"] = datetime.now()
        try:
            self.word_data.insert_one(d)
            return True
        except:
            print("{} 保存失败!".format(d["word"]))
            return False

    # 确定单词是否已收录到数据库
    def sureBe(self, word):
        rest = self.word_data.find_one({"word": word}, {"word": True})

        if rest:
            return True
        else:
            return False

    # 获得单词的变形
    def getDefWord(self, word):
        rest = None
        try:
            rest = self.word_data.find_one({"word":"{}".format(word), "defWord":{"$ne":{}}}, {'_id': False,"defWord":True})
        except:
            pass

        if not rest["defWord"]: return []

        # 过滤掉数据库中已收录的单词
        wls = []
        for word in list(rest["defWord"].values()):
            if not self.sureBe(word):
                wls.append(word)

        return wls

    # 获取单词的原形
    def getOriWord(self, word):
        rest = None
        try:
            rest = self.word_data.find_one({"word": "{}".format(word), "oriWord": {"$ne": {}}}, {'_id': False, "oriWord": True})
        except:
            pass

        # 过滤掉数据库中已收录的单词
        if rest["oriWord"] and (not self.sureBe(rest)):
            return [rest["oriWord"]]
        else:
            return []


if __name__ == '__main__':
    db = MongoDB()
    print(db.getOriWord("looking"))