from werkzeug.routing import BaseConverter
from flask import session,jsonify,g
from ihome_apps.utils.response_code import RET
import functools
# 正则表达式
class ReConverter(BaseConverter):
    def __init__(self,url_map,regex):
        # 调用父类的初始化方法 初始化url_map路由信息
        super(ReConverter,self).__init__(url_map)
        # 将正则表达式的参数保存到对象的属性中,flask会去使用这个属性进行路由的正则匹配
        self.regex=regex


# 定义的验证登录状态的装饰器
def login_required(view_func):

    @functools.wraps(view_func)
    def wrapper(*args,**kwargs):
        # 判断用户的登录状态
        user_id=session.get("user_id")
        # 如果用户为登录状态,执行视图函数
        if user_id is not  None:
            g.user_id=user_id
            # 被装饰的函数可以g通过 user_id=g.user_id 获取数据
            return view_func(*args,**kwargs)
        else:
            # 如果未登录,返回json数据
            return jsonify(error=RET.SESSIONERR,errmsg="用户未登录")
    return wrapper