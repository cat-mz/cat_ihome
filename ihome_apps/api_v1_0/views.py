from . import api
from ihome_apps import db,models
@api.route("/index")
def index():
    return "index pages"
