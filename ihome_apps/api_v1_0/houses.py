from . import api
from flask import g,request,jsonify,current_app,session
from ihome_apps.utils.commons import login_required
from ihome_apps.utils.response_code import RET
from ihome_apps.utils.image_storage import storage
from ihome_apps.models import Area,House,Facility,HouseImage,User,Order
from datetime import datetime
from ihome_apps import db,redis_store
from ihome_apps.constants import *
import json

@api.route("/areas")
def get_houses_area():
    '''获取城区信息'''
    try:
        resp=redis_store.get("area_info").decode()
        print(type(resp))
    except Exception as e:
        current_app.logger.error(e)
    else:
        if resp is not None:
            current_app.logger.info("hit redis area_info")
            return resp,200,{"Content-Type":"application/json"}

    try:
        area_li=Area.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DATAERR,errmsg="数据库异常")
    area_dict_li=[]

    for area in area_li:
        area_dict_li.append(area.to_dict())

    # 将数据转化为json
    resp_dict=dict(error=RET.OK,errmsg="OK",data=area_dict_li)
    resp_json=json.dumps(resp_dict)
    # 将数据保存到redis中
    try:
        redis_store.setex("area_info",AREA_REDIS_CACHE_TIME,resp_json)
    except Exception as e:
        current_app.logger.error(e)

    return resp_json,200,{"Content-Type":"application/json"}

@api.route("/houses/info",methods=["POST"])
@login_required
def save_house_info():
    """保存房屋的基本信息
    前端发送过来的json数据
    {
        "title":"",
        "price":"",
        "area_id":"1",
        "address":"",
        "room_count":"",
        "acreage":"",
        "unit":"",
        "capacity":"",
        "beds":"",
        "deposit":"",
        "min_days":"",
        "max_days":"",
        "facility":["7","8"]
    }
    """
    # 获取数据
    user_id=g.user_id
    house_data=request.get_json()

    title = house_data.get("title")  # 房屋名称标题
    price = house_data.get("price")  # 房屋单价
    area_id = house_data.get("area_id")  # 房屋所属城区的编号
    address = house_data.get("address")  # 房屋地址
    room_count = house_data.get("room_count")  # 房屋包含的房间数目
    acreage = house_data.get("acreage")  # 房屋面积
    unit = house_data.get("unit")  # 房屋布局（几室几厅)
    capacity = house_data.get("capacity")  # 房屋容纳人数
    beds = house_data.get("beds")  # 房屋卧床数目
    deposit = house_data.get("deposit")  # 押金
    min_days = house_data.get("min_days")  # 最小入住天数
    max_days = house_data.get("max_days")  # 最大入住天数

    if not all([title,price,area_id,address,room_count,acreage,unit,capacity,beds,deposit,min_days,max_days]):
        return jsonify(error=RET.PARAMERR,errmsg="参数不全")
    try:
        price = int(float(price) * 100)
        deposit = int(float(deposit) * 100)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.PARAMERR, errmsg="参数错误")

    # 判断城区id是否存在
    try:
        area=Area.query.get(area_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="数据库1异常")

    if area is None:
        return jsonify(error=RET.NODATA, errmsg="城区信息有误")

    # 保存房屋信息
    house = House(
        user_id=user_id,
        area_id=area_id,
        title=title,
        price=price,
        address=address,
        room_count=room_count,
        acreage=acreage,
        unit=unit,
        capacity=capacity,
        beds=beds,
        deposit=deposit,
        min_days=min_days,
        max_days=max_days
    )


    # 处理房屋的设施信息
    facility_ids=house_data.get("facility")

    # 如果用户勾选设施信息,再保存数据库
    if facility_ids:
        # select  * from ih_facility_info where id in []
        try:
            facilities=Facility.query.filter(Facility.id.in_(facility_ids)).all()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(error=RET.DBERR, errmsg="数据库2异常")
        if facilities:
            # 表示有合法的设施数据
            # 保存设施数据
            house.facilities =facilities

    try:
        db.session.add(house)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(error=RET.DBERR, errmsg="保存数据失败")


    # 保存数据成功
    return jsonify(error=RET.OK, errmsg="OK", data={"house_id": house.id})


