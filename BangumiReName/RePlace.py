import argparse
import json
import os
import platform
import re
import sys
import time
from datetime import datetime
from itertools import product

from loguru import logger

#     应该能解析出大部分的命名规则了
# ''')
from custom_rules import starts_with_rules


def format_path(file_path):
    # 修正路径斜杠
    if system == 'Windows':
        return file_path.replace('//', '/').replace('/', '\\')
    return file_path.replace('\\', '/').replace('//', '/')

def rename(old_path,custom_replace_pair):

    # 完整文件路径
    old_name = os.path.basename(old_path)
    parent_folder_path = os.path.dirname(old_path)

    if custom_replace_pair:
        # 自定义替换关键字
        for replace_old_part, replace_new_part in custom_replace_pair:
            new_name = old_name.replace(replace_old_part, replace_new_part)
            logger.info(f"{new_name}")
            new_path = format_path(parent_folder_path + '/' + new_name)


    try:
        if old_name is not new_name:
            os.rename(old_path, new_path)
    except:
        logger.info(f"{'rename fail: ' + old_name}")
    logger.info(f"{'运行完毕'}")

if __name__ == '__main__':

    target_path = ''


    # pyinstaller打包后, 通过命令行调用, 必须这样才能获取到exe文件路径, 普通的script_path获取的是临时文件路径
    # 拿到这个路径之后才能方便地读取到exe同目录的文件
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(os.path.realpath(sys.executable))
    elif __file__:
        application_path = os.path.dirname(os.path.realpath(__file__))

    # 默认配置
    rename_delay = 0
    rename_overwrite = True

    try:
        ap = argparse.ArgumentParser()
        ap.add_argument('--path', required=True, help='目标路径')
        ap.add_argument('--replace', type=str, nargs='+', action='append',
                        help='自定义替换关键字, 一般是给字幕用, 用法 `--replace chs chi --replace cht chi` 就能把chs和cht替换成chi, 可以写多组关键字',
                        default=[])

        args = vars(ap.parse_args())
        target_path = args['path']
        custom_replace_pair = args['replace']
    except:
        logger.info(f"{'参数有误，示例如下： python3 RePlace.py --path {TVanime_path} --Replace {old_part} {new_part} '}")


    if not target_path:
        # 没有路径参数直接退出
        sys.exit()


    target_path = target_path.replace('\\', '/').replace('//', '/')


    # 输出结果列表
    file_lists = []
    unknown = []

    # 当前系统类型
    system = platform.system()

    if os.path.isdir(target_path):
        logger.info(f"{'文件夹处理'}")


        for SeriesDir in os.listdir(target_path):
            SeriesDir = os.path.join(target_path, SeriesDir)
            if os.path.isdir(SeriesDir):
                for SeasonDir in os.listdir(SeriesDir):
                    SeasonDir = os.path.join(SeriesDir, SeasonDir)
                    if os.path.isdir(SeasonDir):
                        for file in os.listdir(SeasonDir):
                            file_path = os.path.join(SeasonDir, file)
                            if os.path.isfile(file_path):
                                rename(file_path, custom_replace_pair)


