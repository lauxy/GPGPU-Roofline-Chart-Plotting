import os
from tokenize import Double
import numpy as np
import pandas as pd
from roofline import roofline

kv_pair={}
# read and parse config.ini 
with open('config.ini', 'r') as ini:
    lines = ini.readlines()
    for line in lines:
        line = line.strip()
        if line == '\n' or line[0] == ';':
            continue
        elif line[0] == '[':
            SectionName = line[1:-1].strip()
        else:
            key = line[:line.find('=')]
            value = line[line.find('=')+1:]
            kv_pair[key] = value

datadir='.'
files=[x for x in os.listdir(datadir) if x.endswith('.csv') and x.startswith('output')]
files.sort()
files=[os.path.join(datadir,file) for file in files]
dfs={}
for file in files:
    tag, ext = os.path.splitext(os.path.basename(file))
    dfs[tag]=pd.DataFrame()

    # [preprocess] remove profiling process in the output*.csv
    with open(file, 'r') as f:
        lines = f.readlines()
    with open(file, 'w') as f:
        newlines = []
        hasTitle = 0
        for line in lines:
            if line[0] == '\"':
                if 'Host Name' in line:
                    hasTitle += 1
                    if hasTitle > 1:
                        continue
                newlines.append(line)
        f.writelines(newlines)
    
    # load csv formally to postprecess the profiling data
    with open(file,'r') as f:
        df = pd.read_csv(file)
        df['Metric Value'] = df['Metric Value'].str.replace(",", "").astype(float)
        dft=df.groupby(['Kernel Name','Metric Name']).sum()
        dfmetric=pd.pivot_table(dft, index='Kernel Name', columns='Metric Name', values='Metric Value')

        # Peak Traffic
        dfmetric['Peak HBM'] = dfmetric['dram__bytes.sum.peak_sustained'] \
                            * dfmetric['dram__cycles_elapsed.avg.per_second'] / 2**30
        dfmetric['Peak L1'] = dfmetric['l1tex__t_bytes.sum.peak_sustained'] \
                            * dfmetric['l1tex__cycles_elapsed.avg.per_second'] / 2**30
        dfmetric['Peak L2'] = dfmetric['lts__t_bytes.sum.peak_sustained'] \
                            * dfmetric['lts__cycles_elapsed.avg.per_second'] / 2**30

        # Peak Work (TFLOPS)
        dfmetric['Peak DP'] = dfmetric['sm__sass_thread_inst_executed_op_dfma_pred_on.sum.peak_sustained'] * 2 \
                            * dfmetric['sm__cycles_elapsed.avg.per_second'] / 2**40
        dfmetric['Peak SP'] = dfmetric['sm__sass_thread_inst_executed_op_ffma_pred_on.sum.peak_sustained'] * 2 \
                            * dfmetric['sm__cycles_elapsed.avg.per_second'] / 2**40
        dfmetric['Peak HP'] = dfmetric['sm__sass_thread_inst_executed_op_hfma_pred_on.sum.peak_sustained'] * 2 \
                            * dfmetric['sm__cycles_elapsed.avg.per_second'] / 2**40
        dfmetric['Peak TC'] = dfmetric['sm__inst_executed_pipe_tensor.sum.peak_sustained'] * 512 \
                            * dfmetric['sm__cycles_elapsed.avg.per_second'] / 2**40

        # Achieved Work (SP, DP, HP, Tensor Core)
        if 'SP' in kv_pair['alu_hierarchy']:
            dfmetric['Achieved SP FLOPS'] = (dfmetric['smsp__sass_thread_inst_executed_op_fadd_pred_on.sum.per_cycle_elapsed'] \
                                        + dfmetric['smsp__sass_thread_inst_executed_op_fmul_pred_on.sum.per_cycle_elapsed'] \
                                        + dfmetric['smsp__sass_thread_inst_executed_op_ffma_pred_on.sum.per_cycle_elapsed'] * 2) \
                                        * dfmetric['smsp__cycles_elapsed.avg.per_second']
        if 'DP' in kv_pair['alu_hierarchy']:
            dfmetric['Achieved DP FLOPS'] = (dfmetric['smsp__sass_thread_inst_executed_op_dadd_pred_on.sum.per_cycle_elapsed'] \
                                        + dfmetric['smsp__sass_thread_inst_executed_op_dmul_pred_on.sum.per_cycle_elapsed'] \
                                        + dfmetric['smsp__sass_thread_inst_executed_op_dfma_pred_on.sum.per_cycle_elapsed'] * 2) \
                                        * dfmetric['smsp__cycles_elapsed.avg.per_second']
        if 'HP' in kv_pair['alu_hierarchy']:
            dfmetric['Achieved HP FLOPS'] = (dfmetric['smsp__sass_thread_inst_executed_op_hadd_pred_on.sum.per_cycle_elapsed'] \
                                        + dfmetric['smsp__sass_thread_inst_executed_op_hmul_pred_on.sum.per_cycle_elapsed'] \
                                        + dfmetric['smsp__sass_thread_inst_executed_op_hfma_pred_on.sum.per_cycle_elapsed'] * 2) \
                                        * dfmetric['smsp__cycles_elapsed.avg.per_second']
        if 'Tensor' in kv_pair['alu_hierarchy']:
            dfmetric['Achieved Tensor FLOPS'] = (dfmetric['smsp__inst_executed_pipe_tensor.sum.per_cycle_elapsed'] * 512) \
                                            * dfmetric['smsp__cycles_elapsed.avg.per_second']
        
        # dfmetric['Achieved All FLOPS'] = dfmetric['Achieved SP FLOPS'] + dfmetric['Achieved DP FLOPS'] \
        #                                + dfmetric['Achieved HP FLOPS'] + dfmetric['Achieved Tensor FLOPS']

        # Note: dfmetric['Achieved Tensor FLOPS'] must not be empty!
        dfmetric['Achieved All FLOPS'] = dfmetric['Achieved Tensor FLOPS']                           
        for item in kv_pair['alu_hierarchy'].split(','):
            if item != 'Tensor':
                dfmetric['Achieved All FLOPS'] += dfmetric['Achieved '+item+' FLOPS']

        # FLOPS --> GFLOPS
        dfmetric['Achieved All GLOPS'] = dfmetric['Achieved All FLOPS'] / 2**30
        # dfmetric['Achieved Tensor GFLOPS'] = dfmetric['Achieved Tensor FLOPS'] / 2**30

        # Achieved Traffic
        if 'HBM' in kv_pair['mem_hierarchy']:
            dfmetric['Achieved HBM Traffic'] = dfmetric['dram__bytes.sum.per_second']
        if 'L1' in kv_pair['mem_hierarchy']:
            dfmetric['Achieved L1 Traffic'] = dfmetric['l1tex__t_bytes.sum.per_second']
        if 'L2' in kv_pair['mem_hierarchy']:
            dfmetric['Achieved L2 Traffic'] = dfmetric['lts__t_bytes.sum.per_second']
        
        # Achieved Arithmetic Intensity
        if 'HBM' in kv_pair['mem_hierarchy']:
            dfmetric['AI HBM'] = dfmetric['Achieved All FLOPS'].div(dfmetric['Achieved HBM Traffic'])
        if 'L1' in kv_pair['mem_hierarchy']:
            dfmetric['AI L1'] = dfmetric['Achieved All FLOPS'].div(dfmetric['Achieved L1 Traffic'])
        if 'L2' in kv_pair['mem_hierarchy']:
            dfmetric['AI L2'] = dfmetric['Achieved All FLOPS'].div(dfmetric['Achieved L2 Traffic'])

        # dfmetric.to_csv('pd_'+tag+'.csv')
        # Each tag corresponds to a csv file
        dfs[tag]=dfmetric


tags=dfs.keys()
options = {'mem_options':kv_pair['mem_hierarchy'], 'alu_options':kv_pair['alu_hierarchy'], 'rfl_name':kv_pair['roofline_name']}

exe_list=[]
if not kv_pair['exe_folder'] or len(os.listdir(kv_pair['exe_folder'])) == 0:
    exe_list = kv_pair['exe_file'].split(',')
else:
    exe_list = os.listdir(kv_pair['exe_folder'])

for tag in tags:
    roofline(tag, dfs[tag], options, exe_list)