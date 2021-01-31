function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

$(document).ready(function() {
    $("#mobile").focus(function(){
        $("#mobile-err").hide();
    });
    $("#password").focus(function(){
        $("#password-err").hide();
    });
    $(".form-login").submit(function(e){
        e.preventDefault();
        mobile = $("#mobile").val();
        passwd = $("#password").val();
        if (!mobile) {
            $("#mobile-err span").html("请填写正确的手机号！");
            $("#mobile-err").show();
            return;
        } 
        if (!passwd) {
            $("#password-err span").html("请填写密码!");
            $("#password-err").show();
            return;
        }

        //调用ajax向后端发送请求,防止重复校验
        var data = {
            mobile:mobile,
            password:passwd
        };
        var request_json=JSON.stringify(data);
        $.ajax({
            url:"/api/v1.0/login",
            type:"post",
            data:request_json,
            contentType:"application/json",
            dataType:"json",
            headers: {
                "X-CSRFToken": getCookie("csrf_token")
            }, // 请求头，将csrf_token值放到请求中，方便后端csrf进行验证
            success:function(resp){
                if (resp.error == "0"){
                    //注册成功跳转主页面
                    location.href="/";
                }else {
                     //其他错误信息,在页面中展示
                     $(".password-err span").html(resp.errmsg);
                     $(".password-err").show();
                     alert(resp.errmsg);
                }
            }
        })

    });
})