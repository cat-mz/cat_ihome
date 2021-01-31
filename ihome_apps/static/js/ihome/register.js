function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

var imageCodeId = "";

function generateUUID() {
    var d = new Date().getTime();
    if(window.performance && typeof window.performance.now === "function"){
        d += performance.now(); //use high-precision timer if available
    }
    var uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = (d + Math.random()*16)%16 | 0;
        d = Math.floor(d/16);
        return (c=='x' ? r : (r&0x3|0x8)).toString(16);
    });
    return uuid;
}

function generateImageCode() {
     // 形成图片验证码的后端地址， 设置到页面中，让浏览请求验证码图片
    // 1. 生成图片验证码编号
    imageCodeId=generateUUID()
    // 是指图片url
    var url="/api/v1.0/image_codes/" + imageCodeId
    $(".image-code img").attr("src",url);

}

function sendSMSCode() {
    //点击发送短信验证码后被执行的函数
    $(".phonecode-a").removeAttr("onclick");
    var mobile = $("#mobile").val();
    if (!mobile) {
        $("#mobile-err span").html("请填写正确的手机号！");
        $("#mobile-err").show();
        $(".phonecode-a").attr("onclick", "sendSMSCode();");
        return;
    } 
    var imageCode = $("#imagecode").val();
    if (!imageCode) {
        $("#image-code-err span").html("请填写验证码！");
        $("#image-code-err").show();
        $(".phonecode-a").attr("onclick", "sendSMSCode();");
        return;
    }
    //构造向后端发送的数据
    var request_data={
        image_codes:imageCode,//图片验证码的值
        image_code_id:imageCodeId,//图片验证码编号
    };
//    向后端发送请求
    $.get("/api/v1.0/sms_codes/" + mobile,request_data,function(resp){
            //resp是后端响应值,因为后端返回json字符串
            // ajax自动将json转化为js对象
            if (resp.error=="0"){
                var number=60;
                //发送成功
                var timer=setInterval(function(){
                    if (number>=1){
                        // 修改倒计时文本
                        $(".phonecode-a").html(number + "秒")
                        number-=1;
                    }else{
                        $(".phonecode-a").html("获取验证码");
                        $(".phonecode-a").attr("obclick","sendSMSCode();");
                        clearInterval(timer);
                    }
                },1000,60)
            }else {
                alert(resp.errmsg);
                $(".phonecode-a").attr("onclick", "sendSMSCode();");
            }
    });


}

$(document).ready(function() {
    generateImageCode();
    $("#mobile").focus(function(){
        $("#mobile-err").hide();
    });
    $("#imagecode").focus(function(){
        $("#image-code-err").hide();
    });
    $("#phonecode").focus(function(){
        $("#phone-code-err").hide();
    });
    $("#password").focus(function(){
        $("#password-err").hide();
        $("#password2-err").hide();
    });
    $("#password2").focus(function(){
        $("#password2-err").hide();
    });

    //为表单的提交自定义的函数行为    (事件e)
    $(".form-register").submit(function(e){
        //阻止浏览器对表单默认提交行为
        e.preventDefault();

        mobile = $("#mobile").val();
        phoneCode = $("#phonecode").val();
        passwd = $("#password").val();
        passwd2 = $("#password2").val();
        if (!mobile) {
            $("#mobile-err span").html("请填写正确的手机号！");
            $("#mobile-err").show();
            return;
        } 
        if (!phoneCode) {
            $("#phone-code-err span").html("请填写短信验证码！");
            $("#phone-code-err").show();
            return;
        }
        if (!passwd) {
            $("#password-err span").html("请填写密码!");
            $("#password-err").show();
            return;
        }
        if (passwd != passwd2) {
            $("#password2-err span").html("两次密码不一致!");
            $("#password2-err").show();
            return;
        }
        //调用ajax向后端发送请求,防止重复校验
        var request_data = {
            mobile:mobile,
            sms_codes:phoneCode,
            password:passwd,
            password2:passwd2
        };
        var request_json=JSON.stringify(request_data);
        $.ajax({
            url:"/api/v1.0/users",
            type:"post",
            data:request_json,
            contentType:"application/json",
            dataType:"json",
            headers: {
                "X-CSRFToken": getCookie("csrf_token")
            }, // 请求头，将csrf_token值放到请求中，方便后端csrf进行验证
            success:function(resp){
                if (resp.error == "0"){
                    //注册成功跳转登录页面
                    location.href="/index.html";
                }else {
                    alert(resp.errmsg);
                }
            }
        })
    });
})