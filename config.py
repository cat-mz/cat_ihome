
import redis

class Config(object):
    # session需要用到的密钥字符串
    SECRET_KEY="fwe974g43n9hv287ybormji"
    # 数据库配置
    SQLALCHEMY_DATABASE_URI="mysql://root:103@127.0.0.1:3306/ihome"
    SQLALCHEMY_TRACK_MODIFICATIONS=True
    # redis
    REDIS_HOST="127.0.0.1"
    REDIS_PORT=6379
    # session
    SESSION_TYPE="redis"
    SESSION_REDIS=redis.StrictRedis(host=REDIS_HOST,port=REDIS_PORT)
    SESSION_USE_SIGNER=True #对cookie中的session_id进行隐藏
    PERMANENT_SESSION_LIFETIME=86400 #代表秒的整数,session数据有效期


class DevelopmentConfig(Config):
    '''开发模式的配置信息'''
    DEBUG=True

class ProductionConfig(Config):
    '''生产环境配置信息'''
    pass

config_map={
    "develop":DevelopmentConfig,
    "product":ProductionConfig
}