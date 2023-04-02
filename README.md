
基于 https://github.com/igor-kupczynski/notion-exporter 的workflow进行修改

基于 https://github.com/LoneKingCode/notion-backup 的导出脚本进行修改

# notion-backup

## notion 自动备份脚本
## Automatic Notion workspace backup to git and local

基于`python3`，利用 notion 官方 api，自动导出所有工作空间内数据为 markdown 格式,虽然官方 API 导出的为 zip，但是脚本会解压，然后一起上传至 github，因为在 github，所以也拥有了版本历史功能。



### 使用方法:

```shell
python notion_backup.py -page YOUR_PAGE_ID -token YOUR_NOTION_TOKEN -file_token YOU_NOTION_FILE_TOKEN  -output OUTPUT_DIR_NAME
```

- page :  page id
- token :  cookie里面的token_v2
- file_token : 导出文件的时候，下载zip的请求cookie里面加了个这个参数，不过导出不同文件的file_token都是一样的，随便下载个ZIP拿请求cookie里的下来就好了
- output ： 导出的文件夹名称

## github workflows参考示例：
```yml
name: Export my notion workspace

on:
  schedule:
    - cron: "0 */24 * * *"  # Call the export every 6 hours
  workflow_dispatch: {}

jobs:
  export:
    runs-on: ubuntu-latest
    steps:
      - uses: AsahiMoon/notion-backup@v1.0.0
        with:
          pages: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Pages IDs identified in (step 2)  
          output-dir: notion-backup
          notion-token: ${{ secrets.NOTION_TOKEN }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          notion-file-token: ${{ secrets.NOTION_FILE_TOKEN }}
```
