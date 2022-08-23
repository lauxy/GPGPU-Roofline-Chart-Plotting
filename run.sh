#!/bin/bash 
#SBATCH -C gpu 
#SBATCH --gres=gpu:1 
#SBATCH -t 01:00:00 

rm *.csv
# rm *.png
config_file=config.ini

# Read and parse config.ini
function ReadIniFile()    
{
    key=$1  
    section=$2
    ReadINI=`awk -F '=' '/\['$section'\]/{a=1} a==1&&$1~/'$key'/ {print $2;exit}' $config_file`    
    echo "$ReadINI"
    return 0 
}

plot_mode=`ReadIniFile "plot_mode" "BaselineConfig"`
mem_hierarchy=`ReadIniFile "mem_hierarchy" "BaselineConfig"`
alu_hierarchy=`ReadIniFile "alu_hierarchy" "BaselineConfig"`
exe_folder=`ReadIniFile "exe_folder" "BaselineConfig"`
exe_file=`ReadIniFile "exe_file" "BaselineConfig"`

# Time (cycle per second)
metrics="smsp__cycles_elapsed.avg.per_second,\
sm__cycles_elapsed.avg.per_second,\
dram__cycles_elapsed.avg.per_second,\
l1tex__cycles_elapsed.avg.per_second,\
lts__cycles_elapsed.avg.per_second,"

# Peak Traffic
metrics+="dram__bytes.sum.peak_sustained,\
l1tex__t_bytes.sum.peak_sustained,\
lts__t_bytes.sum.peak_sustained,"

# Peak Work
metrics+="sm__sass_thread_inst_executed_op_dfma_pred_on.sum.peak_sustained,\
sm__sass_thread_inst_executed_op_ffma_pred_on.sum.peak_sustained,\
sm__sass_thread_inst_executed_op_hfma_pred_on.sum.peak_sustained,\
sm__inst_executed_pipe_tensor.sum.peak_sustained,"

# Achieved Traffic
mem_options=(${mem_hierarchy//,/ })
for var in ${mem_options[@]}
do
    if [ $var == "HBM" ]
    then
        metrics+="dram__bytes.sum.per_second,"
    elif [ $var == "L1" ]
    then
        metrics+="l1tex__t_bytes.sum.per_second,"
    elif [ $var == "L2" ]
    then
        metrics+="lts__t_bytes.sum.per_second,"
    fi
done

# Achieved Work
alu_options=(${alu_hierarchy//,/ })
for var in ${alu_options[@]}
do 
    if [ $var == "Tensor" ]
    then
        metrics+="smsp__inst_executed_pipe_tensor.sum.per_cycle_elapsed,"
    elif [ $var == "SP" ]
    then
        metrics+="smsp__sass_thread_inst_executed_op_fadd_pred_on.sum.per_cycle_elapsed,\
        smsp__sass_thread_inst_executed_op_fmul_pred_on.sum.per_cycle_elapsed,\
        smsp__sass_thread_inst_executed_op_ffma_pred_on.sum.per_cycle_elapsed,"
    elif [ $var == "DP" ]
    then
        metrics+="smsp__sass_thread_inst_executed_op_dadd_pred_on.sum.per_cycle_elapsed,\
        smsp__sass_thread_inst_executed_op_dmul_pred_on.sum.per_cycle_elapsed,\
        smsp__sass_thread_inst_executed_op_dfma_pred_on.sum.per_cycle_elapsed,"
    elif [ $var == "HP" ]
    then
        metrics+="smsp__sass_thread_inst_executed_op_hadd_pred_on.sum.per_cycle_elapsed,\
        smsp__sass_thread_inst_executed_op_hmul_pred_on.sum.per_cycle_elapsed,\
        smsp__sass_thread_inst_executed_op_hfma_pred_on.sum.per_cycle_elapsed,"
    fi
done

# remove the last ','
metrics=`echo ${metrics%?}`
# remove all spaces in string 'metrics'
metrics=${metrics// /''}
profilestr="ncu --metrics $metrics --csv"

isEmpty=`ls $exe_folder | wc -l`
if [ -z $exe_folder ] || [ $isEmpty == 0 ]
then

    exe_file=(${exe_file//,/ })
    for file in ${exe_file[@]}
    do
        if [ $plot_mode == "separate" ] 
        then
            $profilestr $file > output_$file.csv 2>&1
        elif [ $plot_mode == "union" ] 
        then
            $profilestr $file >> output.csv 2>&1
        fi
    done

else

    for file in $exe_folder/*; 
    do
        if [ $plot_mode == "separate" ] 
        then
            $profilestr $file > output_$file.csv 2>&1
        elif [ $plot_mode == "union" ] 
        then
            $profilestr $file >> output.csv 2>&1
        fi
    done

fi

python3 postprocess.py