import json
import os
import random
from ltlf2dfa.parser.ltlf import LTLfParser, LTLfAnd, LTLfUntil, LTLfNot, LTLfAlways, LTLfAtomic, LTLfNext, LTLfOr, LTLfEventually, LTLfImplies, LTLfRelease
from multiprocessing import Pool
# 收集nuxmv timeout, unsat的
# 收集ltl model check认为unsat的
# 其余分为train/test/val

def preorder(f):
    if isinstance(f, LTLfAtomic):
        return f.s
    if isinstance(f, LTLfAnd) or isinstance(f, LTLfUntil) or isinstance(f, LTLfOr) or isinstance(f, LTLfRelease) or isinstance(f, LTLfImplies):
        result = f.operator_symbol
        tstrs=[preorder(f.formulas[i]) for i in range(len(f.formulas))]
        for i in tstrs:
            result += i
        return result
    if isinstance(f, LTLfNot) or isinstance(f, LTLfNext) or isinstance(f, LTLfAlways) or isinstance(f, LTLfEventually):
        result = f.operator_symbol
        result += preorder(f.f)
        return result

def ltl2prefix(ltl: str):
    parser = LTLfParser()
    formula = parser(ltl.replace('1', 'true').replace('0', 'false').replace('W','R'))
    return preorder(formula).replace('true', '1').replace('false', '0').replace('R', 'W')



def split(filenames,id):
    timeout_data = []  # nuxmve超时
    unsat_data = []  # nuxmv认为unsat
    dif_data = []  # 收集ltl model check认为unsat的
    normal_data= []
    cnt=0
    for fname in filenames:
        with open(fname,'r') as f:

            datas=json.load(f)
            # print('filaename:', fname,len(datas))

            # if cnt%10==0:

            for data in datas:
                cnt += 1
                if cnt%100 == 0:
                    print('\rcnt,', cnt,'\t\t',id, end='')
                if data.get('nuxmv_res',-1)!=-1:
                    if data['nuxmv_res']=='unsat':
                        unsat_data.append({'ltl':data['ltl'].strip(),'ltl_pre':data['ltl_pre']})
                    elif data['nuxmv_res']=='timeout':
                        timeout_data.append({'ltl':data['ltl'].strip(),'ltl_pre':data['ltl_pre']})
                else:
                    if data['ltl_check_res']=='unsat':
                        dif_data.append({'ltl':data['ltl'].strip(),'ltl_pre':data['ltl_pre'],'trace':data['trace']})
                    else:
                        normal_data.append({'ltl':data['ltl'].strip(),'ltl_pre':data['ltl_pre'],'trace':data['trace']})
    return timeout_data,unsat_data,dif_data,normal_data

if __name__=="__main__":


    floder='spot_random_raw'
    file_names=[]
    size_name='20t35'
    dataset_name='spot'
    for i in range(0,40):
        file_names.append(os.path.join(floder,'nltl%s%d.json'%(size_name,i)))

    pool = Pool(processes=1)
    result = []

    for i in range(1):
        result.append(pool.apply_async(split, ([file_names,i])))

    pool.close()
    pool.join()
    result = [x.get() for x in result]

    # timeout_data,unsat_data,dif_data,normal_data=split(file_names)
    timeout_data=[]
    unsat_data=[]
    dif_data=[]
    normal_data=[]
    for t_data,u_data,d_data,n_data in result:
        timeout_data+=t_data
        unsat_data+=u_data
        dif_data+=d_data
        normal_data+=n_data
    print('timeout',len(timeout_data),'unsat',len(unsat_data),'dif',len(dif_data),'normal',len(normal_data))
    random.shuffle(normal_data)


    # exit(0)
    # size_name=size_name.replace('t','-')

    with open('%s-%s-train.json'%(dataset_name,size_name),'w') as f:
        json.dump(normal_data[:800000],f)

    with open('%s-%s-test.json'%(dataset_name,size_name),'w') as f:
        json.dump(normal_data[800000:900000],f)

    with open('%s-%s-val.json'%(dataset_name,size_name),'w') as f:
        json.dump(normal_data[900000:1000000],f)

    with open('%s-%s-timeout.json'%(dataset_name,size_name),'w') as f:
        json.dump(timeout_data,f)
    with open('%s-%s-unsat.json'%(dataset_name,size_name),'w') as f:
        json.dump(unsat_data,f)
    with open('%s-%s-dif.json'%(dataset_name,size_name),'w') as f:
        json.dump(dif_data,f)