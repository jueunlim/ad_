import pandas as pd
from soynlp.normalizer import *
import numpy as np

# load history raw file
h1=pd.read_pickle('./all_history.pkl')

h1.pj_name

h1.활동.unique()
print(h1.shape)


# 전처리 시작
# delete row
del_act=['광고 이름 업데이트됨','캠페인 상태 업데이트됨','광고 세트 생성됨','라이브러리에 이미지가 추가됨','라이브러리에서 이미지가 수정됨',
         '캠페인이 생성됨','캠페인 이름 업데이트됨','광고 세트 일정 업데이트됨','사용자가 계정에서 삭제됨','사용자가 계정에 추가됨',
         '맞춤 타겟이 삭제됨','광고 검토 완료 후 광고 상태 업데이트됨','맞춤 타겟 생성됨','광고 세트 이름 업데이트됨','광고 세트 상태 업데이트됨',
         '광고 세트 최적화 목표 업데이트됨','캠페인 지출 한도 업데이트됨']

# 광고 세트 상태 업데이트됨 -> 이게 타겟 별로 광고 세트를 나눈경우 비활성화는 타겟조정에 해당되는데 아직 미처리(예외경우)
# 광고 세트 최적화 목표 업데이트됨 ->  캠페인 kpi(운영옵션)를 바꾸는 경우 미처리 (예외 경우로 판단되며 , 어떤 경우인지 이유 파악 필요)
# 캠페인 지출 한도 업데이트됨 -> ex. 무제한-> ₩40,000,000 (예외경우)

filter_row=[idx for idx, act in enumerate(h1['활동']) if act not in del_act]
h1=h1.iloc[filter_row,:]
h1.loc[h1.활동=='광고가 생성됨','활동 상세 정보']='-'
h1=h1.fillna('-')
h1=h1.loc[~h1['활동 상세 정보'].str.contains('null',na=False),:] #setting단계 히스토리 제외



h1['활동 상세 정보']=h1['활동 상세 정보'].str.replace(r'[-=+,/<>\n;:^#?$.@*\"※~&%ㆍ!』\\‘|\(\)\[\]\<\>`\'…》◀▶●■★◆]', '')
h1['변경된 항목']=h1['변경된 항목'].str.replace(r'[-=+,/<>\n;:^#?$.@*\"※~&%ㆍ!』\\‘|\(\)\[\]\<\>`\'…》◀▶●■★◆]', '')

h1=h1.reset_index().iloc[:,1:]


# 원하는 데이터 형태로 변환
#원하는 칼럼 형식
# cam_id : 매체 캠페인 아이디
# pj_name : 프로젝트 이름
# cam_name : 매체 캠페인명
# adset_id
# ad_id
# kpi,
#monitoring_time : 추후에 api랑 매칭시켜야함.
# change_option : 변경옵션(소재, 일일예산, 타겟)
# change_action : 소재추가, 소재off / 감액, 증액 /유사타겟설정, 타겟조정
# change_action_detail : 변경상세내용(소재-소재off,소재추가, 소재변경 / 일일예산-감액,증액 / 타겟-유사타겟설정,타겟조정)
# action_time : h1.날짜 및 시간

from collections import OrderedDict
result = []


cols = list(h1.columns)
for _,row in h1.iterrows():
    df_dict = OrderedDict()
    for col in cols:
        df_dict[col] = row[col]

# case1. 활동 : 캠페인 예산이 업데이트됨
    if (row['활동']=='캠페인 예산이 업데이트됨' or row['활동']=='광고 세트 예산 업데이트됨'):
        if '일일' in row['활동 상세 정보']:
            df_dict['change_option']='일일예산'
        else:
            df_dict['change_option']='총예산'

        money_list=[]
        for a in list(row['활동 상세 정보'].split('변경 후')):
            money_list.append(''.join(re.findall('[0-9]',a)))
        try:
            if int(money_list[0])-int(money_list[1])<0:
                df_dict['change_action']='증액'
                df_dict['change_action_detail']=row['활동 상세 정보']
            else:
                df_dict['change_action']='감액'
                df_dict['change_action_detail']=row['활동 상세 정보']
        except:
            print(money_list)


#  case2. 활동 : 광고 상태 업데이트됨->활동 상세 정보-> 활성 에서 비활성
    elif row['활동']=='광고 상태 업데이트됨':
        if '활성 에서 비활성' in row['활동 상세 정보']:
            df_dict['change_option']='소재'
            df_dict['change_action']='소재off'
            df_dict['change_action_detail']='-'
        else:
            df_dict['change_option']='-'
            df_dict['change_action']='-'
            df_dict['change_action_detail']='-'

#  case3. 활동 : 광고가 생성됨
    elif row['활동']=='광고가 생성됨':
        df_dict['change_option']='소재'
        df_dict['change_action']='소재추가' #(처음 광고가 게재될 때 광고가 생성되는건 제외할 수 있는 기준 필요)
        df_dict['change_action_detail']='-'

#  case4. 활동 : 광고가 업데이트됨 -> 광고변경
    elif row['활동']=='광고가 업데이트됨':
        df_dict['change_option']='소재'
        df_dict['change_action']='소재변경'
        df_dict['change_action_detail']=row['활동 상세 정보']


#  case5. 활동 : 광고 세트 타게팅 업데이트됨 -> 타겟
    elif row['활동']=='광고 세트 타게팅 업데이트됨' :
        if '전변경' not in row['활동 상세 정보']:
            df_dict['change_option']='타겟'
            df_dict['change_action']='타겟조정'
            df_dict['change_action_detail']=row['활동 상세 정보']

        else:
            if '유사' in row['활동 상세 정보']:
                df_dict['change_option']='타겟'
                df_dict['change_action']='유사타겟설정'
                df_dict['change_action_detail']=row['활동 상세 정보']

            else: #처음 setting값은 제외
                df_dict['change_option']='-'
                df_dict['change_action']='-'
                df_dict['change_action_detail']='-'

    result.append(df_dict)
print('----preprocessing 완료 : %i 개----' %len(result))


result_df = pd.DataFrame(result)
result_df=result_df.loc[result_df['change_option']!='-',:] #change_option이 존재하지 않는('-') row delete
result_df.rename(columns={'날짜 및 시간':'action_time'})
result_df.to_pickle('./all_pp_history.pkl')


