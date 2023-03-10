import json
import requests
import os
import shutil
import tarfile
import argparse
from datetime import datetime
from requests.exceptions import ConnectionError
import re


def slugify(text):
    # 将所有非字母数字字符替换为 -
    text = re.sub(r'[^a-zA-Z0-9]+', '-', text)
    # 将多个 - 替换为一个 -
    text = re.sub(r'-+', '-', text)
    # 将字符串转换为小写
    text = text.lower()
    # 去除开头和结尾的 -
    text = text.strip('-')
    return text


def main():
    local_path = os.path.join(os.path.expanduser("~/Library/Application Support"), 'Local')
    local_bin_path = '/Applications/Local.app/Contents/Resources/extraResources/bin'

    parser = argparse.ArgumentParser()
    parser.add_argument('--path', type=str, help='The path to the directory that keeps the database backup file.')
    args = parser.parse_args()

    if args.path is None:
        backup_path = os.path.join(os.path.expanduser("~/Documents/LocalDBBackup"))
    else:
        backup_path = os.path.expanduser(args.path)

    with open(f'{local_path}/sites.json', 'r') as f:
        data = json.load(f)
        site_data = {}

        for d in data:
            port = data[d]['services']['nginx']['ports']['HTTP'][0]
            path = data[d]['path']
            site_data[d] = {'port': port, 'path': path, 'name': data[d]['name']}

        # 创建以当前日期为名的文件夹
        today = datetime.now().strftime("%Y-%m-%d-%H")
        folder_path = os.path.join(backup_path, today)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True, mode=0o777)

        for sd in site_data:
            url = f'http://127.0.0.1:{site_data[sd]["port"]}/'
            export_file_name = slugify(site_data[sd]["name"])

            try:
                requests.get(url)

                os.chdir(site_data[sd]["path"] + '/app/public')
                os.environ["PATH"] = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/Applications' \
                                     '/Local.app/Contents/Resources/extraResources/bin'
                os.environ["MYSQL_HOME"] = f'{local_path}/run/{sd}/conf/mysql'
                os.environ["WP_CLI_CONFIG_PATH"] = os.path.join(local_bin_path, "wp-cli/config.yaml")

                os.system(f'wp db export {export_file_name}.sql')

                # 移动.sql文件到文件夹
                source_file_path = os.path.join(os.getcwd(), f'{export_file_name}.sql')
                target_file_path = os.path.join(folder_path, f'{export_file_name}.sql')
                shutil.move(source_file_path, target_file_path)

            except ConnectionError:
                print(f'{export_file_name} not running, skip it.')

        # 压缩文件夹为.tar.gz文件
        output_file_path = os.path.join(backup_path, today + ".tar.gz")

        with tarfile.open(output_file_path, "w:gz") as tar:
            tar.add(folder_path, arcname=os.path.basename(folder_path))

        # 删除文件夹
        shutil.rmtree(folder_path)


if __name__ == '__main__':
    main()
