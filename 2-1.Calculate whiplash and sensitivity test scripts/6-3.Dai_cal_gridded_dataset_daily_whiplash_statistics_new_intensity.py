# -*- coding: utf-8 -*-

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import scipy
from scipy import signal  
import os
from datetime import datetime
import pandas as pd
import tqdm
import multiprocessing
import gc


#%% -------------------------------------------基本参数---------------------------------------

#basic_dir='E:/research/4.East_Asia/Again/'
#basic_dir='/media/dai/disk2/suk/research/4.East_Asia/Again/'
#basic_dir='/scratch/xtan/suk/4.East_Asia/Again/'
basic_dir='/media/dai/suk_code/research/4.East_Asia/Again/'


basic_dai_dir='/media/dai/disk2/suk/research/4.East_Asia/Again/'




threshold=[0.05,0.1,0.15,0.2,0.25,0.75, 0.8,0.85,0.9,0.95]

MIN_period=[10,15,20,25,30,35,40,50,60,90]
MIN_period_sub=[20,25,30,35,40]

num=[np.linspace(1,35,35).astype(int)]
num.append(np.linspace(101,105,5).astype(int))
num=[j for i in num for j in i]

rcp85_start=86

#threshold_type = ['time_varying','series_mean','PIC_mean','calendar_mean']

extremes=['wet','dry','dry2wet','wet2dry']



preferred_dims = ('lat', 'lon', 'time') #需要调整为这种维度排序？

threshold_type=['Series_mean','Time_varying','Time_varying_standardized','Daily_SPI_proxy']



datasets=['CFSR','ERA5','MERRA2','NCEP2','JRA-55','MSWEP_V1.2', #6 reanalysis
'CHIRP','CHIRPS','PERSIANN', #3 satellite
'CPC','GPCC','REGEN_AllStns','REGEN_LongTermStns'] #4 grond-base land only

#%%#%%   -------------------------------  functions  -------------------------------

#th=1-q
#mth=0.05
#thres=b.sel(quantile= round(th+mth,2)).values


def cal_anom_quantile_Series_mean(var):
    global cum_prec

    j=var[0]
    k=var[1]
    day_cycle=pd.Series(cum_prec[:,j,k]).groupby(calendar_day).mean()
    sd=pd.Series(cum_prec[:,j,k]).groupby(calendar_day).std()
    anom_prec= (cum_prec[:,j,k]-np.tile(day_cycle,nyear))/np.tile(sd,nyear)
    quan_prec=anom_prec.quantile(threshold)
    return {'anom_prec':anom_prec.values,'quan_prec':quan_prec}


def rough_event_Series_mean(j):
    global Summary_Stats    
    a=Summary_Stats[j].get('anom_prec')
    b=Summary_Stats[j].get('quan_prec')
    
    dry_events=(a > b.sel(quantile= round(1-q,2)).values ).astype(float) #找出事件
    c = dry_events.cumsum()
    c[np.where(np.array(dry_events)!=0)]=np.nan
    c[0:(min_period-1)]=np.nan
    

    wet_events=(a < b.sel(quantile= q ).values  ).astype(float) 
    d = wet_events.cumsum()
    d[np.where(np.array(wet_events)!=0)]=np.nan
    d[0:(min_period-1)]=np.nan
    return {'dry_events':c,'wet_events':d}

def cal_anom_quantile_Time_varying(var):
    #global anom_prec,extreme_type,daily_event,quan_threshold

    j=var[0]
    k=var[1]
    day_cycle=pd.Series(cum_prec[:,j,k]).groupby(calendar_day).mean()
    #sd=pd.Series(cum_prec[:,j,k]).groupby(calendar_day).std()
    anom_prec= cum_prec[:,j,k]-np.tile(day_cycle,nyear)
    #quan_prec=pd.Series(anom_prec).groupby(year).quantile(threshold)
    quan_prec=anom_prec.groupby('time.year').quantile(threshold)
    return {'anom_prec':anom_prec.values,'quan_prec':quan_prec}




