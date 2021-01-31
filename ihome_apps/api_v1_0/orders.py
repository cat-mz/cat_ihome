from . import api
from flask import g,request,jsonify,current_app
from ihome_apps.utils.commons import login_required
from ihome_apps.utils.response_code import RET
from ihome_apps.models import House,Order
from datetime import datetime
from ihome_apps import db,redis_store


@api.route("/orders",methods=["POST"])
@login_required
def save_ordes():
    '''
    保存订单
    参数:house_id,start_date,end_date 2020-01-23
    格式:json
    '''
    user_id=g.user_id

    # 获取参数
    request_data=request.get_json()
    if not request_data:
        return jsonify(error=RET.PARAMERR,errmsg="请重新提交订单")

    house_id=request_data.get("house_id")   # 预订的房屋编号
    start_date=request_data.get("start_date")  # 预订的起始时间
    end_date=request_data.get("end_date")        # 预订的结束时间
    if not all([house_id,start_date,end_date]):
        return jsonify(error=RET.PARAMERR, errmsg="请重新提交订单")

    # 日期格式检查
    try:
        # 将请求的时间参数字符串转换为datetime类型
        start_date=datetime.strptime(start_date,"%Y-%m-%d")
        end_date=datetime.strptime(end_date,"%Y-%m-%d")
        assert start_date <= end_date
        # 计算预订的天数
        date=(end_date - start_date).days + 1     # datetime.timedelta
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.PARAMERR, errmsg="日期格式错误")

    # 查询房屋是否存在
    try:
        house=House.query.get(house_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="MYSQL错误")
    else:
        if house is None:
            return jsonify(error=RET.PARAMERR, errmsg="房屋信息错误")

    # 预订的房屋是否是房东自己的
    if user_id == house.user_id:
        return jsonify(error=RET.ROLEERR,errmsg="不能进行刷单")


    # 确保用户预订的时间内，房屋没有被别人下单
    try:
        # 查询时间冲突的订单数
        count=Order.query.filter(Order.begin_date <= end_date,Order.end_date >= start_date).count()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="检查出错，请稍候重试")
    else:
        if count > 0:
            return jsonify(error=RET.DATAERR,errmsg="房屋已被预订")

    # 订单总额
    count_price = date * house.price

    # 保存订单数据
    order=Order(
        user_id=user_id,
        house_id=house_id,
        begin_date=start_date,
        end_date=end_date,
        days=date,
        house_price=house.price,
        amount=count_price
    )

    try:
        db.session.add(order)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(error=RET.DBERR, errmsg="保存订单失败")
    return jsonify(error=RET.OK, errmsg="OK", data={"order_id": order.id})


# /api/v1.0/user/orders?role=custom     role=landlord
@api.route("/users/orders",methods=["GET"])
@login_required
def get_orders():
    """
    查询用户的订单信息
    参数:role 判断用户身份 房东 role=="landlord"
    """
    user_id = g.user_id

    # 判断用户的身份，用户想要查询作为房客预订别人房子的订单，还是想要作为房东查询别人预订自己房子的订单
    role = request.args.get("role", "")

    # 查询订单数据
    try:
        if role == "landlord":
            # 以房东的身份查询订单
            # 先查询属于自己的房子有哪些
            houses=Order.query.filter(House.user_id == user_id).all()
            houses_ids = [house.id for house in houses]
            # 再查询预订了自己房子的订单
            orders=Order.query.filter(Order.house_id.in_(houses_ids)).order_by(Order.create_time.desc()).all()
        else:
            # 以房客的身份查询订单， 查询自己预订的订单
            orders=Order.query.filter(Order.user_id == user_id).order_by(Order.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="查询订单信息失败")

    # 将订单对象转换为字典数据
    orders_dict_list = []
    if orders:
        for order in orders:
            orders_dict_list.append(order.to_dict())

    return jsonify(error=RET.OK, errmsg="OK", data={"orders": orders_dict_list})

@api.route("/orders/<int:order_id>/status", methods=["PUT"])
@login_required
def accept_reject_order(order_id):
    """
    参数:action:接单、拒单   如果拒单，要求用户传递拒单原因  reason
    格式:json
    """

    user_id = g.user_id

    # 获取参数
    request_data=request.get_json()
    if not request_data:
        return jsonify(error=RET.PARAMERR, errmsg="参数错误")

    # action参数表明客户端请求的是接单还是拒单的行为
    action= request_data.get("action")

    if action not in ("accept", "reject"):
        return jsonify(error=RET.PARAMERR, errmsg="参数错误")


    try:
        # 根据订单号查询订单，并且要求订单处于等待接单状态
        order = Order.query.filter(Order.id == order_id, Order.status == "WAIT_ACCEPT").first()
        house = order.house
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="无法获取订单数据")

    # 确保房东只能修改属于自己房子的订单
    if not order or house.user_id != user_id:
        return jsonify(error=RET.REQERR, errmsg="操作无效")

    if action == "accept":
        # 接单，将订单状态设置为等待评论
        order.status = "WAIT_PAYMENT"
    elif action == "reject":
        # 拒单，要求用户传递拒单原因
        reason = request_data.get("reason")
        if not reason:
            return jsonify(error=RET.PARAMERR, errmsg="参数错误")
        order.status = "REJECTED"
        order.comment = reason

    try:
        db.session.add(order)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(error=RET.DBERR, errmsg="操作失败")

    return jsonify(error=RET.OK, errmsg="OK")


@api.route("/orders/<int:order_id>/comment", methods=["PUT"])
@login_required
def save_order_comment(order_id):
    """保存订单评论信息"""
    user_id = g.user_id
    # 获取参数
    req_data = request.get_json()
    comment = req_data.get("comment")  # 评价信息

    # 检查参数
    if not comment:
        return jsonify(error=RET.PARAMERR, errmsg="参数错误")

    try:
        # 需要确保只能评论自己下的订单，而且订单处于待评价状态才可以
        order = Order.query.filter(Order.id == order_id, Order.user_id == user_id,
                                   Order.status == "WAIT_COMMENT").first()
        house = order.house
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="无法获取订单数据")

    if not order:
        return jsonify(error=RET.REQERR, errmsg="操作无效")

    try:
        # 将订单的状态设置为已完成
        order.status = "COMPLETE"
        # 保存订单的评价信息
        order.comment = comment
        # 将房屋的完成订单数增加1
        house.order_count += 1
        db.session.add(order)
        db.session.add(house)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(error=RET.DBERR, errmsg="操作失败")

    # 因为房屋详情中有订单的评价信息，为了让最新的评价信息展示在房屋详情中，所以删除redis中关于本订单房屋的详情缓存
    try:
        redis_store.delete("house_info_%s" % order.house.id)
    except Exception as e:
        current_app.logger.error(e)

    return jsonify(error=RET.OK, errmsg="OK")

