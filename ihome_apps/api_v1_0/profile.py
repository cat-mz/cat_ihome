from . import api
from flask import g,request,jsonify,current_app,session
from ihome_apps.utils.commons import login_required
from ihome_apps.utils.response_code import RET
from ihome_apps.utils.image_storage import storage
from ihome_apps.models import User
from ihome_apps import db
from ihome_apps.constants import QINIU_URL
from sqlalchemy.exc import IntegrityError

# 先访问网址,再进行校验  api在上面
@api.route("/users/avatar",methods=["POST"])
@login_required
def set_user_avatar():
    '''
    设置用户头像
    参数:图片,user_id
    '''
    # 装饰器的代码中已经将user_id存储在g对象中,所以可以获取
    user_id=g.user_id
    # 获取图片

    image_file=request.files.get("avatar")

    if image_file is None:
        return jsonify(error=RET.PARAMERR,errmsg="未上传图片")

    image_data= image_file.read()
    # 调用七牛云上传图片
    try:
        file_name=storage(image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.THIRDERR,errmsg="上传图片失败")

    # 保存文件名到数据库中
    try:
        User.query.filter_by(id=user_id).update({"avatar_url":file_name})
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR,errmsg="保存数据库失败")

    avatar_url=QINIU_URL +"/"+ file_name

    # 保存成功,返回信息
    return jsonify(error=RET.OK,errmsg="保存成功",data={"avatar_url":avatar_url})

@api.route("/users/name",methods=["PUT"])
@login_required
def set_user_name():
    '''
    格式:json
    参数:name
    '''
    user_id=g.user_id

    # 获取name参数
    username=request.get_json().get("name")

    if username is None:
        return jsonify(error=RET.PARAMERR,errmsg="请填写昵称")

    try:
        user=User.query.filter_by(id=user_id).update({"name":username})
        db.session.commit()
    except IntegrityError as e:
        # 表示出现重复值
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(error=RET.DATAEXIST,errmsg="用户名已存在")
    except Exception as  e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR,errmsg="保存数据库失败")
    session["name"]=username
    return jsonify(error=RET.OK,errmsg="存储成功",data={"username":username})

@api.route("/users/messages",methods=["GET"])
@login_required
def get_user_info():
    '''
    从数据库中获取数据,并返回前端
    参数:name ,avatar_uri json格式
    '''
    user_id=g.user_id

    try:
        user=User.query.filter_by(id=user_id).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR,errmsg="链接数据库失败")
    user.avatar_url=QINIU_URL + "/" + user.avatar_url
    return jsonify(error=RET.OK,errmsg="ok",data={"name":user.name,"mobile":user.mobile,"avatar_uri":user.avatar_url})

@api.route("/users/auth", methods=["GET"])
@login_required
def get_user_auth():
    """获取用户的实名认证信息"""
    user_id = g.user_id

    # 在数据库中查询信息
    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="获取用户实名信息失败")

    if user is None:
        return jsonify(error=RET.NODATA, errmsg="无效操作")

    return jsonify(error=RET.OK, errmsg="OK", data=user.auth_to_dict())

@api.route("/users/auth",methods=["POST"])
@login_required
def get_users_real_messages():
    '''
    获取真实姓名,身份证号码 14位
    格式:json
    '''
    user_id=g.user_id
    request_dict=request.get_json()
    if not request_dict:
        return jsonify(error=RET.PARAMERR,errmsg="参数不全")
    real_username=request_dict.get("real_name")
    user_ID_card=request_dict.get("id_card")

    if not all([real_username,user_ID_card]):
        return jsonify(error=RET.DATAERR ,errmsg="参数不全请重新输入")

    # 只有真实姓名字段与身份证号码字段都为None,才允许,提交修改,意味着只能提交一次
    try:
        user=User.query.filter_by(id=user_id,real_name=None,id_card=None).update({"real_name":real_username,"id_card":user_ID_card})
        db.session.commit()
    except Exception as  e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(error=RET.DBERR, errmsg="保存用户实名信息失败")

    return jsonify(error=RET.OK, errmsg="OK")