def rough_event_Time_varying(j):
    global Summary_Stats    
    a=Summary_Stats[j].get('anom_prec')
    b=Summary_Stats[j].get('quan_prec')

    dry_events=(a > np.repeat(b.sel(quantile= round(1-q,2)).values,365) ).astype(float) #找出事件
    c = dry_events.cumsum()
    c[np.where(np.array(dry_events)!=0)]=np.nan
    c[0:(min_period-1)]=np.nan
    

    wet_events=(a < np.repeat(b.sel(quantile=q ).values,365) ).astype(float) 
    d = wet_events.cumsum()
    d[np.where(np.array(wet_events)!=0)]=np.nan
    d[0:(min_period-1)]=np.nan
    return {'dry_events':c,'wet_events':d}


def cal_anom_quantile_Time_varying_standardized(var):
    #global anom_prec,extreme_type,daily_event,quan_threshold

    j=var[0]
    k=var[1]
    day_cycle=pd.Series(cum_prec[:,j,k]).groupby(calendar_day).mean()
    sd=pd.Series(cum_prec[:,j,k]).groupby(calendar_day).std()
    anom_prec= (cum_prec[:,j,k]-np.tile(day_cycle,nyear))/np.tile(sd,nyear)
    #quan_prec=pd.Series(anom_prec).groupby(year).quantile(threshold)
    quan_prec=anom_prec.groupby('time.year').quantile(threshold)
    return {'anom_prec':anom_prec.values,'quan_prec':quan_prec}


def rough_event_Time_varying_standardized(j):
    global Summary_Stats    
    a=Summary_Stats[j].get('anom_prec')
    b=Summary_Stats[j].get('quan_prec')
    
    dry_events=(a > np.repeat(b.sel(quantile= round(1-q,2)).values,365) ).astype(float) #找出事件
    c = dry_events.cumsum()
    c[np.where(np.array(dry_events)!=0)]=np.nan
    c[0:(min_period-1)]=np.nan
    
    wet_events=(a < np.repeat(b.sel(quantile=q ).values,365) ).astype(float) 
    d = wet_events.cumsum()
    d[np.where(np.array(wet_events)!=0)]=np.nan
    d[0:(min_period-1)]=np.nan
    return {'dry_events':c,'wet_events':d}


def cal_anom_quantile_Daily_SPI_proxy(var):
    #global anom_prec,extreme_type,daily_event,quan_threshold

    j=var[0]
    k=var[1]
    day_cycle=pd.Series(cum_prec[:,j,k]).groupby(calendar_day).mean()
    sd=pd.Series(cum_prec[:,j,k]).groupby(calendar_day).std()
    anom_prec= (cum_prec[:,j,k]-np.tile(day_cycle,nyear))/np.tile(sd,nyear)
    #quan_prec=pd.Series(anom_prec).groupby(year).quantile(threshold)
    quan_prec=(anom_prec.groupby('time').quantile(threshold))
    
    return {'anom_prec':anom_prec.values,'quan_prec':quan_prec}


def rough_event_Daily_SPI_proxy(j):
    global Summary_Stats    
    a=Summary_Stats[j].get('anom_prec')
    b=Summary_Stats[j].get('quan_prec')
    
    dry_events=(a > np.tile(b.sel(quantile= round(1-q,2)).values,nyear) ).astype(float) #找出事件
    c = dry_events.cumsum()
    c[np.where(np.array(dry_events)!=0)]=np.nan
    c[0:(min_period-1)]=np.nan
    

    wet_events=(a < np.tile(b.sel(quantile= q).values,nyear) ).astype(float) 
    d = wet_events.cumsum()
    d[np.where(np.array(wet_events)!=0)]=np.nan
    d[0:(min_period-1)]=np.nan
    return {'dry_events':c,'wet_events':d}



