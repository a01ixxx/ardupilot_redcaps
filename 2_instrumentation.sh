## FIXME

curr_dir=$(pwd)
analysis_pass="$curr_dir/../Gecko/SVF/Release-build/tools/recovery_pass/cmpt_analysis/libCMPTAnalysis.so"
llvm_output_json_file="$curr_dir/build/sitl/analysis_result.json"
input_ll_file="$curr_dir/build/sitl/one_bitcode.bc"
output_bc_file="$curr_dir/build/sitl/after_cmpt.bc"
cmpt_output_json_file="$curr_dir/build/sitl/compartments_result.json"
template_ld_file="/home/lab/Gecko/compartment/ld_templates/x86-template-link-script.ld"
output_ld_file="$curr_dir/build/sitl/output-link-script.ld"
checkpoint_pass="$curr_dir/../Gecko/SVF/Release-build/tools/recovery_pass/checkpointing/libPassCheckpointing.so"
output_bc_ckeckpoint_file="$curr_dir/build/sitl/after_checkpoint.bc"
# output_bc_ckeckpoint_file="$curr_dir/build/sitl/one_bitcode.bc"
enforce_pass="$curr_dir/../Gecko/SVF/Release-build/tools/recovery_pass/cmpt_enforce/libEnforceCMPT.so"

### Emforce CMPT
opt -f -enable-new-pm=0 -load "$enforce_pass" -HexboxApplication --hexbox-policy="${cmpt_output_json_file}"  "$input_ll_file" -o "$output_bc_file"

./generate_arducopter_lib.sh
./generate_executable.sh 
