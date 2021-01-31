from . import api
from ihome_apps import db,redis_store,constants
from flask import current_app,jsonify,make_response,request
from ihome_apps.utils.captcha.captcha import captcha
from ihome_apps.utils import response_code
from ihome_apps.models import User
import random
from ihome_apps.libs.send import send_msg
import json

# GET 127.0.0.1/api/v1.0/image_codes/<image_code_id>
@api.route("/image_codes/<image_codes_id>")
def get_image_code(image_codes_id):
    """
    获取图片验证码
    : params image_code_id:  图片验证码编号
    :return:  正常:验证码图片  异常：返回json
    """
    # 业务逻辑处理
    # 生成验证码图片
    # 名字，真实文本， 图片数据
    name,text,image_data=captcha.generate_captcha()
    # 将验证码真实值与编号保存到redis中, 设置有效期
    # redis：  字符串   列表  哈希   set
    # "key": xxx 字符串
    # 使用哈希维护有效期的时候只能整体设置
    # "image_codes": {"id1":"abc", "":"", "":""} 哈希  hset("image_codes", "id1", "abc")  hget("image_codes", "id1")
    # 单条维护记录，选用字符串
    # "image_code_编号1": "真实值"
    # "image_code_编号2": "真实值"
    # 以列表格式存储,获取get key
    # redis_store.set("image_code_%s" % image_code_id, text)
    # redis_store.expire("image_code_%s" % image_code_id, constants.IMAGE_CODE_REDIS_EXPIRES)
    #                   记录名字                          有效期                              记录值
    try:
        print(image_codes_id)
        print(type(image_codes_id))
        redis_store.setex("image_code_%s" % image_codes_id,constants.IMAGE_CODE_REDIS_OUTTIME,text)
    except Exception as e:
        # 记录日志
        current_app.logger.error(e)
        return jsonify(error=response_code.RET.DBERR,errmsg="保存图片验证码失败")
    # 返回图片
    resp=make_response(image_data)
    resp.headers["Content-Type"] = "image/jpg"
    return  resp


# GET /api/v1.0/sms_codes/<mobile>?image_code=xxxx&image_code_id=xxxx
@api.route("/sms_codes/<re(r'1[3-9]\d{9}'):moblie>")
def get_sms_code(moblie):
    """获取短信验证码"""
    # 获取参数
    image_code_id=request.args.get("image_code_id")
    image_codes=request.args.get("image_codes")
    # 校验参数
    if not all([image_codes,image_code_id]):
        # 表示参数不完整
        return jsonify(error=response_code.RET.PWDERR,errmsg="参数不完整")
    # 业务逻辑处理
    # 从redis中取出真实的图片验证码
    try:
        real_image_code=redis_store.get("image_code_%s" % image_code_id )
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=response_code.RET.DBERR,errmsg="redis数据库异常")
    # 判断图片验证码是否过期
    if real_image_code is None:
        # 表示图片验证码没有或者过期
        return jsonify(error=response_code.RET.NODATA,errmsg="图片验证码失效")

    # 删除redis中的图片验证码，防止用户使用同一个图片验证码验证多次
    try:
        redis_store.delete("image_code_%s" % image_code_id)
    except Exception as e:
        current_app.logger(e)


    # 与用户填写的值进行对比
    '''
    print("----------------------1---------------------------")
    print("---%s----%s" % (real_image_code.lower(),image_codes.lower()))
    print("----------------------2---------------------------")

    ----------------------1---------------------------
    ---b'zsyj'----zsyj      从url获取,比特类型 real_image_code.decode()
    ----------------------2---------------------------
    '''
    if real_image_code.decode().lower() != image_codes.lower():
        # 表示用户填写错误
        return jsonify(error=response_code.RET.DATAERR,errmsg="图片验证码错误")


    # 判断对于这个手机号的操作，在60秒内有没有之前的记录，如果有，则认为用户操作频繁，不接受处理
    try:
        send_flag=redis_store.get("send_sms_code_%s" % moblie)
    except Exception as e:
        current_app.logger.error(e)
    else:
        if send_flag is not None:
            # 表示在60秒内发送过记录
            return jsonify(error=response_code.RET.REQERR,errmsg="请求过于频繁")



    try:
        user=User.query.filter_by(moblie=moblie).first()
    except Exception as e:
        current_app.logger.error(e)
    else:
        if user is not None:
            # 表示手机号已存在
            return jsonify(error=response_code.RET.DATAEXIST,errmsg="手机号已存在")


    # 如果手机号不存在，则生成短信验证码 ,可以确保生成六位
    sms_code="%06d" % random.randint(0,999999)


    # 保存真实的短信验证码
    try:
        redis_store.setex("sms_code_%s" % moblie,constants.SEND_SMS_CODE_OUTTIME,sms_code)
        # 保存发送给这个手机号的记录，防止用户在60s内再次出发发送短信的操作
        redis_store.setex("send_sms_code_%s" % moblie,constants.SEND_SMS_CODE_OUTTIME,1)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=response_code.RET.DBERR,errmsg="保存短信验证码异常")


    datas=sms_code,constants.SMS_CODE_REDIS_OUTTIME
    '''
    发送成功返回的值
    {"statusCode":"000000","templateSMS":{"smsMessageSid":"b388c3051dc042
    ...: ec9e286ab30543db8e","dateCreated":"20210126143409"}}
    '''
    Send={"statusCode":"000000","templateSMS":{"smsMessageSid":"a22692e1ea804c61b4830db8085d6186","dateCreated":"20210126154918"}}
    Send=json.dumps(Send)
    try:
        # Send=send_msg(moblie,datas)
        Send = json.loads(Send)#返回的值为json,需要将json格式转化为字典
        print("----------------------1---------------------------")
        print(Send)
        print("----------------------2---------------------------")
    except Exception as e:
        current_app.logger.error(e)

    if Send["statusCode"] == "000000":
        return jsonify(error=response_code.RET.OK,errmsg="发送成功")
    else:
        return jsonify(error=response_code.RET.THIRDERR, errmsg="发送失败")