@api.route("/houses/image",methods=["POST"])
@login_required
def save_houses_images():
    '''
    保存房屋的图片
    参数:图片,houses_id
    '''
    image_files=request.files.get("house_image")
    house_id=request.form.get("house_id")

    if not all([house_id,image_files]):
        return jsonify(error=RET.PARAMERR, errmsg="参数不全")

    # 判断house_id是否存在
    try:
        house=House.query.get(house_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="数据库异常")

    if house is None:
        return jsonify(error=RET.NODATA, errmsg="房屋信息有误")

    # 图片的二进制数据
    image_data=image_files.read()
    # 保存图片到七牛云中
    try:
        file_name=storage(image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.THIRDERR,errmsg="第三方保存图片失败")

    # 保存url到数据库中
    house_image=HouseImage(house_id=house_id,url=file_name)
    db.session.add(house_image)

    # 处理房屋首页图片
    if not house.index_image_url:
        house.index_image_url=file_name
        db.session.add(house)


    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="数据库异常")

    image_url=QINIU_URL + "/" + file_name
    return jsonify(error=RET.OK , errmsg="OK",data={"image_url":image_url})


@api.route("/users/houses")
@login_required
def get_users_house():
    '''获取房东房屋信息'''
    user_id=g.user_id

    try:
        user=User.query.get(user_id)
        houses=user.houses
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="获取数据失败")

    # 将查询到的房屋信息转换为字典存放到列表中
    house_li=[]

    if houses:
        for house in houses:
            house_li.append(house.to_basic_dict())
    return jsonify(error=RET.OK, errmsg="OK", data={"houses": house_li})


@api.route("/houses/index")
def get_houses_index():
    '''
    获取主页幻灯片展示的房屋基本信息
    参数:房屋图片路由,从数据库获取,访问七牛云
    redis
    '''
    # 从缓存中尝试获取数据
    try:
        resp=redis_store.get("home_page_data")
    except Exception as e:
        current_app.logger.error(e)
        resp = None

    if resp is not None:
        current_app.logger.info("hit house index info redis")
        # 因为redis中保存的是json字符串，所以直接进行字符串拼接返回
        return '{"error":0, "errmsg":"OK", "data":%s}' % resp.decode(), 200, {"Content-Type": "application/json"}
    else:
        # 查询数据库，返回房屋订单数目最多的5条数据
        try:
            houses = House.query.order_by(House.order_count.desc()).limit(HOME_PAGE_MAX_HOUSES)
            # houses=House.query.all()[1].user_id
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(error=RET.DBERR, errmsg="查询数据失败")

        if not houses:
            return jsonify(error=RET.NODATA, errmsg="查询无数据")
        print("-----------1===-----------" )
        print("-----------%s_______------" % houses)
        print("-----------2===-----------")
        houses_li=[]

        for house in houses:
            # 如果房屋未设置主图片，则跳过
            if not house.index_image_url:
                continue
            houses_li.append(house.to_basic_dict())
        print("-----------1===-----------")
        print("-----------%s_______------" % houses_li)
        print("-----------2===-----------")
        # 将数据转换为json，并保存到redis缓存
        house_json=json.dumps(houses_li)
        try:
            redis_store.setex("home_page_data",HOUSES_REDIS_CACHE_TIME,house_json)
        except Exception as e:
            current_app.logger.error(e)
        print("-----------1===-----------")
        print("-----%s_______------" % house_json)
        print("-----------2===-----------")

    return '{"error":0, "errmsg":"OK", "data":%s}' % house_json, 200, {"Content-Type": "application/json"}

@api.route("/houses/<int:house_id>")
def get_houses_detail(house_id):
    """获取房屋详情"""
    # 前端在房屋详情页面展示时，如果浏览页面的用户不是该房屋的房东，则展示预定按钮，否则不展示，
    # 所以需要后端返回登录用户的user_id
    # 尝试获取用户登录的信息，若登录，则返回给前端登录用户的user_id，否则返回user_id=-1
    user_id = session.get("user_id", "-1")
    # 校验参数
    if not house_id:
        return jsonify(error=RET.PARAMERR, errmsg="参数确实")

    # 先从redis缓存中获取信息
    try:
        ret = redis_store.get("house_info_%s" % house_id).decode()
    except Exception as e:
        current_app.logger.error(e)
        ret = None
    if ret:
        current_app.logger.info("hit house info redis")
        return '{"error":"0", "errmsg":"OK", "data":{"user_id":%s, "house":%s}}' % (user_id, ret),200, {"Content-Type": "application/json"}

     # 查询数据库
    try:
        house = House.query.get(house_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="查询数据失败")

    if not house:
        return jsonify(error=RET.NODATA, errmsg="房屋不存在")

        # 将房屋对象数据转换为字典
    try:
        house_data = house.to_full_dict()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DATAERR, errmsg="数据出错")

        # 存入到redis中
    json_house = json.dumps(house_data)
    try:
        redis_store.setex("house_info_%s" % house_id, HOUSES_REDIS_CACHE_TIME, json_house)
    except Exception as e:
        current_app.logger.error(e)

    resp = '{"error":"0", "errmsg":"OK", "data":{"user_id":%s, "house":%s}}' % (user_id, json_house), 200, {"Content-Type": "application/json"}

    return resp