def cal_w_d_events(j):
    global Summary_Stats,Rough_Stats
    #global anom_prec,extreme_type,daily_event,quan_threshold

    #j=var[0]
    #k=var[1]
    '''
    if (thes_typ == 'Series_mean') | (thes_typ == 'Daily_SPI_proxy'):
        a=Summary_Stats[j].get('anom_prec')
    else :
        a=Summary_Stats[j].get('anom_prec').values
    '''
    a=Summary_Stats[j].get('anom_prec')
    
    #a=anom_prec[:,j,k].values
    b=Rough_Stats[j].get(extreme_type+'_events')
    
    
    if extreme_type=='dry':
        thres=Summary_Stats[j].get('quan_prec').sel(quantile= round(th+mth,2)).values
    else :
        thres=Summary_Stats[j].get('quan_prec').sel(quantile= round(1-th-mth,2)).values
  
        
    w_event=np.where(b>=0)[0] #存在事件的位置
    #w_interval=w_event[1:] - w_event[0:len(w_event)-1] #这里>1，则说明和前一个有[非事件]间隔
    w_interval=np.diff(w_event) #这里>1，则说明和前一个有[非事件]间隔
    w_ind_event_start=np.append(0,np.where(w_interval >1)[0]+1) #存在事件的位置里，每次独立事件开始的index
    where_independent_event_start=w_event[w_ind_event_start] #独立事件在整个序列里开始的index
    
    ##存在事件的位置里，每次独立事件结束的index，（第二行的条件为考虑没有持续，即仅单日的事件）
    w_ind_event_end=np.where(   ( (w_interval[:len(w_interval)-1]==1) & (w_interval[1:]!=1) ) \
                | ((w_interval[:len(w_interval)-1]!=1) & (w_interval[1:]!=1)) )[0]+1
    if w_interval[0]>1: #如果第一天是个单日事件，加上
        w_ind_event_end=np.append(0,w_ind_event_end)
        
    #加上最后一天    
    where_independent_event_end=np.append(w_event[w_ind_event_end],w_event[len(w_event)-1])
    
    #2.筛选出真正的独立事件（不独立的进行合并）
    '''
    #确定两场事件（开始时间）之间的时间间隔
    inter_arrival= np.diff(where_independent_event_start)
    #找到间隔≤我们所定义的搜索时间的事件（在where_independent_event_start中的index）
    w_start_depend=np.where(inter_arrival<=min_period)[0] #（实际为它的前一事件
    '''
    #确定前一场时间结束时间和后一场时间开始时间之间的间隔
    w_start_depend=np.where((where_independent_event_start[1:]-where_independent_event_end[0:-1])<=min_period )[0]
    
    c=b.copy()
    #如果两次独立事件之间间隔很短，考虑将其合并（原理为持续到下一次事件之前的平均SPI满足阈值）
    for i in range(len(w_start_depend)):
        #print(i)
        #i=3
        #两场间隔很短的独立事件
        #前一场的开始
        w_interarr_start=where_independent_event_start[w_start_depend[i]]
        #到后一场的前一天
        w_interarr_end=where_independent_event_start[w_start_depend[i]+1]
        #这段时间内的平均值≤阈值
        m=a[w_interarr_start:w_interarr_end].mean() #一开始算错，a[b:c]实际到c-1
        #print(m)
        
        if thes_typ == 'Series_mean':
            m_thres=thres
        elif thes_typ == 'Daily_SPI_proxy':
             #好像要注意这里跨了年份怎么办
            if (w_interarr_end%365 - w_interarr_start%365)<0:
                m_thres=np.append(thres[:w_interarr_end%365],thres[w_interarr_start%365:]).mean()
            else:
                m_thres=thres[w_interarr_start%365:w_interarr_end%365].mean()
        
        else:  
            m_thres=thres[int(np.floor(w_interarr_start/365))]
        
        if extreme_type == 'dry':
            if m <=  m_thres:
                #print(i)
                #前一场事件的开始 ：后一场事件的结束 都设置为前一场事件的number
                c[w_interarr_start:where_independent_event_end[w_start_depend[i]+1]+1 ]=c[w_interarr_start]
        elif extreme_type == 'wet':
            if m >=  m_thres:
                #print(i)
                #前一场事件的开始 ：后一场事件的结束 都设置为前一场事件的number
                c[w_interarr_start:where_independent_event_end[w_start_depend[i]+1]+1 ]=c[w_interarr_start]
      
    
    '''
    uni=np.unique(c)
    for i in range(len(uni)):
        c[c==uni[i]]=i
    '''
    #求事件的平均发生强度
    df = pd.DataFrame(np.vstack((c,a)).T)
    df.columns = ['index','spi']
    df_mean = df.groupby('index')['spi'].mean() 
    
    
    #找到一场事件的首尾
    w1=np.where( (c[1:]>=0) & (np.isnan(c[0:len(c)-1])) )[0] +1
    w2=np.where( (c[0:len(c)-1]>=0) & (np.isnan(c[1:])) )[0] 
    
    
    
    #如果最后一天存在事件，记得补上。
    if(c[-1]>=0):
        w2=np.append(w2,int(c[-1]))
    
    w=np.vstack((w1,w2,df_mean)).T
    
    # 删掉持续时间小于3天的
    a= np.where( (w2-w1)<3 )[0]
    for i in range(len(a)):
        c[w1[a[i]]:(w2[a[i]]+1) ]=np.nan
       
    #UNI_EVENT.append(np.float32(w)) #发生的时间
    
    #independent_event[:,j,k]=c
    return {'uni_event':np.float32(w[a,:]),'independent_event':c }



