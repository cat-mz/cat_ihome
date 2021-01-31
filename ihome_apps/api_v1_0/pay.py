from . import api
from flask import g,current_app,jsonify,request
from ihome_apps.utils.commons import login_required
from  ihome_apps.models import Order,db
from ihome_apps.utils.response_code import RET
from ihome_apps.constants import  ALIPAY_URL
from alipay import AliPay
from alipay.utils import AliPayConfig
import os

@api.route("/orders/<int:order_id>/payment",methods=["POST"])
@login_required
def order_pay(order_id):
    '''发起支付宝支付'''

    user_id=g.user_id
    # 判断订单状态
    try:
        order=Order.query.filter(Order.id==order_id,Order.user_id==user_id,Order.status=="WAIT_PAYMENT").first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.PARAMERR,errmsg="MYSQL异常")

    if order is None:
        return jsonify(error=RET.NODATA,errmsg="订单数据有误")

    # 私钥
    app_private_key_string=os.path.join(os.path.dirname(__file__),"keys/app_private_key.pem")
    app_private_key_string = open(app_private_key_string,"r").read()
    print(app_private_key_string)
    print("=======================================")
    print(type(app_private_key_string))

    # 公钥
    alipay_public_key_string=os.path.join(os.path.dirname(__file__),"keys/alipay_public_key.pem")
    alipay_public_key_string = open(alipay_public_key_string,"r").read()
    print(alipay_public_key_string)
    print("=======================================")
    print(type(alipay_public_key_string))
    # 创建支付宝sdk工具对象
    alipay = AliPay(
        appid="2021000118642729",
        app_notify_url=None,  # 默认回调url
        app_private_key_string=app_private_key_string,
        # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
        alipay_public_key_string=alipay_public_key_string,
        sign_type="RSA2" , # RSA 或者 RSA2
        debug = True,  # 默认False
        config = AliPayConfig(timeout=15)  # 可选, 请求超时时间
    )

    # 手机网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string
    # 沙箱环境:https: // openapi.alipaydev.com / gateway.do? + order_string
    order_string = alipay.api_alipay_trade_wap_pay(
        out_trade_no=order.id,    # 订单编号
        total_amount=str(order.amount/100.0),   # 总金额
        subject="云猫爱家租房 %s" % order.id,    # 订单标题
        return_url="http://127.0.0.1:5000/payComplete.html",    # 返回的连接地址
        notify_url=None # 可选, 不填则使用默认notify url
    )
    # 构建让用户跳转的支付链接
    pay_url=ALIPAY_URL + order_string
    return jsonify(error=RET.OK,errmsg="ok",data={"pay_url":pay_url})


@api.route("/orders/payment",methods=["PUT"])
@login_required
def get_payment():
    '''获取支付结果'''

    alipay_data=request.form.to_dict()

    # 对支付宝的数据进行分离  提取出支付宝的签名参数sign 和剩下的其他数据
    signature = alipay_data.pop("sign")

    app_private_key_string = os.path.join(os.path.dirname(__file__), "keys/app_private_key.pem")
    app_private_key_string = open(app_private_key_string, "r").read()

    # 公钥
    alipay_public_key_string = os.path.join(os.path.dirname(__file__), "keys/alipay_public_key.pem")
    alipay_public_key_string = open(alipay_public_key_string, "r").read()

    # 创建支付宝sdk工具对象
    alipay = AliPay(
        appid="2021000118642729",
        app_notify_url=None,  # 默认回调url
        app_private_key_string=app_private_key_string,
        # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
        alipay_public_key_string=alipay_public_key_string,
        sign_type="RSA2",  # RSA 或者 RSA2
        debug=True,  # 默认False
        config=AliPayConfig(timeout=15)  # 可选, 请求超时时间
    )

    # 借助工具验证参数的合法性
    # 如果确定参数是支付宝的，返回True，否则返回false
    result=alipay.verify(alipay_data,signature)

    if result:
        # 修改数据库的订单
        order_id=alipay_data.get("out_trade_no")
        trade_no=Order.query.get("trade_no")
        try:
            Order.query.filter_by(id=order_id).update({"status":"WAIT_COMMENT","trade_no":trade_no})
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            db.session.rollback()

    return jsonify(error=RET.OK,errmsg="ok")