# GET /api/v1.0/houses?sd=2021-01-01&ed=2021-02-5&aid=10&sk=new&page=1
@api.route("/houses")
def get_houses_list():
    """获取房屋的列表信息（搜索页面）---分页处理显示减轻mysql"""
    start_date=request.args.get("sd","") #居住起始时间
    end_date=request.args.get("ed","") #居住结束时间
    area_id =request.args.get("aid","") #区域号
    sork_key=request.args.get("sk","new")#排序关键字 缺省参数默认new
    page=request.args.get("p")#页数

    # 判断日期
    try:
        if start_date:
            start_date=datetime.strptime(start_date,"%Y-%m-%d")

        if end_date:
            end_date=datetime.strptime(end_date,"%Y-%m-%d")

        if start_date and end_date:
            assert start_date <=end_date
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.PARAMERR,errmsg="日期参数有误")


    # 判断区域号
    try:
        area=Area.query.get(area_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.PARAMERR, errmsg="区域参数有误")

    # 处理页数
    try:
        page=int(page)
    except Exception as e:
        current_app.logger.error(e)
        page=1

    # 使用缓存
    redis_key="house_%s_%s_%s_%s" % (start_date,end_date,area_id,sork_key)
    try:
        resp_json=redis_store.hget(redis_key,page)
    except Exception as e:
        current_app.logger.error(e)
    else:
        if resp_json:
            return resp_json,200,{"Content-Type": "application/json"}


    # 参数不确定时,用列表存储参数,后期取出来时,解包
    # 过滤条件参数的容器
    filter_parmas = []
    conflict=None
    try:
        if start_date and end_date:
            # 查询冲突的订单
            conflict=Order.query.filter(Order.begin_date <= end_date,Order.end_date >=start_date ).all()
        elif start_date:
            conflict=Order.query.filter(Order.end_date>=start_date).all()
        elif end_date:
            conflict=Order.query.filter(Order.begin_date<=end_date)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="数据库异常")

    if conflict is not None:
        # 从订单中获取冲突房屋id
        conflict_houses_id = [order.house_id for order in conflict]

        # 如果冲突房屋id不为空.向查询参数添加条件
        if conflict_houses_id:
            filter_parmas.append(House.id.notin_(conflict_houses_id))
    # 区域条件
    if area_id:
        filter_parmas.append(House.area_id == area_id)
        #转化为sql语句表达式

    # 查询mysql
    # 排序 new
    if sork_key == "booking":#入住最多
        houses=House.query.filter(*filter_parmas).order_by(House.order_count.desc())
    elif sork_key == "price-inc":
        houses=House.query.filter(*filter_parmas).order_by(House.price.asc())
    elif sork_key == "price-des":
        houses=House.query.filter(*filter_parmas).order_by(House.price.desc())
    else:
        houses=House.query.filter(*filter_parmas).order_by(House.create_time.desc())

    # 处理分页
    try:
        #                               当前页数          每页数据量                              自动的错误输出
        page_data=houses.paginate(page=page,per_page=HOUSES_LIST_PAGE,error_out=False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="数据库异常")

    # 获取页面数据
    house_li=page_data.items
    house=[]
    for i in house_li:
        house.append(i.to_basic_dict())

    # 获取总页数
    total_pages=page_data.pages

    resp_dict=dict(error=RET.OK,errmsg="ok",data={"total_page": total_pages, "houses": house, "current_page": page})
    resp_json=json.dumps(resp_dict)
    # 设置缓存信息
    redis_key="house_%s_%s_%s_%s" % (start_date,end_date,area_id,sork_key)
    # 设置哈希类型
    try:
        # redis_store.hset(redis_key,page,resp_json)
        # redis_store.expire(redis_key,HOUSES_LIST_REDIS_CACHE)
        # 创建管道对象,可以一次性执行多条语句
        pipeline=redis_store.pipeline()
        # 开启多条语句的记录
        pipeline.multi()
        pipeline.hset(redis_key,page,resp_json)
        pipeline.expire(redis_key,HOUSES_LIST_REDIS_CACHE)
        # 执行多条语句
        pipeline.execute()
    except Exception as e:
        current_app.logger.error(e)

    return resp_json,200,{"Content-Type": "application/json"}

# redis_store
#
# "house_起始_结束_区域id_排序_页数"
# (error=RET.OK, errmsg="OK", data={"total_page": total_page, "houses": houses, "current_page": page})
#
#
#
# "house_起始_结束_区域id_排序": hash
# {
#     "1": "{}",
#     "2": "{}",
# }