def cal_whiplash_events(j):
    global independent_dry,independent_wet
    #j=var
    
    
    '''
    if (thes_typ == 'Series_mean') | (thes_typ == 'Daily_SPI_proxy'):
        a=Summary_Stats[j].get('anom_prec')
    else :
        a=Summary_Stats[j].get('anom_prec').values
    '''
    a=Summary_Stats[j].get('anom_prec')
    
    
    independent_dry_bool=independent_dry[j].copy()
    independent_dry_bool[independent_dry_bool>=0]=1
    independent_dry_bool[np.isnan(independent_dry_bool)]=0
    
    independent_wet_bool=independent_wet[j].copy()
    independent_wet_bool[independent_wet_bool>=0]=2
    independent_wet_bool[np.isnan(independent_wet_bool)]=0
    


    e_s=independent_wet_bool+independent_dry_bool
    
    # 5.1 识别dry to wet 事件
    #识别dry事件的结束，即前一天为1（dry），后一天为0
    d_end=np.where( (np.diff(e_s)== -1)&(e_s[:-1]==1) )[0] 
    #识别出dry事件的结束和wet事件的开始的时间间隔
    dw_d_end=[] 
    dw_w_start=[]
    for i in range(len(d_end)):
        if (2 in e_s[d_end[i]:d_end[i]+inter_period+1]): #如果在dry事件的min_period时长内有wet事件
            
            dw_d_end.append(d_end[i])
            dw_w_start.append(d_end[i]+np.where(e_s[d_end[i]:d_end[i]+inter_period+1]==2)[0][0]) #找出首次出现的位置
    
    #cumu_start=a[dw_d_end]# 找出相应的SPI值
    #cumu_end=a[dw_w_start]
    
    
    bbb=pd.DataFrame(np.vstack((independent_dry[j],a)).T)
    bbb.columns = ['index','spi']
    bbb_min = bbb.groupby('index')['spi'].min() 
    bbb_dry_sum = bbb.groupby('index')['spi'].sum() 
    
    
    bbb=pd.DataFrame(np.vstack((independent_wet[j],a)).T)
    bbb.columns = ['index','spi']
    bbb_max = bbb.groupby('index')['spi'].max() 
    bbb_wet_sum = bbb.groupby('index')['spi'].sum() 
    
    cumu_start = bbb_min.get(independent_dry[j][dw_d_end])
    cumu_end = bbb_max.get(independent_wet[j][dw_w_start])
    
    cumu_start_sum = bbb_dry_sum.get(independent_dry[j][dw_d_end])
    cumu_end_sum = bbb_wet_sum.get(independent_wet[j][dw_w_start])
    #%
    
    d_to_w=np.vstack((dw_d_end,cumu_start,cumu_start_sum,dw_w_start,cumu_end,cumu_end_sum)).T
    #dry_to_wet.append(np.float32(d_to_w))
    #%
    # 5.2 识别wet to dry 事件
    #识别wet事件的结束，即前一天为2（wet），后一天为0
    w_end=np.where( (np.diff(e_s)== -2)&(e_s[:-1]==2) )[0] 
    #识别出dry事件的结束和wet事件的开始的时间间隔
    wd_w_end=[] 
    wd_d_start=[]
    for i in range(len(w_end)):
        if (1 in e_s[w_end[i]:w_end[i]+inter_period+1]): #如果在dry事件的min_period时长内有wet事件
            
            wd_w_end.append(w_end[i])
            wd_d_start.append(w_end[i]+np.where(e_s[w_end[i]:w_end[i]+inter_period+1]==1)[0][0]) #找出首次出现的位置
    
    #cumu_start=a[wd_w_end]# 找出相应的SPI值
    #cumu_end=a[wd_d_start]
    cumu_start = bbb_max.get(independent_wet[j][wd_w_end])
    cumu_end = bbb_min.get(independent_dry[j][wd_d_start])
    
    #w_to_d=np.vstack((wd_w_end,cumu_start,wd_d_start,cumu_end)).T
    
    
    cumu_start_sum = bbb_wet_sum.get(independent_wet[j][wd_w_end])
    cumu_end_sum = bbb_dry_sum.get(independent_dry[j][wd_d_start])
    #%
    w_to_d=np.vstack((wd_w_end,cumu_start,cumu_start_sum,wd_d_start,cumu_end,cumu_end_sum)).T
    
    
    
    #wet_to_dry.append(np.float32(w_to_d))
    return ({'wd':w_to_d,'dw':d_to_w})


