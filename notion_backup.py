import shutil
import time
import json
import zipfile
import requests
import argparse
import re
import datetime
import os
import traceback
import logging
from urllib.parse import urlparse


import environ

# REMOVE_FILES_ID = True
# NOTION_TIMEZONE = 'Europe/Moscow'
# NOTION_LOCALE = 'en'
# NOTION_API = 'https://www.notion.so/api/v3'
# NOTION_EXPORT_TYPE = os.getenv('NOTION_EXPORT_TYPE', 'markdown')  # html pdf

@environ.config
class AppConfig:
    debug = environ.bool_var(help="Debug mode", default=False)
    remove_files_id = environ.bool_var(help="Remove files ID's", default=True)
    timezone = environ.var(help="Timezone", default="Europe/Moscow")
    locale = environ.var(help="Locale", default="en")
    api_endpoint = environ.var(help="Notion API endpoint", default="https://www.notion.so/api/v3")
    export_type = environ.var(help="Notion export type, defaults to export to Markdown. Replacing links does not support any other types of export", default="markdown")

app_config = environ.to_config(AppConfig)

logging.basicConfig(
    level=logging.DEBUG,  # Set the minimum logging level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log message format
    datefmt='%Y-%m-%d %H:%M:%S',  # Date format
    handlers=[
        logging.StreamHandler()          # Also log to the console
    ]
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if app_config.debug else logging.INFO)


def unzip(filename: str, saveDir: str = ''):
    try:
        file = zipfile.ZipFile(filename)
        dirname = filename.replace('.zip', '')
        if saveDir != '':
            dirname = saveDir
        # If a folder with the same name as the package exists, prompt for a message and skip it.
        if os.path.exists(dirname):
            logger.info(f'{dirname} folder exists')
        else:
            # Creating folder and unzipping it
            os.mkdir(dirname)
        file.extractall(dirname)
        file.close()
        return dirname
    except Exception as e:
        logger.error(f'{filename} unzip fail,{str(e)}')


def zip_dir(dirpath, outFullName):
    """
        Compress the specified folder
        :param dirpath: Destination folder path
        :param outFullName: path_to_zip_file+xxxx.zip
        :return: None
    """
    logger.debug(f"Zipping data to file {outFullName}")
    zip_file = zipfile.ZipFile(os.path.join(dirpath, outFullName), "w", zipfile.ZIP_DEFLATED)
    for path, dirnames, filenames in os.walk(dirpath):
        if path != os.path.join(dirpath, outFullName):
            fpath = path.replace(dirpath, '')
            for filename in filenames:
                if filename != outFullName:
                    zip_file.write(os.path.join(path, filename), os.path.join(fpath, filename))
    zip_file.close()


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
                    'exportType': app_config.export_type,
                    'timeZone': app_config.timezone,
                    'locale': app_config.locale,
                    'flattenExportFiletree': False
                }
            }
        }
    }


def exportSpace(space_id):
    return {
        'task': {
            'eventName': 'exportSpace',
            'request': {
                'spaceId': space_id,
                'exportOptions': {
                    'exportType': app_config.export_type,
                    'timeZone': app_config.timezone,
                    'locale': app_config.locale,
                    "collectionViewExportType": "all",
                    'flattenExportFiletree': False
                }
            }
        }
    }


def request_post(endpoint: str, params: object):
    logger.info('reqeust:{} {}'.format(endpoint, params))
    response = requests.post(
        f'{app_config.api_endpoint}/{endpoint}',
        data=json.dumps(params).encode('utf8'),
        headers={
            'content-type': 'application/json',
            'cookie': 'token_v2='+config.token+'; '
        },
    )
    logger.debug("JSON output")
    logger.debug(response.json())
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



def replace_markdown_links(directory, old_filename, new_filename):
    # Regular expression pattern to find Markdown links
    markdown_link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

    for root, _, files in os.walk(directory):
        for file in files:
            if not any(file.endswith(extension) for extension in [".md", ".csv"]):
                continue
            
            file_path = os.path.join(root, file)
            
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Function to replace the target link
            def replace_link(match):
                link_text = match.group(1)
                link_target = match.group(2)
                if old_filename in link_target:
                    # Replace only the part of the link that matches old_filename with new_filename
                    new_target = link_target.replace(old_filename, new_filename)
                    return f"[{link_text}]({new_target})"
                return match.group(0)

            # Replace the Markdown links
            new_content = markdown_link_pattern.sub(replace_link, content)

            # Write back the modified content if changes were made
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated links in: {file_path}")


