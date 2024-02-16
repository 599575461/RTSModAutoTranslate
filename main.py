import json
import os
import sys
import re
import argparse
import time

from hashlib import md5

from requests import post
from configparser import RawConfigParser
from random import randint
from typing import  Dict


def stopApp():
    os.system('pause')
    sys.exit(1)


def stdError(msg):
    sys.stderr.write(f"发生错误:{msg}\n")
    stopApp()


class TranslateManager:
    def __init__(self):
        self.appid = args.tranAppId
        self.appkey = args.tranAppKey
        self.headers = {"Content-Type": "application/x-www-form-urlencoded"}
        self.url = "https://fanyi-api.baidu.com/api/trans/vip/translate"

    def translate(self, text: str):
        salt = randint(32768, 65536)
        sign = md5(
            (self.appid + text + str(salt) + self.appkey).encode("utf-8")
        ).hexdigest()
        payload = {
            "appid": self.appid,
            "q": text,
            "from": 'en',
            "to": 'zh',
            "salt": salt,
            "sign": sign,
        }
        try:
            response = post(
                self.url, params=payload, headers=self.headers
            )
        except Exception as e:
            stdError(f"在请求网络时发生错误:{e}")
        else:
            res = response.json()
            if "error_code" in res:
                stdError(res["error_msg"])
            result = "\n".join([s["dst"] for s in res["trans_result"]])
            return result


class RustedWarfareInI:
    def __init__(self):
        self.translateManager: TranslateManager = TranslateManager()

        self.conf = None
        self.jsonPath = args.jsonPath

        # 文件储存地址
        self.jsonFile = os.path.join(args.jsonPath, "translateAndPos.json")
        # 正在处理的文件
        self.file = ""
        # 匹配键的位置
        self.valPos = {}
        # 翻译对照表
        self.translateDict: Dict[str, str] = {}
        # valPos和translateDict的结合
        self.jsonContext = {}

    @staticmethod
    def getInIFiles():
        listInI = []

        for root, dirs, files in os.walk(args.modPath):
            for file in files:
                if file.endswith(".ini"):
                    listInI.append(os.path.join(root, file))

        if not listInI:
            stdError("错误：Mod目录不存在\n将EXE文件放在assets\\builtin_mods \n")

        return listInI

    def build(self) -> None:
        for file in self.getInIFiles():
            self.initConf(file)
            if self.setValPos():
                self.setTranslateDict()
            else:
                continue

            self.convertJsonToInI()
            self.setConTextJson()
        self.writeToJson()

    def initConf(self, file):
        self.conf = RawConfigParser()
        self.conf.optionxform = lambda option: option
        self.file = file

        # 清空以免不同文件冲突
        self.translateDict = {}
        self.valPos = {}

        try:
            self.conf.read(file, encoding="utf-8")
        except Exception as msg:
            stdError(msg)

    def inputTranslate(self, oldEnName: str):
        time.sleep(0.001)
        tranTxt = self.translateManager.translate(oldEnName)
        if args.allTran:
            return tranTxt
        else:
            newEnName = input(f"输入以下字符的翻译\n {oldEnName} \n猜测翻译结果为:{tranTxt}\n")
            return tranTxt if newEnName == "" else newEnName

    def setTranslateDict(self):
        for listVal in self.valPos.values():
            val = listVal[1]
            newName = self.inputTranslate(val)
            self.translateDict[val] = newName

    def convertPosToJson(self, section, key, val):
        if section and key and val:
            self.valPos[section] = [key, val]

    def convertJsonToInI(self):
        """
        在TranslateDict和valPos都设置完成的情况下将他们加载到conf
        :return:
        """
        for key, valList in self.valPos.items():
            cnVal = self.translateDict[valList[1]]
            self.conf[key][valList[0]] = cnVal

        self.writeToInI()

    def readJson(self):
        try:
            with open(self.jsonFile, 'r', encoding='utf-8') as jsonFile:
                tempDict = json.load(jsonFile)

                for file, val in tempDict.items():
                    self.initConf(file)

                    self.valPos = val['pos']
                    self.translateDict = val['translate']

                    self.convertJsonToInI()

        except Exception as msg:
            stdError(msg)

    def writeToInI(self):
        with open(self.file, 'w', encoding='utf-8') as configFile:
            self.conf.write(configFile)
        print(f"成功翻译InI文件: {self.file}")

    def writeToJson(self):
        if not os.path.exists(args.jsonPath):
            os.makedirs(args.jsonPath)

        with open(self.jsonFile, 'w', encoding='utf-8') as jsonFile:
            json.dump(self.jsonContext, jsonFile, ensure_ascii=False, indent=4)

        print(f"成功翻译模组,翻译对照表为: {self.translateDict}")

    def setValPos(self) -> bool:
        """
        获取InI文件夹下Description，text结尾的键值，获取他的val,key,section
        :return: 返回一个数组 0:val 1:key 2:section
        """
        for section in self.conf.sections():
            for key, val in self.conf.items(section):
                if re.search(r".*(text|Description)$", key, re.IGNORECASE):
                    self.convertPosToJson(section, key, val)

        if None in self.valPos:
            return False
        return True

    def setConTextJson(self):
        tempDict = {"translate": self.translateDict, "pos": self.valPos}
        self.jsonContext[self.file] = tempDict


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='铁锈战争MOD翻译器')
    parser.add_argument('-m', "--modPath", type=str, default=".", help="mod文件夹路径,一般文件夹下有mod-info.txt文件")
    parser.add_argument('-k', "--tranAppKey", type=str, default="gN5BDI4o35mJsDMYewWQ",
                        help="百度翻译API Key,不写用作者的")
    parser.add_argument('-i', "--tranAppId", type=str, default="20230821001788876", help="百度翻译API Id,不写用作者的")
    parser.add_argument('-j', "--jsonPath", type=str, default="build",
                        help="软件自己生成的Json文件地址,不写使用build文件夹下的，如果已经存在则读取并配置")
    parser.add_argument('-a', "--allTran", type=bool, default=False,
                        help="全部使用机翻")
    args = parser.parse_args()

    print("正在加载INI配置器...")
    r = RustedWarfareInI()
    print("加载成功,欢迎使用铁锈战争MOD翻译器,作者:QQ599575461\n开始检查Json文件")
    if os.path.isfile(r.jsonFile):
        print(f"在{args.jsonPath}下读取到Json文件")
        r.readJson()
    else:
        print(f"未读取到Json文件,开始配置")
        r.build()

    os.system("pause")