#%%
result_dir = basic_dai_dir +'code_new/6-3.gridded_datasets_daily_whiplash_statistics/'  #硬盘不够位置了，拷在本机

#注意 181； 注意 2月29日 

n=7

all_plans=[]
for dtrd_typ in [1,2]:
    all_plans.append((dtrd_typ,'Series_mean',30,0.9))
for m in [20,25,35,40]:
    inter_period=np.ceil(m/2).astype(int)
    all_plans.append((2,'Series_mean',m,0.9))
for q in [0.8,0.95]: ##这俩不记得了
    all_plans.append((2,'Series_mean',30,q))       
for method in ['Daily_SPI_proxy','Time_varying','Time_varying_standardized']:
    all_plans.append((2,method,30,0.9))   
    
#%%

for plan in [1]:
    
    Dtrd_typ=all_plans[plan][0]
    Thes_typ=all_plans[plan][1]
    Min_period=all_plans[plan][2]
    Q=all_plans[plan][3]
   
    
    for n in range(len(datasets)):
        
        #1. 创建每个ensemble一个的文件夹，以防一个文件夹里面装过多东西
        if os.path.exists(result_dir+datasets[n]+'/')==False:
            os.makedirs(result_dir+datasets[n]+'/')
        method_dir=result_dir+datasets[n]+'/'
        
        print('dataset='+datasets[n])
        print(datetime.now())
        
        
        #2. 读入降水数据
        data=xr.open_dataarray( basic_dir+  'data/combined_gridded_prcp/'+datasets[n]+'_daily_prcp.nc'  ).sel(time=slice('1979-01-01','2020-12-31') )
    
        print('inputed data:'+str(datetime.now() ))
        
        ##去除掉2月29日
        data=data.drop_sel(time= data.time[(data['time.month']==2 ) & (data['time.day']==29 )])
        
        #3. 保存原始日期和calendar日
        original_time=data.time
        month=data['time.month'].values
        day=data['time.day'].values
        year=data['time.year'].values
        calendar_day=[str(month[i]).zfill(2)+'-'+str(day[i]).zfill(2) for i in range(len(month))]
        
        nyear=len(np.unique(data['time.year'].values))
        
        #1,求不同历时的情况
    
        for dtrd_typ in [Dtrd_typ]: #不去趋势 #linear #二阶趋势 #多模型平均进行缩放
            print('detrend_method='+str(dtrd_typ))
            #dtrd_typ=2
            #dtrd_typ=1
            if dtrd_typ ==1:
                data1=data.copy(deep=True)
           
            if dtrd_typ ==2:
                
                
                data_year=data.groupby('time.year').mean()
                #已经在去趋势的时候仅仅保留了1979年以后的
                data_year_dtrd=xr.open_dataarray(basic_dir + 'code/4-2.gridded_dataset_annual_ensemble_mean_prec/PRECT_annual_mean_'+datasets[n]+'_detrend1.nc')
                data1 =data.groupby('time.year')-(data_year-data_year_dtrd) #可能会出现负值但好像不影响
           
                
            print('detrend done ! ') 
            
            #min_period=30
            for min_period in [Min_period]:
                
                print('min_period='+str(min_period))
                
                start=datetime.now()
                
                cum_prec=data1.rolling(time=min_period,center=False).sum()
                #cum_prec=cum_prec.assign_coords({'time':calendar_day})
                
                end=datetime.now()
                print('spend cal cum_prec:'+str(end-start))
                #del(data)  ##内存不够了！
                    
                input_combo=[]
                for j in range(cum_prec.shape[1]):
                    for k in range(cum_prec.shape[2]):
                        #input_combo.append((j,k))
                        
                        if cum_prec[:,j,k].sum()!=0:
                            input_combo.append((j,k))
                        
                len_input_combo = []
                for j in range(len(input_combo)):
                    len_input_combo.append(j)
                
                
                for thes_typ in [Thes_typ] :
                    #thes_typ='Series_mean'
                    #thes_typ='Daily_SPI_proxy'
                    #thes_typ='Time_varying'
                    #thes_typ='Time_varying_standardized'
                    #%
                    #获得不同方法下的降水异常和事件
                    start=datetime.now()
                    if thes_typ=='Daily_SPI_proxy':
                        cum_prec=cum_prec.assign_coords({'time':calendar_day})
                   
                    pool = multiprocessing.Pool(processes = 48) # object for multiprocessing
                    Summary_Stats = list(tqdm.tqdm(pool.imap( globals()['cal_anom_quantile_'+thes_typ] , input_combo), 
                                                   total=len(input_combo), position=0, leave=True))
                    pool.close()    
                    del(pool)
                    gc.collect()
                    
                    end=datetime.now()
                    print('spend cal anom and quan:'+str(end-start)) # about 5 mins 
                    
                 
                    
                    for q in [Q]:
                        #print('q='+str(q))
                        #q=0.9
                        # 10. 得到粗糙的事件
                        start=datetime.now()
                        
                        #注意日期类型？
                        ### 要注意！！我们这里所用的方法是要反过来求0 和 1 的！
                        
                        pool = multiprocessing.Pool(processes = 48) # object for multiprocessing
                        Rough_Stats = list(tqdm.tqdm(pool.imap( globals()['rough_event_'+thes_typ], len_input_combo), 
                                                       total=len(len_input_combo), position=0, leave=True))
                        pool.close()    
                        del(pool)
                        gc.collect()
    
                        
                        end=datetime.now()
                        print('spend cal rough wet and dry event indexs:'+str(end-start)) #about   11 mins !!!!
                        
                        
                        
                        th= round(1-q,2)
                        
                        
                        #### 衔接阈值为多少差别不会很大（但是当极端值为0.8的时候，可能差别会比较大）
                        for mth in [0.05]:
                            #mth=0.05
                            
                            
                         
                          
                            print('cal dry and wet events')
                            #independent_event=np.zeros(shape=daily_event.shape)
                            #UNI_EVENT=[]
    
                            extreme_type='dry'
                            
                            pool = multiprocessing.Pool(processes = 24) # object for multiprocessing
                            Summary_Stats_dry = list(tqdm.tqdm(pool.imap(cal_w_d_events, len_input_combo), 
                                                           total=len(len_input_combo), position=0, leave=True))
                            pool.close()
                            del(pool)
                            gc.collect()
                            
                            #################################
                            extreme_type='wet'
                      
                            pool = multiprocessing.Pool(processes = 24) # object for multiprocessing
                            Summary_Stats_wet = list(tqdm.tqdm(pool.imap(cal_w_d_events, len_input_combo), 
                                                           total=len(len_input_combo), position=0, leave=True))
                            pool.close()
                            del(pool)
                            
                            
                            UNI_DRY=[]
                            for j in range(len(input_combo)):
                                UNI_DRY.append(Summary_Stats_dry[j].get('uni_event'))
                            
                            UNI_WET=[]
                            for j in range(len(input_combo)):
                                UNI_WET.append(Summary_Stats_wet[j].get('uni_event'))
                            
                            
                            #储存其属性
                            np.save(method_dir+'dry_'+thes_typ+'_detrend_'+str(dtrd_typ)+'_of_'+str(min_period)+'_days'+
                                    '_quantile_'+str(round((1-th),2))+'.npy',UNI_DRY)
    
                            np.save(method_dir+'wet_'+thes_typ+'_detrend_'+str(dtrd_typ)+'_of_'+str(min_period)+'_days'+
                                    '_quantile_'+str(round((1-th),2))+'.npy',UNI_WET)
                           
                            del(UNI_WET)
                            del(UNI_DRY)
    
                            print('cal whiplash events')
                            independent_dry=[]
                            for j in range(len(input_combo)):
                                independent_dry.append(Summary_Stats_dry[j].get('independent_event'))
                            
                            
                            independent_wet=[]
                            for j in range(len(input_combo)):
                                independent_wet.append(Summary_Stats_wet[j].get('independent_event'))
                                
                                
                            del(Summary_Stats_dry)
                            del(Summary_Stats_wet)
                            
                            
                            for ip in [1,2,3]:
                                inter_period=np.ceil(min_period/ip).astype(int)
                                
                                pool = multiprocessing.Pool(processes = 24) # object for multiprocessing
                                Summary_Stats_whiplash = list(tqdm.tqdm(pool.imap(cal_whiplash_events, len_input_combo ), 
                                                               total=len(len_input_combo), position=0, leave=True))
                                pool.close()
                                del(pool)
                                gc.collect()
                                
                                dry_to_wet=[]
                                for j in range(len(input_combo)):
                                    dry_to_wet.append(Summary_Stats_whiplash[j].get('dw'))
                                
                                wet_to_dry=[]
                                for j in range(len(input_combo)):
                                    wet_to_dry.append(Summary_Stats_whiplash[j].get('wd'))
                                
                                
                                np.save(method_dir+'dry_to_wet_'+thes_typ+'_detrend_'+str(dtrd_typ)+'_of_'+str(min_period)+'_days'+
                                        '_quantile_'+str(round((1-th),2))+'_inter_period_'+str(inter_period)+'.npy',dry_to_wet)
                                np.save(method_dir+'wet_to_dry_'+thes_typ+'_detrend_'+str(dtrd_typ)+'_of_'+str(min_period)+'_days'+
                                        '_quantile_'+str(round((1-th),2))+'_inter_period_'+str(inter_period)+'.npy',wet_to_dry)
                            
                                del(Summary_Stats_whiplash)
                                del(dry_to_wet)
                                del(wet_to_dry)
                            del(independent_wet)
                            del(independent_dry)                        
                        del(Rough_Stats)
                        gc.collect()
                    del(Summary_Stats)
                    gc.collect()
                del(cum_prec)
                gc.collect()
        del(data)
        gc.collect()
