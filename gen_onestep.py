# -*- coding:utf-8 -*-
import os
import sys
import subprocess
import queue
import json
from copy import deepcopy
import time
import timeout_decorator
import argparse
from ltlf2dfa.parser.ltlf import LTLfParser, LTLfAnd, LTLfUntil, LTLfNot, LTLfAlways, LTLfAtomic, LTLfNext, LTLfOr, LTLfEventually, LTLfImplies, LTLfRelease
from ltl_model_check_proof import check
from ltl_model_check_proof import get_switch_cnt
import signal
from multiprocessing import Pool
from queue import Queue

TIME_LIMIT=60
# trace->list
def trace2list(trace:str):
    trace=trace.split(';')
    loop_start=-1
    for i in range(0,len(trace)):
        if '{' in trace[i]:
            loop_start=i
        tstr=trace[i].replace('&','').replace('{','').replace('}','')
        trace[i]=[j for j in tstr]
    return trace,loop_start

#list->trace
def list2trace(trace, loop_start):
    retstr=''
    cnt=0
    for state in trace:
        if cnt!=0:
            retstr+=';'
        if cnt==loop_start:
            retstr+='{'
        for i in range(len(state)-1):
            retstr+='&'
        for var in state:
            retstr+=var
        cnt+=1
    retstr+='}'
    return retstr


def get_sub_trace(ori_trace,key):
    ori_trace,loop_start=trace2list(ori_trace)
    new_trace=ori_trace[key[0]:]
    if key[0]>loop_start:
        new_trace+=ori_trace[loop_start:key[0]]
        new_loop_start=0
    else:
        new_loop_start=loop_start-key[0]
    new_trace=list2trace(new_trace,new_loop_start)
    return new_trace

def get_sub_data(ori_trace,ori_ltl_pre,father_key,son_key_list):
    # print('father',father_key)
    # print('son',son_key_list)
    father_ltl_pre=ori_ltl_pre[father_key[1]:father_key[2]+1]
    father_trace=get_sub_trace(ori_trace,father_key)
    src="%s,%s,%d"%(father_ltl_pre,father_trace,father_key[3])

    end_formula="@"
    if len(son_key_list)==0:
        tgt="@,@,@#@,@,@"
        return src,tgt

    son_ltl_pre=ori_ltl_pre[son_key_list[0][1]:son_key_list[0][2]+1]
    son_trace=get_sub_trace(ori_trace,son_key_list[0])
    tgt="%s,%s,%d"%(son_ltl_pre,son_trace,son_key_list[0][3])
    if len(son_key_list)==2:
        son_ltl_pre = ori_ltl_pre[son_key_list[1][1]:son_key_list[1][2] + 1]
        son_trace = get_sub_trace(ori_trace, son_key_list[1])
        tgt+="#%s,%s,%d"%(son_ltl_pre,son_trace,son_key_list[1][3])
    else:
        tgt+="#@,@,@"
    return src,tgt

