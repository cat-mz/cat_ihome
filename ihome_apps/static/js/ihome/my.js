function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

// 点击推出按钮时执行的函数
function logout() {
    $.ajax({
        url: "/api/v1.0/login",
        type: "delete",
        headers: {
            "X-CSRFToken": getCookie("csrf_token")
        },
        dataType: "json",
        success: function (resp) {
            if ("0" == resp.error) {
                location.href = "/index.html";
            }
        }
    });
}

$(document).ready(function(){
    $.get("/api/v1.0/users/messages", function(resp){
        // 用户未登录
        if ("4101" == resp.error) {
            location.href = "/login.html";
        }
        // 查询到了用户的信息
        else if ("0" == resp.error) {
            $("#user-name").html(resp.data.name);
            $("#user-mobile").html(resp.data.mobile);
            if (resp.data.avatar_uri) {
                $("#user-avatar").attr("src", resp.data.avatar_uri);
            }

        }
    }, "json");

})