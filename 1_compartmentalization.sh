./pre_compile.sh
./link_as_one_bitcode.sh

curr_dir=$(pwd)
analysis_pass="$curr_dir/../Gecko/SVF/Release-build/tools/recovery_pass/cmpt_analysis/libCMPTAnalysis.so"
llvm_output_json_file="$curr_dir/build/sitl/analysis_result.json"
input_ll_file="$curr_dir/build/sitl/one_bitcode.bc"
output_bc_file="$curr_dir/build/sitl/after_cmpt.bc"
cmpt_output_json_file="$curr_dir/build/sitl/compartments_result.json"
template_ld_file="$curr_dir/../Gecko/compartment/ld_templates/x86-template-link-script.ld"
output_ld_file="$curr_dir/build/sitl/output-link-script.ld"
checkpoint_pass="$curr_dir/../Gecko/SVF/Release-build/tools/recovery_pass/checkpointing/libPassCheckpointing.so"
output_bc_ckeckpoint_file="$curr_dir/build/sitl/after_checkpoint.bc"
# output_bc_ckeckpoint_file="$curr_dir/build/sitl/one_bitcode.bc"
enforce_pass="$curr_dir/../Gecko/SVF/Release-build/tools/recovery_pass/cmpt_enforce/libEnforceCMPT.so"

## Generate CMPT
opt -f -enable-new-pm=0 -load "$analysis_pass" -HexboxAnaysis --task-names-file="/tmp/task_cmpt.txt" --hexbox-analysis-results="${llvm_output_json_file}" < "$input_ll_file" > "$output_bc_file"

# opt load xxpass  one_bitcode.bc
## Compartementalize
## Generate a link script
python3 "$curr_dir/../Gecko/compartment/scripts/analyzer.py" \
    -j="$llvm_output_json_file" \
    -s="./size_result.json" \
    -o="$cmpt_output_json_file" \
    -m=task \
    -T="$template_ld_file" \
    -L="$output_ld_file"