def remove_files_id(output_path):
    if not app_config.remove_files_id:
        return
    for root, dirs, files in os.walk(output_path):
        for file in files:
            path = os.path.join(root, file)
            filename_id = re.compile(r'[a-fA-F\d]{32}').findall(file)
            if filename_id:
                new_filename = file.replace(' ' + filename_id[0], '')
                new_path = os.path.join(root, new_filename)
                replace_markdown_links(root, file, new_filename)
                try:
                    os.rename(path, new_path)
                except FileExistsError:
                    os.remove(path)
    # while True:
    #     rename_dir_flag = False
    #     for root, dirs, files in os.walk(output_path):
    #         for dir_name in dirs:
    #             path = os.path.join(root, dir_name)
    #             dir_id = re.compile(
    #                 r'[a-fA-F\d]{8}-[a-fA-F\d]{4}-[a-fA-F\d]{4}-[a-fA-F\d]{4}-[a-fA-F\d]{12}').findall(dir_name)
    #             if dir_id:
    #                 new_dirname = dir_name.replace('-' + dir_id[0], '')
    #                 new_path = os.path.join(root, new_dirname)
    #                 try:
    #                     os.rename(path, new_path)
    #                 except FileExistsError:
    #                     logger.debug(f"Renaming {path} to {new_path} failed: new path is already exists")
    #                 rename_dir_flag = True
    #                 break
    #     if not rename_dir_flag:
    #         break
    
    for root, dirs, files in os.walk(output_path, topdown=False):
        for f in files:
            f_path = os.path.join(root, f)
            if f_path.endswith("_all.csv"):
                os.remove(f_path)
            else:
                try:
                    subtitute_f_path = re.sub(r'( \w{32,32}\b)', '', os.path.abspath(f_path))
                    os.renames(f_path, subtitute_f_path)
                except FileExistsError:
                    logger.debug(f"Renaming {f_path} to {subtitute_f_path} failed: new path is already exists")

def downloadAndUnzip(url, config):
    os.makedirs(config.output, exist_ok=True)
    url_filename = os.path.basename(urlparse(url).path)
    savePath = os.path.join(config.output, url_filename)
    logger.debug(savePath)
    headers = {
        'cookie': f'file_token='+config.file_token+';'
    }
    with requests.get(url, headers=headers, stream=True) as r:
        with open(savePath, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
    unzip(savePath, config.output)
    if os.path.exists(savePath):
        logger.info('Save file to following path:' + savePath)
    else:
        raise Exception('Save file to following path:' + savePath + 'failed')

    for f in os.listdir(config.output):
        file_path = os.path.join(config.output, f)
        if '.zip' in file_path:
            unzip(file_path, config.output)
    
    for f in os.listdir(config.output):
        if '.zip' in file_path:
            os.remove(file_path)

    if app_config.remove_files_id:
        remove_files_id(config.output)
    
    zip_dir(config.output, f"release-{datetime.datetime.now().strftime('%Y%m%dT%H%M%SZ')}.zip")


def main(config):
    if config.space:
        taskId = ''
        taskId = request_post('enqueueTask', exportSpace(
            space_id=config.space)).get('taskId')
        url = exportUrl(taskId)
        downloadAndUnzip(url, config)
        
        logger.info(f"Backup {config.space} to local completion {config.output}")
    elif config.page:
        for page_id in config.page.split(','):
            taskId = ''
            taskId = request_post('enqueueTask', exportPage(
                page_id=page_id)).get('taskId')
            url = exportUrl(taskId)
            downloadAndUnzip(url, config.output +'.zip')

            logger.info(f'Backup {page_id} to local completion {config.OUTPUT}')
    else:
        raise Exception("You should provide Page ID's or Space ID.")


def run_retry(config):
    count = 0
    while True:
        try:
            main(config)
            break
        except Exception as e:
            count += 1
            logger.error('Error trying {} times:'.format(count),e)
            logger.debug(traceback.format_exc())
            
        if count > 3:
            logger.error('Error trying {} times: task failed'.format(count))
            break
        time.sleep(15)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-page',help='pageid, the string after the page url. Multiple page_id\'s are separated by commas', default=None)
    parser.add_argument('-space',help='spaceid, the string after the page url', default=None)
    parser.add_argument('-token',help='notion\'s token_v2')
    parser.add_argument('-file_token',help='file_token is required in cookies when downloading the url of the exported file, each generic')
    parser.add_argument('-output',help='output folder')    

    config = parser.parse_args()

    logger.debug(config)
    print(app_config)

    run_retry(config)
