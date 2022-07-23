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


def resource_path(relative_path):
    # 兼容pyinstaller的文件资源访问
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)



def fix_ext(ext):
    # 文件扩展名修正
    # 1.统一小写
    # 2.字幕文件 把sc替换成chs, tc替换成cht, jap替换成jpn
    new_ext = ext.lower()

    # 双重生成器
    ori_list = [f'{y}.{x}' for x in COMMON_CAPTION_EXTS for y in ['sc', 'tc', 'jap']]
    new_list = [f'{y}.{x}' for x in COMMON_CAPTION_EXTS for y in ['chs', 'cht', 'jpn']]

    for i, x in enumerate(ori_list):
        if new_ext == x:
            new_ext = new_list[i]
            break

    return new_ext


def get_file_name_ext(file_full_name):
    # 获取文件名和后缀
    file_name = None
    ext = None

    for x in COMPOUND_EXTS:
        if file_full_name.lower().endswith(x):
            ext = x
            file_name = file_full_name[:-(len(x) + 1)]
            break
    if not ext:
        file_name, ext = file_full_name.rsplit('.', 1)

    return file_name, ext


def format_path(file_path):
    # 修正路径斜杠
    if system == 'Windows':
        return file_path.replace('//', '/').replace('/', '\\')
    return file_path.replace('\\', '/').replace('//', '/')


