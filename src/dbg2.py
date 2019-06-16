import math
import sys
import os
import argparse
import numpy as np
from os.path import join as opj
from matplotlib import pyplot as plt
from collections import defaultdict
from Bio import Seq, SeqIO, SeqRecord
from itertools import chain
from utils import *
# from DNA.src.utils import *
sys.setrecursionlimit(100000) # set the maximum depth as 1500

class PairEnd:
    def __init__(self,length,reads1,reads2,pair_dis=500):
        self.length = length
        self.pairs = {}
        self.pair_dis = pair_dis
        for i in range(len(reads1)):
            self.pairs[reads1[i]] = twin(reads2[i])
            self.pairs[twin(reads2[i])] = reads1[i]

            self.pairs[twin(reads1[i]) ] = reads2[i]
            self.pairs[twin(reads2[i])] = twin(reads1[i])
    
    def contain_pairs(self,contig):
        ans = []
        seqset = set()
        locmap = {}
        c_size = len(contig)
        for i in range(c_size - self.length+1):
            subc = contig[i : i+self.length]
            seqset.add(subc)
            locmap[subc] = i
        for read in self.pairs:
            if read in seqset:
                ans.append((read,locmap[read]))
        return ans
    
    def get_pair(self,p1):
        return self.pairs[p1]


def longest_path(graph, root,visited:set,depth):
    if len(graph[root][1])==0:
        return [root]
    best = [root]
    cur = [root]
    # print("cur depth:{}".format(depth))
    for child in graph[root][1]:
        if child not in visited:
            visited.add(child)
            cur = [root] + longest_path(graph,child,visited,depth+1)
            visited.remove(child)
            if len("".join(cur)) > len("".join(best)) :
                best = cur
    if len(graph[root][1])>0 and best==[root]:
        # circle occur caused terminate
        # print("!!!!")
        pass
    return best

def nodes_combine(nodes,k):
    assert(len(nodes) > 0)
    return nodes[0] + "".join(n[k-1:] for n in nodes[1:])

def choose_path(cur_path,cur_node,graph,k,target_pairs,pair_length):
    count = 0
    for p,loc in target_pairs:
        if len(cur_path)>=loc:
            if p == cur_path[loc-pair_length:loc]:
                return cur_path
            else:
                target_pairs.remove( (p,loc) )
            count += 1
    if len(target_pairs) == 0:
        return ""
    else:
        for node in graph[cur_node][1]:
            next_path = cur_path + node[k-1:]
            ans = choose_path( next_path, node, graph, k, target_pairs, pair_length)
            return ans

def compressed_graph_mining(graph, discription):
    # using pair ends info
    k = discription['k']
    in_degree = discription['in_degree']
    out_degree = discription['out_degree']
    PES = discription['pair_ends']
    count_dict = discription['count_dict']
    results = []
    start_nodes = []
    end_nodes = []
    single_nodes = []
    split_nodes = []
    merge_nodes = []
    hub_nodes = []
    total_length = 0
    for node in graph:
        if len(graph[node][0]) == 0 : # in degree is 0
            start_nodes.append(node)
            assert in_degree[node] == 0, in_degree[node]
        if len(graph[node][1]) == 0 : # out degree is 0
            end_nodes.append(node) # both in-out degree is 0
            assert out_degree[node] == 0, out_degree[node]
        if len(graph[node][0]) == 0 and len(graph[node][1]) == 0:
            single_nodes.append(node)
        if len(graph[node][1]) > 1:
            # assert(len(graph[node][1]) == 2)
            split_nodes.append(node)
            if len(graph[node][0]) > 1:
                # assert(len(graph[node][0]) == 2)
                hub_nodes.append(node)
        if len(graph[node][0]) > 1:
            # assert(len(graph[node][0]) == 2)
            merge_nodes.append(node)
        total_length += len(node)
    print("All asserts passed.")
    print("Split nodes number:{}".format(len(split_nodes)))
    print("Merge nodes number:{}".format(len(merge_nodes)))
    print("Hub nodes number:{}".format(len(hub_nodes)))
    print("Start nodes number:{}".format(len(start_nodes)))
    print("End nodes number:{}".format(len(end_nodes)))
    print("Sigle nodes number:{}".format(len(single_nodes)))
    print("The Start node and End nodes maybe same(single node case),Let's remove them.")
    for node in single_nodes:
        print(len(node))
        results.append(node)
        total_length -= len(node)
        start_nodes.remove(node)
        end_nodes.remove(node)
    print("Length:{}".format(total_length))
    # assert(len(start_nodes) == 4)
    
    visited = set()
    # for node in start_nodes[0:2]:
    #     visited.add(node)
    #     path = longest_path(graph,node,visited,0)
    #     for p in path:
    #         visited.add(p)
    #     ans = nodes_combine(path,k)
    #     print(ans)
    #     results.append(ans)
    for node in split_nodes:
        single_pairs = PES.contain_pairs(node)
        target_pairs = []
        for pair,loc in single_pairs:
            target_pairs.append(( PES.get_pair(pair),loc+PES.pair_dis ))
        right_path = choose_path(node,node,graph,k,target_pairs,PES.length)
        checked_len = len(node) - (k-1)
        cur_check = node
        nxt_check = node
        while(checked_len < len(right_path)- (k-1)):
            choice = 0
            if len(graph[cur_check][1]) == 0:
                break
            # nxt_check = graph[cur_check][1][0]
            for i in range( len(graph[cur_check][1]) ):
                cur = graph[cur_check][1][i]
                if cur == right_path[checked_len:checked_len+len(cur)]:
                    choice = i
                    nxt_check = cur
                    break
            checked_len += len(graph[cur_check][1][choice]) - (k-1)
            graph[cur_check][1] = [ graph[cur_check][1][choice] ]
            cur_check = nxt_check

    for node in start_nodes[0:]:
        visited.add(node)
        path = longest_path(graph,node,visited,0)
        for p in path:
            visited.add(p)
        ans = nodes_combine(path,k)
        # print(ans)
        results.append(ans)
    
    return results


