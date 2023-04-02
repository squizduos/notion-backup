FROM python:3.8-alpine3.12

WORKDIR /app

COPY notion_backup.py /app/notion_backup.py
COPY entrypoint.sh /app/entrypoint.sh

# 修复执行sh权限报错的问题
RUN chmod +x /app/entrypoint.sh  

RUN apk --no-cache add ca-certificates git rsync
RUN pip install requests
ENTRYPOINT ["/app/entrypoint.sh"]
