from . import api
from flask import request,jsonify,current_app,session
from ihome_apps import redis_store,db,constants
from ihome_apps.models import User
from ihome_apps.utils.response_code import RET
from sqlalchemy.exc import IntegrityError
import re
@api.route("/users",methods=["POST"])
def register():
    '''注册
    请求参数:moblie,短信验证码,密码1 2
    参数格式:json
    '''
    request_dict=request.get_json()
    print("--------------1------------------------")
    print(request_dict)
    print(type(request_dict))
    print("--------------1------------------------")
    user_moblie=request_dict.get("mobile")
    sms_codes=request_dict.get("sms_codes")
    pwd1=request_dict.get("password")
    pwd2 = request_dict.get("password2")
    if not all([user_moblie,sms_codes,pwd1,pwd2]):
        return jsonify(error=RET.PARAMERR,errmsg="参数不完整")
    # 判断手机号格式
    if not re.match(r"1[3-9]\d{9}",user_moblie):
        # 格式错误
        return jsonify(error=RET.PARAMERR,errmsg="手机格式错误")

    if pwd1 != pwd2:
        return jsonify(error=RET.PARAMERR,errmsg="两次密码不一致")

    # redis中取出短信验证码
    try:
        real_sms_codes=redis_store.get("sms_code_%s" % user_moblie)
    except Exception as  e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR,errmsg="读取真实验证码异常")
    # 并判断其有效期
    if real_sms_codes is None:
        return jsonify(error=RET.NODATA,errmsg="短信验证码失效")
    # 删除redis中的短信验证码
    try:
        redis_store.delete("sms_codes_%s" % user_moblie)
    except Exception as  e:
        current_app.logger.error(e)

    # 判断用户的填写短信验证码正确性
    if real_sms_codes.decode() != sms_codes:
        return jsonify(error=RET.DATAERR,errmsg="短信验证码错误")
    # 判断手机号是否注册过
    # try:
    #     user=User.query.filter_by(moblie=user_moblie).first()
    # except Exception as e:
    #     current_app.logger.error(e)
    #     return jsonify(error=RET.DBERR, errmsg="数据库异常")
    # else:
    #     if user is not None:
    #         # 表示手机号已存在
    #         return jsonify(error=RET.DATAEXIST,errmsg="手机号已存在")

    # 将注册信息存入数据库
    try:
        users=User(name=user_moblie,mobile=user_moblie)
        # users.generate_password_hash(pwd1) 第一种方法
        users.password=pwd1 #设置密码
        db.session.add(users)
        db.session.commit()
    except IntegrityError as e:
        # 数据库操作错误回滚
        db.session.rollback()
        # 表示出现重复值,判断手机号是否注册过
        current_app.logger.error(e)
        return jsonify(error=RET.DATAEXIST,errmsg="手机号已存在")
    except Exception as  e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="数据库异常")
    # 保存登录状态
    session["name"]=user_moblie
    session["moblie"]=user_moblie
    session["User_id"]=users.id
    # 返回
    return jsonify(error=RET.OK,errmsg="注册成功")


@api.route("/login",methods=["POST"])
def login():
    '''
    用户登录
    参数:手机号,密码,
    格式:json
    '''
    request_dict=request.get_json()
    mobile=request_dict.get("mobile")
    pwd=request_dict.get("password")
    print("---%s---%s---"% (mobile,pwd))
    if not all([mobile,pwd]):
        return jsonify(error=RET.PARAMERR,errmsg="参数不完整")

    # 判断手机号格式
    if not re.match(r"1[3-9]\d{9}", mobile):
        # 格式错误
        return jsonify(error=RET.PARAMERR, errmsg="手机格式错误")

    # 判断错误次数是否超过限制次数,如果超过限制,返回
    # redis记录:"access_token_用户请求的ip地址":次数
    user_ip=request.remote_addr  #获取用户ip地址
    try:
        access_nums=redis_store.get("access_num_%s" % user_ip)
    except Exception as e:
        current_app.logger.error(e)
    else:
        if access_nums is not None and int(access_nums) >= constants.LOGIN_ERROR_MAX_NUMBER:
            return jsonify(error=RET.REQERR,errmsg="错误次数过多,请稍后重试")

    # 从数据库中拿取用户数据
    try:
        user=User.query.filter_by(mobile=mobile).first()
    except Exception as  e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="数据库异常")

    # 用户名为空               密码错误
    if user is None or not user.check_password(pwd):
        # 验证失败,记录验证次数
        try:
            redis_store.incr("access_num_%s" % user_ip)
            redis_store.expire("access_num_%s" % user_ip,constants.LOGIN_ERROR_TIME)
        except Exception as e:
            current_app.logger.error(e)
        return jsonify(error=RET.DATAERR,errmsg="用户名或密码输入有误")

    # 如果验证成功,将登录状态记录在session中,并返回值
    session["name"]=user.name
    session["moblie"]=user.mobile
    session["user_id"]=user.id

    return jsonify(error=RET.OK,errmsg="登录成功")


@api.route("/login",methods=["GET"])
def check_login():
    '''检查登录状态'''
    name=session.get("name")
    if name is None:
        return jsonify(error=RET.SESSIONERR,errmsg="false")
    else:
        return jsonify(error=RET.OK,errmsg="True",data={"name":name})

@api.route("/login",methods=["DELETE"])
def delete_login():
    '''退出登录'''
    csrf_token=session.get("csrf_token")
    session.clear()
    session["csrf_token"]=csrf_token
    return jsonify(error=RET.OK,errmsg="退出登录")