def kmerize(seq,k,count_dict, graph, in_degree, out_degree):
    for i in range(len(seq)-k +1 -1):
        kmer = seq[i:i+k]
        nxtkmer = seq[i+1:i+1+k]
        if kmer not in count_dict:
            graph[kmer] = [[],[]] # 0 is in and 1 is out
            out_degree[kmer] = 0
            in_degree[kmer] = 0
            count_dict[kmer] = 0
        if nxtkmer not in count_dict:
            graph[nxtkmer] = [[],[]]
            out_degree[nxtkmer] = 0
            in_degree[nxtkmer] = 0
            count_dict[nxtkmer] = 0
        
        if nxtkmer not in graph[kmer][1]:
            graph[kmer][1].append(nxtkmer)
        if kmer not in graph[nxtkmer][0]:
            graph[nxtkmer][0].append(kmer)

        out_degree[kmer] += 1
        in_degree[nxtkmer] += 1
        
        count_dict[kmer] += 1
    
    count_dict[seq[-k:]] += 1

def has_kmer(kmerlist,kmer):
    for km in kmerlist:
        if km == kmer:
            return True
    return False

def little_check(G):
    for node in G:
        for nxtnode in G[node][1]:
            assert( has_kmer(G[nxtnode][0],node) )
        for befnode in G[node][0]:
            assert( has_kmer(G[befnode][1],node) )