def get_proof(data_s):
    vocab = [i for i in 'abcdefghij']
    vocab = set(vocab)

    ret_data=[]
    formula_turples=[]
    cnt=0
    for data in data_s:
        cnt+=1
        # print('??cnt',cnt)
        if cnt%100==0:
            print('\r',cnt,end='')
        proof_list = []
        v, root_node, proof_dic, pair_set, formula_turple = check(data['ltl'], data['trace'], vocab)
        formula_turples.append(formula_turple)
        que = Queue()
        que.put(root_node)
        visited = set()
        visited.add(root_node)
        # proof_list.append(root_node)
        while not que.empty():
            cur_node = que.get()
            cur_list = proof_dic.get(cur_node, -1)
            if cur_list != -1:
                for son in cur_list:
                    proof_list.append((son, cur_node))
                    if son in visited:
                        continue
                    else:
                        que.put(son)
                        visited.add(son)

        data['proof']=list(proof_list)
        ret_pair=[0]*len(pair_set)
        for i in pair_set:
            ret_pair[i[0]]=i[1]
        # data['tgt']=data['trace']+'#'
        # for node in proof_list:
        #     data['tgt']+="%d,%d,%d,%d]"%(node[0],node[1][0],node[1][1],node[2])
        data['pair_set']=ret_pair
        ret_data.append(data)



    new_data=[]
    empty_formula='$'
    switch_cnt={}
    switch_cnt_sum=0
    cnt=-1
    for data in ret_data:
        cnt+=1
        new_data.append({
                         'src':'%s,%s,1'%(data['ltl_pre'],empty_formula),
                         'tgt':'%s,%s,1#@,@,@'%(data['ltl_pre'],data['trace'])}) #'ltl_pre':data['ltl_pre'],'trace':data['trace'],
        #
        if testset==1:
            new_data[-1]['ltl']=data['ltl']
            continue
        sub_formula_set={}
        for edge in data['proof']:
            son_key=(edge[0][0],edge[0][1][0],edge[0][1][1],edge[0][2])
            father_key=(edge[1][0],edge[1][1][0],edge[1][1][1],edge[1][2])
            if father_key not in sub_formula_set.keys():
                sub_formula_set[father_key]=[]
            if son_key not in sub_formula_set.keys():
                sub_formula_set[son_key] = []
            sub_formula_set[father_key].append(son_key)
            sub_formula_set[father_key].sort(key=lambda x:(x[1],x[2]))
            assert (len(sub_formula_set[father_key])<=2)

        for father_key in sub_formula_set.keys():

            if data['ltl_pre'][father_key[1]] in vocab and len(sub_formula_set[father_key])>=1:
                f=open('error','w')
                print('error:',data['ltl_pre'],father_key,sub_formula_set[father_key],file=f)
                print(data['ltl'],file=f)
                print(formula_turples[cnt],file=f)
                for k in sub_formula_set.keys():
                    print(k,sub_formula_set[k],file=f)
                f.close()
                # exit(1)
            if len(sub_formula_set[father_key])>=1:
                if len(sub_formula_set[father_key])==1:
                    key="operator:%s,son_len:%d,ori:%d,right:%d,expect:%d"%(data['ltl_pre'][father_key[1]],
                                                          len(sub_formula_set[father_key]),
                                                          father_key[1]==sub_formula_set[father_key][0][1],
                                                          father_key[2]==sub_formula_set[father_key][0][2],
                                                          father_key[3])
                else:
                    key="operator:%s,son_len:%d,s1ori:%d,s1right:%d,s2ori:%d,s2right:%d,expect:%d"%(data['ltl_pre'][father_key[1]],
                                                          len(sub_formula_set[father_key]),
                                                          father_key[1]==sub_formula_set[father_key][0][1],
                                                          father_key[2]==sub_formula_set[father_key][0][2],
                                                          father_key[1]==sub_formula_set[father_key][1][1],
                                                          father_key[2]==sub_formula_set[father_key][1][2],
                                                          father_key[3])
            else:
                key="atomic proposition"
            if switch_cnt.get(key,-1)==-1:
                switch_cnt[key]=1
            else:
                switch_cnt[key]+=1
            switch_cnt_sum+=1

            src,tgt=get_sub_data(data['trace'],data['ltl_pre'],father_key,sub_formula_set[father_key])
            new_data.append({'src':src,'tgt':tgt,'key':key}) #

    print('return')
    return (new_data,switch_cnt)


if __name__ == "__main__":




    parser = argparse.ArgumentParser(description='Main script for active learning')
    parser.add_argument('-f', type=str, required=False ,default='randltls', help='input file containing ltls')
    parser.add_argument('-o', type=str, required=True, help='output file')
    parser.add_argument('--test', type=int, required=False, default=0, help='output file')
    parser.add_argument('-t', type=int, required=False, default=40, help='thread number')
    parser.add_argument('-s', type=int, required=False, default=100000, help='size')
    parser.add_argument('-b', type=int, required=False, default=0, help='balance data')

    args = parser.parse_args()
    infile=args.f
    ofile=args.o
    testset=args.test
    balance=args.b


    f=open(infile,'r')
    data_s=json.load(f)
    f.close()

    pool = Pool(processes=args.t)

    job_size=args.s//args.t
    result = []
    for i in range(args.t):
        result.append(pool.apply_async(get_proof, ([data_s[i*job_size:(i+1)*job_size]])))
    pool.close()
    pool.join()

    ret=[]
    result = [x.get() for x in result]




    switch_cnt={}
    for i in result:
        for j in i[1].keys():
            if switch_cnt.get(j,-1)==-1:
                switch_cnt[j]=i[1][j]
            else:
                switch_cnt[j]+=i[1][j]

    f=open(ofile+'switch_cnt.json','w')
    json.dump(switch_cnt,f,indent=2)
    f.close()

    # generate balance data
    if balance:
        mini_switch=10000000
        for k in switch_cnt.keys():
            if switch_cnt[k]<mini_switch:
                mini_switch=switch_cnt[k]
        cur_cnt={k:0 for k in switch_cnt.keys()}
        t_ret=[]
        for i in result:
            t_ret+=i[0]

        ret=[]
        for i in t_ret:
            if i.get('key',-1)==-1:
                ret.append(i)
            elif cur_cnt[i['key']]<mini_switch:
                ret.append(i)
                cur_cnt[i['key']]+=1
    else:
        for i in result:
            ret+=i[0]

    f=open(ofile,'w')
    json.dump([{'src':i['src'],'tgt':i['tgt']} for i in ret],f,indent=2)
    f.close()
