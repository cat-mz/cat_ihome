from ronglian_sms_sdk import SmsSDK
from ihome_apps import constants

def send_msg(mobile,datas):
    '''发送短信验证码'''
    sdk=SmsSDK(constants.accId,constants.accToken,constants.accIp)
    tid=constants.TID
    resp=sdk.sendMessage(tid,mobile,datas)
    return resp

if __name__ == '__main__':
    send_msg()