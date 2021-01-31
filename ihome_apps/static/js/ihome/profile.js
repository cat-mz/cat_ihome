function showSuccessMsg() {
    $('.popup_con').fadeIn('fast', function() {
        setTimeout(function(){
            $('.popup_con').fadeOut('fast',function(){}); 
        },1000) 
    });
}

function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}


$(document).ready(function () {
    $("#form-avatar").submit(function (e) {
        // 阻止表单的默认行为
        e.preventDefault();
        // 利用jquery.form.min.js提供的ajaxSubmit对表单进行异步提交
        $(this).ajaxSubmit({
            url: "/api/v1.0/users/avatar",
            type: "post",
            dataType: "json",
            headers: {
                "X-CSRFToken": getCookie("csrf_token")
            },
            success: function (resp) {
                if (resp.error == "0") {
                    // 上传成功
                    var avatarUrl = resp.data.avatar_url;
                    $("#user-avatar").attr("src", avatarUrl);
                } else if (resp.error == "4101") {
                    location.href = "/login.html";
                } else {
                    alert(resp.errmsg);
                }
            }
        })
    });

    // 在页面加载是向后端查询用户的信息
    $.get("/api/v1.0/users", function(resp){
        // 用户未登录
        if ("4101" == resp.error) {
            location.href = "/login.html";
        }
        // 查询到了用户的信息
        else if ("0" == resp.error) {
            $("#user-name").val(resp.data.name);
            if (resp.data.avatar) {
                $("#user-avatar").attr("src", resp.data.avatar);
            }
        }
    }, "json");


    $("#form-name").submit(function(e){
        // 阻止表单的默认行为
        e.preventDefault();
        var name=$("#user-name").val();
        var data_cat={
            name:name
        }
        var data_cat01=JSON.stringify(data_cat);
        $.ajax({
            url:"/api/v1.0/users/name",
            type:"post",
            dataType:"json",
            contentType:"application/json",
            data:data_cat01,
            headers: {
                "X-CSRFToken": getCookie("csrf_token")
            },
            success:function(resp){
                if (resp.error == "0"){
                    $(".error-msg").hide();
                    showSuccessMsg();
                }else if (resp.error == "4101"){
                    location.href = "/login.html";
                }else if (resp.error == "4003"){
                    $(".error-msg").show();
                }else {
                    alert(resp.errmsg);
                }
            }
        });
    });

})
