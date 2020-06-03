from django.shortcuts import render, redirect
from . import models
from . import forms
import hashlib
import datetime
from django.conf import settings

# 加密密码
def hash_code(s, salt='mysite'):# 加点盐
    h = hashlib.sha256()
    s += salt
    h.update(s.encode()) # update方法只接收bytes类型
    return h.hexdigest()

def make_confirm_string(user):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    code = hash_code(user.name, now)
    models.ConfirmString.objects.create(code=code, user=user,)
    return code

def send_email(email, code):
    from django.core.mail import EmailMultiAlternatives
    subject = '来自www.liujiangblog.com的注册确认邮件'

    text_content = '''感谢注册www.liujiangblog.com，这里是刘江的博客和教程站点，专注于Python、Django和机器学习技术的分享！\
                        如果你看到这条消息，说明你的邮箱服务器不提供HTML链接功能，请联系管理员！'''

    html_content = '''
                        <p>感谢注册<a href="http://{}/confirm/?code={}" target=blank>www.liujiangblog.com</a>，\
                        这里是刘江的博客和教程站点，专注于Python、Django和机器学习技术的分享！</p>
                        <p>请点击站点链接完成注册确认！</p>
                        <p>此链接有效期为{}天！</p>
                        '''.format('127.0.0.1:8000', code, settings.CONFIRM_DAYS)
    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
    msg.attach_alternative(html_content, 'text/html')
    msg.send()

def index(request):
    if not request.session.get('is_login', None):
        return redirect('/login/')
    return render(request, 'login/index.html')

def login(request):
    if request.session.get('is_login', None): # 不允许重复登录
        return redirect('/index/')
    if request.method == "POST":
        # get方法是Python字典类型的内置方法，它能够保证在没有指定键的情况下，
        # 返回一个None，从而确保当数据请求中没有username或password键时不会抛出异常
        # username = request.POST.get('username')
        # password = request.POST.get('password')
        login_form = forms.UserForm(request.POST)
        message = '请检查填写的内容！'
        if login_form.is_valid():
            # 验证成功后可以从表单对象的cleaned_data数据字典中获取表单的具体值；
            username = login_form.cleaned_data.get('username')
            password = login_form.cleaned_data.get('password')
        # if username.strip() and password: # 确保用户名和密码都不为空
            # 用户名字符合法性验证
            # 密码长度验证
            # 更多的其它验证.....
            try:
                user = models.User.objects.get(name=username)
            except:
                message = '用户不存在！'
                # message,这个数据字典在渲染模板的时候会传递到模板里供你调用。
                # return render(request, 'login/login.html', {'message': message})
                # locals() 函数，它返回当前所有的本地变量字典
                return render(request, 'login/login.html', locals())

            if not user.has_confirmed:
                message = '该用户未经过邮件确认！'
                return render(request, 'login/login.html', locals())

            if user.password == hash_code(password):
                # 往session字典内写入用户状态和数据：
                # 完全可以往里面写任何数据，不仅仅限于用户相关！
                request.session['is_login'] = True
                request.session['user_id'] = user.id
                request.session['user_name'] = user.name
                return redirect('/index/')
            else:
                message = '密码不正确！'
                return render(request, 'login/login.html', locals())
        else:
            return render(request, 'login/login.html',locals())
    login_form = forms.UserForm()
    return render(request, 'login/login.html', locals())

def register(request):
    if request.session.get('is_login', None):
        return redirect('/index/')
    if request.method == 'POST':
        register_form = forms.RegisterForm(request.POST)
        message = '请检查填写的内容！'
        if register_form.is_valid():
            username = register_form.cleaned_data.get('username')
            password1 = register_form.cleaned_data.get('password1')
            password2 = register_form.cleaned_data.get('password2')
            email = register_form.cleaned_data.get('email')
            sex = register_form.cleaned_data.get('sex')

            if password1 != password2:
                message = '两次输入的密码不同！'
                return render(request, 'login/register.html', locals())
            else:
                same_name_user = models.User.objects.filter(name=username)
                if same_name_user:
                    message = '用户名已存在！'
                    return render(request, 'login/register.html', locals())
                same_name_user = models.User.objects.filter(email=email)
                if same_name_user:
                    message = '该邮箱已经被注册了！'
                    return render(request, 'login/register.html', locals())

                new_user = models.User()
                new_user.name = username
                new_user.password = hash_code(password1)
                new_user.email = email
                new_user.sex = sex
                new_user.save()

                code = make_confirm_string(new_user)
                send_email(email, code)

                message = '请前往邮箱进行确认！'
                return redirect('/login/confirm.html', locals())
        else:
            return render(request, 'login/register.html', locals())
    register_form = forms.RegisterForm()
    return render(request, 'login/register.html')

def logout(request):
    if not request.session.get('is_login', None):
        # 如果本来就未登录，也就没有登出一说
        return redirect('/login/')
    request.session.flush()
    # 或者使用下面的方法
    # del request.session['is_login']
    # del request.session['user_id']
    # del request.session['user_name']
    return redirect('/login/')

def user_confirm(request):
    code = reqeust.GET.get('code', None) # 从请求的url地址中获取确认码;
    message = ''
    try:
        confirm = models.ConfirmString.objects.get(code=code) # 先去数据库内查询是否有对应的确认码;
    except:
        message = '无效的确认请求！'
        return render(request, 'login/confirm.html', locals())

    c_time = confirm.c_time
    now = datetime.datetime.now()
    if now > c_time + datetime.timedelta(settings.CONFIRM_DAYS):
        confirm.user.delete()
        message = '您的邮件已经过期！请重新注册！'
        return render(request, 'login/confirm.html', locals())
    else:
        confirm.user.has_confirmed = True
        confirm.user.save()
        confirm.delete()
        message = '感谢确认，请使用账户登录！'
        return render(request, 'login/confirm.html', locals())