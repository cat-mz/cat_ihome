#   coding=utf-8
from qiniu import Auth, put_data, etag, urlsafe_base64_encode
import qiniu.config

# 需要填写你的 Access Key 和 Secret Key
access_key = 'lB1PvBCDjkbu4UB1hJER1vPJ-CFLw3HpxFSH5vJ8'
secret_key = '11dNf2f04Y30FWUgpUtIM-B2egtLcjLrUyJjVFt_'


def storage(file_data):
    """
    上传文件到七牛
    :param file_data: 要上传的文件数据
    :return:
    """
    # 构建鉴权对象
    q = Auth(access_key, secret_key)

    # 要上传的空间
    bucket_name = 'cat-ihome01'

    # 生成上传 Token，可以指定过期时间等
    token = q.upload_token(bucket_name, None, 3600)

    ret, info = put_data(token, None, file_data)

    print(info)
    print("*"*10)
    print(ret)
    if info.status_code == 200:
        # 表示上传成功, 返回文件名
        # {"hash":  xxx ,"key":xxx}
        return ret.get("key")
    else:
        # 上传失败
        raise Exception("上传七牛失败")


if __name__ == '__main__':
    # {'hash': 'FsxYqPJ-fJtVZZH2LEshL7o9Ivxn', 'key': 'FsxYqPJ-fJtVZZH2LEshL7o9Ivxn'}
    with open("/home/cat/Desktop/ihome/ihome_apps/static/images/home01.jpg", "rb") as f:
        file_data = f.read()
        storage(file_data)
