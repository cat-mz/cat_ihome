from ihome_apps import create_app
from flask_migrate import Migrate,MigrateCommand
from flask_script import Manager
from ihome_apps import db
import pymysql
pymysql.install_as_MySQLdb()
# 创建flask应用对象
app=create_app("develop")
mananger=Manager(app)
Migrate(app,db)
mananger.add_command("db",MigrateCommand)


if __name__ == "__main__":
    # print(app.url_map)
    mananger.run()
    # app.run(debug=True)