if __name__ == '__main__':

    script_path = os.path.dirname(os.path.realpath(__file__))
    target_path = ''

    # 重命名的文件移动到season目录下
    move_up_to_season_folder = True

    # pyinstaller打包后, 通过命令行调用, 必须这样才能获取到exe文件路径, 普通的script_path获取的是临时文件路径
    # 拿到这个路径之后才能方便地读取到exe同目录的文件
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(os.path.realpath(sys.executable))
    elif __file__:
        application_path = os.path.dirname(os.path.realpath(__file__))

    # if len(sys.argv) < 2:
    #     exit()

    # 默认配置
    rename_delay = 0
    rename_overwrite = True

    # logger.add(os.path.join(application_path, 'app.log'))
    # logger.info(sys.argv)
    # print(sys.argv)

    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        # 旧版的命令解析
        # 简单通过判断是否有 - 来区分新旧参数
        # python EpisodeReName.py {path_name}
        # python EpisodeReName.py {path_name} {delay_time}

        # 读取命令行目标路径
        target_path = sys.argv[1]
        logger.info(f"{'target_path', target_path}")
        if len(sys.argv) > 2:
            # 重命名延迟(秒) 配合qb使用的参数, 默认为0秒
            rename_delay = int(sys.argv[2])
            logger.info(f"{'rename_delay', rename_delay}")
        name_format = 'S{season}E{ep}'
        force_rename = 0
    else:
        # 新的argparse解析
        # python EpisodeReName.py --path E:\test\极端试验样本\S1 --delay 1 --overwrite 1
        # python EpisodeReName.py --path E:\test\极端试验样本\S1 --delay 1 --overwrite 0
        # EpisodeReName.exe --path E:\test\极端试验样本\S1 --delay 1 --overwrite 0

        ap = argparse.ArgumentParser()
        ap.add_argument('--path', required=True, help='目标路径')
        ap.add_argument('--delay', required=False, help='重命名延迟(秒) 配合qb使用的参数, 默认为0秒不等待', type=int, default=0)
        ap.add_argument('--overwrite', required=False, help='强制重命名, 默认为1开启覆盖模式, 0为不覆盖, 遇到同名文件会跳过, 结果输出到error.txt',
                        type=int,
                        default=1)
        ap.add_argument('--name_format', required=False,
                        help='(慎用) 自定义重命名格式, 参数需要加引号 默认为 "S{season}E{ep}" 可以选择性加入 系列名称如 "{series} - S{season}E{ep}" ',
                        default='S{season}E{ep}')
        ap.add_argument('--force_rename', required=False, help='(慎用) 即使已经是标准命名, 也强制重新改名, 默认为0不开启, 1是开启', type=int,
                        default=0)
        ap.add_argument('--replace', type=str, nargs='+', action='append',
                        help='自定义替换关键字, 一般是给字幕用, 用法 `--replace chs chi --replace cht chi` 就能把chs和cht替换成chi, 可以写多组关键字',
                        default=[])

        args = vars(ap.parse_args())
        target_path = args['path']
        rename_delay = args['delay']
        rename_overwrite = args['overwrite']
        name_format = args['name_format']
        force_rename = args['force_rename']
        custom_replace_pair = args['replace']

    if not target_path:
        # 没有路径参数直接退出
        sys.exit()
        # 1 / 0
        # 直接运行的目标路径
        target_path = r'E:\test\极端试验样本'
        target_path = r'E:\test\极端试验样本\S1'

    target_path = target_path.replace('\\', '/').replace('//', '/')

    # 需要重命名的文件后缀
    COMMON_MEDIA_EXTS = [
        'flv',
        'mkv',
        'mp4',
        'avi',
        'rmvb',
        'm2ts',
        'wmv',
    ]

    # 字幕文件
    COMMON_CAPTION_EXTS = [
        'srt',
        'ass',
        'ssa',
        'sub',
        'smi',
    ]

    # 语言文件
    COMMON_LANG = [
        # 特殊命名处理
        'chs&jpn',
        'cht&jpn',
        # 一般命名
        'cn',
        'chs',
        'cht',
        'zh',
        'sc',
        'tc',
        'jp',
        'jap',
        'jpn',
        'en',
        'eng',
    ]

    # 混合后缀
    COMPOUND_EXTS = COMMON_MEDIA_EXTS + ['.'.join(x) for x in
                                         list(product(COMMON_LANG, COMMON_CAPTION_EXTS))] + COMMON_CAPTION_EXTS

    # 输出结果列表
    file_lists = []
    unknown = []

    # 当前系统类型
    system = platform.system()

    if os.path.isdir(target_path):
        logger.info(f"{'文件夹处理'}")


        # 遍历文件夹, 只处理媒体文件
        for root, dirs, files in os.walk(target_path, topdown=False):
            for name in files:

                # 只处理媒体文件
                file_name, ext = get_file_name_ext(name)
                if not ext.lower() in COMPOUND_EXTS:
                    continue

                # 完整文件路径
                file_path = os.path.join(root, name).replace('\\', '/')
                file_path = os.path.abspath(file_path)
                parent_folder_path = os.path.dirname(file_path)

                if custom_replace_pair:
                    # 自定义替换关键字
                    for replace_old_part, replace_new_part in custom_replace_pair:
                        new_name = name.replace(replace_old_part, replace_new_part)
                        logger.info(f"{new_name}")

                        new_path = format_path(parent_folder_path + '/' + new_name)

                        file_lists.append([file_path, new_path])
                    else:
                        logger.info(f"{'未能识别'}")
                        unknown.append(file_path)

            if unknown:
                logger.info(f"{'----- 未识别文件 -----'}")
                for x in unknown:
                    logger.info(f'{x}')

            if rename_delay:
                # 自动运行改名
                logger.info(f"{'重命名延迟等待中...'}")
                # 程序运行太快 会导致重命名失败 估计是文件被锁了 这里故意加个延迟(秒)
                time.sleep(rename_delay)

            logger.info(f"{'file_lists', file_lists}")

            # 错误记录
            error_logs = []

            for old, new in file_lists:

                if not rename_overwrite:
                    # 如果设置不覆盖 遇到已存在的目标文件不强制删除 只记录错误
                    if os.path.exists(new):
                        error_logs.append(
                            f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} 重命名 {old} 失败, 目标文件 {new} 已经存在')
                        continue

                # 默认遇到文件存在则强制删除已存在文件
                try:
                    # 检测文件能否重命名 报错直接忽略
                    tmp_name = new + '.new'
                    os.rename(old, tmp_name)

                    # 目标文件已存在, 先删除
                    if os.path.exists(new):
                        os.remove(new)

                    # 临时文件重命名
                    os.rename(tmp_name, new)
                except:
                    pass

            if error_logs:
                error_file = os.path.join(application_path, 'error.txt')
                logger.warning(f'部分文件重命名失败, 请检查{error_file}')
                if not os.path.exists(error_file):
                    f = open(error_file, 'w', encoding='utf-8')
                    f.write('\n'.join(error_logs))
                else:
                    f = open(error_file, 'a', encoding='utf-8')
                    f.write('\n' + '\n'.join(error_logs))

            logger.info(f"{'运行完毕'}")

