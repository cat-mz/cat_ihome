from flask import Blueprint,current_app,make_response
from flask_wtf import csrf

# 提供静态文件
html=Blueprint("web.html",__name__)
# 127.0.0.1:5000/favicon.ico 浏览器认为的网站标识,浏览器会自己请求这个资源,标题图片

@html.route('/<re(r".*"):html_name>')
def get_html(html_name):
    """提供html文件"""
    # 如果html_file_name为"",表示访问路径是/,请求主页
    if not html_name:
        html_name = "index.html"
        # 如果资源名不是favicon.ico
    if html_name !="favicon.ico":
        html_name="html/" + html_name
    # 创建一个csrf_token值
    csrf_token=csrf.generate_csrf()
    # flask提供的静态文件返回方法
    resp=make_response(current_app.send_static_file(html_name))
    # 设置cookie值
    resp.set_cookie("csrf_token",csrf_token)
    return  resp


