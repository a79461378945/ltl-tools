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
import signal
from multiprocessing import Pool
from queue import Queue

TIME_LIMIT=60

def get_proof(data_s):
    vocab = [i for i in 'abcdefghij']
    vocab = set(vocab)

    ret_data=[]
    cnt=0
    for data in data_s:
        cnt+=1
        if cnt%100==0:
            print('\r',cnt,end='')
        proof_list = []
        v, root_node, proof_dic, pair_set, trace = check(data['ltl'], data['trace'], vocab)
        que = Queue()
        que.put(root_node)
        visited = set()
        visited.add(root_node)
        # proof_list.append(root_node)
        # print('proof_dic')
        # print(proof_dic)
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
        # print('proof')
        # for i in proof_list:
        #     print(i)
        data['proof']=list(proof_list)
        ret_pair=[0]*len(pair_set)
        for i in pair_set:
            ret_pair[i[0]]=i[1]
        # data['tgt']=data['trace']+'#'
        # for node in proof_list:
        #     data['tgt']+="%d,%d,%d,%d]"%(node[0],node[1][0],node[1][1],node[2])
        data['pair_set']=ret_pair
        ret_data.append(data)

    return ret_data


if __name__ == "__main__":



    parser = argparse.ArgumentParser(description='Main script for active learning')
    parser.add_argument('-f', type=str, required=False ,default='randltls', help='input file containing ltls')
    parser.add_argument('-o', type=str, required=True, help='output file')
    parser.add_argument('-t', type=int, required=False, default=40, help='thread number')
    parser.add_argument('-s', type=int, required=False, default=100000, help='size')

    args = parser.parse_args()
    infile=args.f
    ofile=args.o

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
    for i in result:
        ret+=i
    f=open(ofile,'w')
    json.dump(ret,f)
    f.close()