class DBG():
    """ The DBG Algorithm to implement the de novo problem. """
    def __init__(self,k=29,step=1,limit=1):
        print("Initializing...")
        self.k = k
        self.step = step
        self.limit = limit
        self.count_dict = None
        self.nodes = None
        self.graph = None
        self.in_degree = None
        self.out_degree = None
        self.pair_ends = None

    def load_data(self,data_dir='../data/data1',file_type='short'):
        filenames = os.listdir(data_dir)
        rlist = []
        for fid,fname in enumerate(filenames):
            file_prefix = fname.split('.')[0].split('_')[0]
            if file_type!="all" and file_prefix != file_type:
                continue
            print("Get data from {}".format(fname))
            file_path = opj(data_dir,fname)
            reads = SeqIO.parse(file_path,'fasta')
            rlist.append(reads)
        print("Load the sequences in {} done".format(data_dir))
        print("Building counting dict for them...")
        return rlist

    def build_graph(self,reads_list):
        assert(isinstance(reads_list,list))
        graph={}
        k = self.k
        count_dict = defaultdict(int)
        in_degree = defaultdict(int)
        out_degree = defaultdict(int)
        cache1 = []
        cache2 = []
        for r_id,reads in enumerate(reads_list):
            for read in reads:
                seq = str(read.seq)
                kmerize(seq,k,count_dict,graph,in_degree,out_degree)
                kmerize(twin(seq),k,count_dict,graph,in_degree,out_degree)
                # kmerize(reverse(seq),k,count_dict,graph,in_degree,out_degree)
                # kmerize(reverse(twin(seq) ),k,count_dict,graph,in_degree,out_degree)
                if r_id == 0:
                    cache1.append(seq)
                else:
                    cache2.append(seq)
        self.pair_ends = PairEnd(len(seq),cache1,cache2)

        print("Size of count dict:{}".format(len(count_dict)))
        print("Number of the graph nodes:{}".format(len(graph)))
        self.graph = graph
        self.in_degree = in_degree
        self.out_degree = out_degree
        self.count_dict = count_dict
        count = 0
        for kmer in self.in_degree:
            if self.in_degree[kmer] == 0:
                count += 1
        print("Before Compress, 0 Degree count:{}".format(count))
    
    def graph_simplify(self):
        old_graph = self.graph
        new_graph = {}
        new_in = defaultdict(int)
        new_out = defaultdict(int)
        new_dict = defaultdict(int)
        done = set()
        k = self.k
        node_num = 0
        nodes = []
        for kmer in old_graph:
            if kmer in done:
                continue
            size = 0
            node_num += 1
            new_node = kmer
            cur_kmer = kmer
            done.add(kmer)

            kmer = cur_kmer
            while len(old_graph[kmer][0]) == 1:
                befkmer = old_graph[kmer][0][0]
                if len(old_graph[befkmer][1]) == 1:
                    if befkmer in done:
                        break
                    done.add(befkmer)
                    new_node = befkmer[0] + new_node
                    kmer = befkmer
                    size += 1
                else:
                    break

            kmer = cur_kmer
            while len(old_graph[kmer][1]) == 1:
                nxtkmer = old_graph[kmer][1][0]
                if len(old_graph[nxtkmer][0]) == 1:
                    if nxtkmer in done:
                        break # it will be ok without this judgement
                    done.add(nxtkmer)
                    new_node += nxtkmer[-1]
                    kmer = nxtkmer
                    size += 1
                else:
                    break
                    
            if new_node not in nodes:
                nodes.append(new_node)
                new_graph[new_node] = [[],[]]
                new_dict[new_node] = 0
                new_out[new_node] = 0
                new_in[new_node] = 0
            new_dict[new_node] += size
        
        print("Node Num:{}".format(node_num))
        for i in range(node_num):
            node1 = nodes[i]
            for j in range(i+1,node_num):
                node2 = nodes[j]
                if node1[-k+1:] == node2[:k-1]:
                    new_graph[node1][1].append(node2)
                    new_out[node1] += 1
                    new_graph[node2][0].append(node1)
                    new_in[node2] += 1
                if node2[-k+1:] == node1[:k-1]:
                    new_graph[node2][1].append(node1)
                    new_out[node2] += 1
                    new_graph[node1][0].append(node2)
                    new_in[node1] += 1
        little_check(new_graph)
        self.graph = new_graph
        self.in_degree = new_in
        self.out_degree = new_out
        self.count_dict = new_dict
        print("Compressed Graph size:{}".format(len(self.graph)))

    def show_graph(self,dotpath,idtable=None):
        node2id = {}
        id2node = {}
        G = self.graph
        g_size = len(G)
        for id,node in enumerate(G):
            node2id[node] = id
            id2node[id] = node
        lines = ["digraph G {", "graph [rankdir=LR, fontname=\"Courier\"];", "node [shape=record];"]
        for id in range(g_size):
            node = id2node[id]
            lines.append("{}[label=\"{}({})\"];".format(id,id,len(node)) )
        for id in range(g_size):
            node = id2node[id]
            for child in G[node][1]:
                child_id = node2id[child]
                lines.append("{} -> {} ;".format(id,child_id))
            # for child in G[node][0]:
            #     child_id = node2id[child]
            #     lines.append("{} -> {} ;".format(child_id,id))
        lines.append("}")
        with open(dotpath,'w') as f:
            f.write('\n'.join(lines))
        if idtable is not None:
            with open(idtable,'w') as f:
                for id in id2node:
                    f.write("{} : {} \n".format(id,id2node[id]))
        return '\n'.join(lines)

    def fit(self,data_dir='../data/data1',file_type='short'):
        rlist = self.load_data(data_dir,file_type)
        self.build_graph(rlist)
        self.graph_simplify()
        # node_len_lst = []
        # for node in self.graph:
        #     node_len_lst.append(len(node))
        # plt.hist(node_len_lst,bins=100)
        # plt.show()        

    def get_answers(self,mode='simple',graph_path=None,table_path=None):
        discription = { 'in_degree':self.in_degree,'count_dict':self.count_dict,
                        'out_degree':self.out_degree,'k':self.k,'pair_ends':self.pair_ends }
        if (graph_path is not None) :
            self.show_graph(graph_path,table_path)
        output = compressed_graph_mining(self.graph,discription)
        print("Number of results:{}".format(len(output)))
        # print(output)
        return output


if __name__ == "__main__":
    args = parse_args()
    dbg = DBG(k=args.k,step=args.step,limit=args.limit)
    dbg.fit(args.data_dir,args.file_type)
    res = dbg.get_answers(  mode=args.mode,
                            graph_path='./graph_2.dot',table_path='./id2node_2.txt')
    if args.top == 0:
        n = len(res)
    else:
        n = args.top
    seq_len = []
    for i,seq in enumerate(res):
        seq_len.append((i,len(seq)))
    seq_len = sorted(seq_len,key=lambda x: -x[1])
    ans = [res[x[0]] for x in seq_len[:n]]
    # print(ans)
    result_name = args.result_name
    result_name = "result_t.fasta"
    with open(opj(args.result_dir, result_name) ,'w') as fout:
        for i,seq in enumerate(ans):
            fout.write(">short_read_{}/1".format(i))
            fout.write("\n")
            fout.write(seq)
            fout.write("\n")
