import shutil
import time
import json
import zipfile
import requests
import argparse
import re
import datetime
import os


REMOVE_FILES_ID = False
# 默认配置无需更改
NOTION_TIMEZONE = 'Asia/Shanghai'
NOTION_LOCALE = 'en'
NOTION_API = 'https://www.notion.so/api/v3'
NOTION_EXPORT_TYPE = os.getenv('NOTION_EXPORT_TYPE', 'markdown')  # html pdf

CONFIG = {
    'NOTION_TOKEN': '',
    'OUTPUT': '',
    'NOTION_FILE_TOKEN': '',
    'PAGE_ID': ''
}


def unzip(filename: str, saveDir: str = ''):
    try:
        file = zipfile.ZipFile(filename)
        dirname = filename.replace('.zip', '')
        if saveDir != '':
            dirname = saveDir
        # 如果存在与压缩包同名文件夹 提示信息并跳过
        if os.path.exists(dirname):
            print(f'{dirname} 已存在,将被覆盖')
            shutil.rmtree(dirname)
        # 创建文件夹,并解压
        os.mkdir(dirname)
        file.extractall(dirname)
        file.close()
        return dirname
    except Exception as e:
        print(f'{filename} unzip fail,{str(e)}')


def zip_dir(dirpath, outFullName):
    """
        压缩指定文件夹
        :param dirpath: 目标文件夹路径
        :param outFullName: 压缩文件保存路径+xxxx.zip
        :return: 无
    """
    zip = zipfile.ZipFile(outFullName, "w", zipfile.ZIP_DEFLATED)
    for path, dirnames, filenames in os.walk(dirpath):
        # 去掉目标跟路径，只对目标文件夹下边的文件及文件夹进行压缩
        fpath = path.replace(dirpath, '')
        for filename in filenames:
            zip.write(os.path.join(path, filename),
                      os.path.join(fpath, filename))
    zip.close()


def exportPage(page_id):

    block_id = page_id[:8]+'-'+page_id[8:12]+'-' + \
        page_id[12:16]+'-'+page_id[16:20]+'-'+page_id[20:]
    return {
        'task': {
            'eventName': 'exportBlock',
            'request': {
                'block': {
                    'id': block_id
                },
                'recursive': True,
                'exportOptions': {
                    'exportType': NOTION_EXPORT_TYPE,
                    'timeZone': NOTION_TIMEZONE,
                    'locale': NOTION_LOCALE,
                    'flattenExportFiletree': False
                }
            }
        }
    }


def request_post(endpoint: str, params: object):
    # print('reqeust:{} {}'.format(endpoint, params))
    response = requests.post(
        f'{NOTION_API}/{endpoint}',
        data=json.dumps(params).encode('utf8'),
        headers={
            'content-type': 'application/json',
            'cookie': 'token_v2='+CONFIG['NOTION_TOKEN']+'; '
        },
    )
    # print(response.json())
    return response.json()


def exportUrl(taskId):
    url = False
    print('Polling for export task: {}'.format(taskId))
    while True:
        res = request_post('getTasks', {'taskIds': [taskId]})
        tasks = res.get('results')
        task = next(t for t in tasks if t['id'] == taskId)
        if task['state'] == 'success':
            url = task['status']['exportURL']
            print("download url:" + url)
            break
        elif task['state'] == 'failure':
            print(task['error'])
        else:
            print('{}.'.format(task['state']), end='', flush=True)
            time.sleep(10)
    return url


def remove_files_id():
    OUTPUT = CONFIG['OUTPUT']
    if not REMOVE_FILES_ID:
        return
    for root, dirs, files in os.walk(OUTPUT):
        for file in files:
            path = os.path.join(root, file)
            filename_id = re.compile(r'[a-fA-F\d]{32}').findall(file)
            if filename_id:
                new_filename = file.replace(' ' + filename_id[0], '')
                new_path = os.path.join(root, new_filename)
                os.rename(path, new_path)
    while True:
        rename_dir_flag = False
        for root, dirs, files in os.walk(OUTPUT):
            for dir in dirs:
                path = os.path.join(root, dir)
                dir_id = re.compile(
                    r'[a-fA-F\d]{8}-[a-fA-F\d]{4}-[a-fA-F\d]{4}-[a-fA-F\d]{4}-[a-fA-F\d]{12}').findall(dir)
                if dir_id:
                    new_dirname = dir.replace('-' + dir_id[0], '')
                    new_path = os.path.join(root, new_dirname)
                    os.rename(path, new_path)
                    rename_dir_flag = True
                    break
        if not rename_dir_flag:
            break


def downloadAndUnzip(url, filename):
    OUTPUT = CONFIG['OUTPUT']
    os.makedirs(OUTPUT, exist_ok=True)
    savePath = filename
    headers = {
        'cookie': f'file_token='+CONFIG['NOTION_FILE_TOKEN']+';'
    }
    with requests.get(url, headers=headers, stream=True) as r:
        with open(savePath, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
    unzip(savePath, OUTPUT)
    if os.path.exists(savePath):
        print('保存文件:' + savePath)
    else:
        print('保存文件:' + savePath + '失败')

    # OUTPUT = savePath.replace(".zip", "")
    for file in os.listdir(OUTPUT):
        file_path = os.path.join(OUTPUT, file)
        if '.zip' in file_path:
            unzip(file_path)
            os.remove(file_path)
    if REMOVE_FILES_ID:
        remove_files_id()
        os.remove(savePath)
        zip_dir(OUTPUT, savePath)


def main():

    taskId = ''
    taskId = request_post('enqueueTask', exportPage(
        page_id=CONFIG['PAGE_ID'])).get('taskId')
    url = exportUrl(taskId)
    downloadAndUnzip(url, CONFIG['OUTPUT']+'.zip')

    print('备份到本地完成')


def run_retry():
    count = 0
    while True:
        try:
            main()
            break
        except Exception as e:
            count += 1
            print('尝试{}次出错:'.format(count),e)
            
        if count > 3:
            print('尝试{}次出错:'.format(count),e)
            break
        time.sleep(15)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-page',help='pageid,页面url后面那一串字符串')
    parser.add_argument('-token',help='notion的token_v2')
    parser.add_argument('-file_token',help='下载导出文件的url的时候cookies中需要file_token，每个通用的')
    parser.add_argument('-output',help='输出的文件夹')

    args = parser.parse_args()

    
    CONFIG['PAGE_ID'] = args.page
    CONFIG['NOTION_TOKEN'] = args.token
    CONFIG['NOTION_FILE_TOKEN'] = args.file_token
    CONFIG['OUTPUT'] = args.output
    
    print(CONFIG)
    run_retry()
