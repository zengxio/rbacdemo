from django.shortcuts import render,redirect,HttpResponse
from rbac.service import initial_permission
from web import models
import datetime
# Create your views here.
def login(request):
    if request.method=="GET":
        return render(request,'login.html')
    else:
        u=request.POST.get('username')
        p=request.POST.get('password')
        obj=models.UserInfo.objects.filter(user__username=u,user__password=p).first()
        if obj:
            request.session['user_info']={'username':u,'nickname':obj.nickname,'nid':obj.id}
            initial_permission(request,obj.user_id)
            return redirect('/index.html')
        else:
            return render(request,'login.html')

def index(request):
    if not request.session.get('user_info'):
        return redirect('/login.html')
    return render(request,'index.html')

def trouble(request):
    if request.permission_code=="LOOK":
        trouble_list=models.Order.objects.filter(create_user_id=request.session['user_info']['nid'])
        return render(request,'trouble.html',{'trouble_list':trouble_list})

    elif request.permission_code=="DEL":
        nid=request.GET.get('nid')
        models.Order.objects.filter(create_user_id=request.session['user_info']['nid'],id=nid).delete()
        return redirect('/trouble.html')
    elif request.permission_code=="POST":
        if request.method=="GET":
            return render(request,'trouble_add.html')
        else:
            title=request.POST.get('title')
            content=request.POST.get('content')
            models.Order.objects.create(title=title,detail=content,create_user_id=request.session['user_info']['nid'])
            return redirect('/trouble.html')

    elif request.permission_code=="EDIT":
        if request.method=="GET":
            return render(request,'trouble_edit.html')
        else:
            title=request.POST.get('title')
            content=request.POST.get('content')
            models.Order.objects.create(title=title,detail=content,create_user_id=request.session['user_info']['nid'])
            return redirect('/trouble.html')

from django.db.models import Q

def trouble_kill(request):
    nid=request.session['user_info']['nid']
    if request.permission_code=="LOOK":
        #查看列表，未解决，当前用户已经解决的。或者正在解决
        trouble_list=models.Order.objects.filter(Q(status=1)|Q(processor_id=nid)).order_by('status')
        return render(request,'trouble_kill_look.html',{'trouble_list':trouble_list})
    elif request.permission_code=="EDIT":
        if request.method=="GET":
            order_id=request.GET.get("nid")
            #已经抢到了
            if models.Order.objects.filter(id=order_id,processor_id=nid,status=2):
                #抢到未处理
                obj = models.Order.objects.filter(id=order_id).first()
                return render(request, 'trouble_kill_edit.html', {'obj': obj})
            #开始抢
            res=models.Order.objects.filter(id=order_id,status=1).update(processor_id=nid,status=2)
            if not res:
                return HttpResponse("手慢无")
            else:
                obj=models.Order.objects.filter(id=order_id).first()
                return render(request,'trouble_kill_edit.html',{'obj':obj})
        else:
           order_id=request.GET.get("nid")
           solution=request.GET.get("solution")
           models.Order.objects.filter(id=order_id,processor_id=nid).update(status=3,solution=solution,ptime=datetime.datetime.now())
           return redirect("/trouble-kill.html")

import json
from django.db.models import Count

def report(request):
    if  request.permission_code=="LOOK":
        # models.Order.objects.filter(status=3).extra(select={'ymd':'strftime(%%Y-%%m-%%d,ptime)'}).values('processor_id','ymd').annotate(ct=Count("id")) #日期格式化
        # models.Order.objects.filter(status=3).extra(select={'ymd':'strftime(%%s,ptime)'}).values('processor_id','ymd').annotate(ct=Count("id"))  #时间戳

        #获取每个人处理个数
        if request.method=="GET":
            return render(request,'report.html')
        else:

            result=models.Order.objects.filter(status=3).values_list('processor__nickname').annotate(ct=Count("id"))

            ymd_list=models.Order.objects.filter(status=3).extra(
                select={'ymd': "strftime('%%s',strftime('%%Y-%%m-%%d',ptime))"}).values(
                'processor_id', 'processor__nickname', 'ymd').annotate(ct=Count("id"))
            ymd_dict={}
            for row in ymd_list:
                key=row['processor_id']
                if key in ymd_dict:
                    ymd_dict[key]['data'].append([float(row['ymd'])*1000,row['ct']])
                else:
                    ymd_dict[key]={'name':row['processor__nickname'],'data':[[float(row['ymd'])*1000,row['ct']]]}

            response={
                #饼图
                'pie':[
                    ['方少伟',45.0],
                    ['吴永强',40.0],
                    ['由秦兵',3.0],
                    ['尹树林',90.0]
                ],
                #折线图
                'zhexian':list(ymd_dict.values())


            }
            return HttpResponse(json.dumps(response))
