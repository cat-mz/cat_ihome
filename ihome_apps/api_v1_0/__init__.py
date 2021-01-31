from flask import Blueprint

# 创建蓝图对象
api=Blueprint("api_v1_0",__name__)
# 导入蓝图的视图
from . import views,users, verify_code, passport, profile, houses, orders, pay